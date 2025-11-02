from django.shortcuts import render, redirect, HttpResponse
from django.views import View
from finance.forms import RegisterForm, TransactionForm, GoalForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from finance.models import Transaction, Goal
from django.db.models import Sum
from .admin import TransactionResource
from django.contrib import messages
from django.urls import reverse_lazy
# Create your views here.



class RegisterView(View):
    def get(self, request, *args, **kwargs):
        form=RegisterForm()
        return render(request, 'finance/register.html', {'form':form})
    
    def post(self, request, *args, **kwargs):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
        return render(request, 'finance/register.html', {'form':form})    

class DashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        transactions = Transaction.objects.filter(user=request.user)
        goals = Goal.objects.filter(user=request.user)

        #calculate total income and expenses
        total_income = Transaction.objects.filter(user=request.user, transaction_type='Income').aggregate(Sum('amount'))['amount__sum'] or 0 
            

        total_expense = Transaction.objects.filter(user=request.user, transaction_type='Expense').aggregate(Sum('amount'))['amount__sum'] or 0
            
        net_savings = total_income - total_expense

        remaining_savings = net_savings
        goal_progress = []
        for goal in goals:
            if remaining_savings >= goal.target_amount:
                goal_progress.append({'goal':goal, 'progress':100})
                remaining_savings -= goal.target_amount
            elif remaining_savings > 0:
                progress= (remaining_savings / goal.target_amount) * 100
                goal_progress.append({'goal':goal, 'progress':progress})
                remaining_savings = 0
            else:
                goal_progress.append({'goal':goal, 'progress':0})


        context = {
            'transactions': transactions,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_savings': net_savings,
            'goal_progress': goal_progress,
        }

        return render(request, 'finance/dashboard.html', context)
                       

class TransactionCreateView(LoginRequiredMixin, View): 
    def get(self, request, *args, **kwargs):
        form=TransactionForm()
        return render(request, 'finance/transaction_form.html', {'form':form})
    
    def post(self, request, *args, **kwargs):
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, "Transaction added successfully!")
            return redirect('dashboard')

        return render(request, 'finance/transaction_form.html', {'form':form})
    
class TransactionListView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        transactions = Transaction.objects.filter(user=request.user)
        return render(request, 'finance/transaction_list.html', {'transactions': transactions})
    

class GoalCreateView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form=GoalForm()
        return render(request, 'finance/goal_form.html', {'form':form})
    
    def post(self, request, *args, **kwargs):
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, "Goal added successfully!")
            return redirect('dashboard')

        return render(request, 'finance/goal_form.html', {'form':form})

    

class GoalUpdateView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            goal = Goal.objects.get(id=kwargs['pk'], user=request.user)
        except Goal.DoesNotExist:
            messages.error(request, "Goal not found.")
            return redirect('dashboard')
        
        form = GoalForm(instance=goal)
        return render(request, 'finance/goal_form.html', {
            'form': form, 
            'goal': goal, 
            'is_edit': True
        })
    
    def post(self, request, *args, **kwargs):
        try:
            goal = Goal.objects.get(id=kwargs['pk'], user=request.user)
        except Goal.DoesNotExist:
            messages.error(request, "Goal not found.")
            return redirect('dashboard')
        
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()  # No need to reassign
            messages.success(request, "Goal updated successfully!")
            return redirect('dashboard')
        
        messages.error(request, "Please correct the errors below.")
        return render(request, 'finance/goal_form.html', {
            'form': form, 
            'goal': goal, 
            'is_edit': True
        })

class GoalDeleteView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            goal = Goal.objects.get(id=kwargs['pk'], user=request.user)
        except Goal.DoesNotExist:
            messages.error(request, "Goal not found.")
            return redirect('dashboard')
        
        return render(request, 'finance/goal_confirm_delete.html', {'goal': goal})
    
    def post(self, request, *args, **kwargs):
        try:
            goal = Goal.objects.get(id=kwargs['pk'], user=request.user)
        except Goal.DoesNotExist:
            messages.error(request, "Goal not found.")
            return redirect('dashboard')
        
        goal.delete()
        messages.success(request, "Goal deleted successfully!")
        return redirect('dashboard')
    


def export_transactions(request):
    user_transactions = Transaction.objects.filter(user=request.user)

    transactions_resource = TransactionResource()
    dataset = transactions_resource.export(queryset=user_transactions)

    excel_data=dataset.export('xlsx')

    response =  HttpResponse(excel_data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # header for download the file
    response['Content-Disposition'] = 'attachment; filename=transactions.xlsx'
    return response