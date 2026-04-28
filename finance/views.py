from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.views import View
from finance.forms import TransactionForm, GoalForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from finance.models import Transaction, Goal, User
from django.db.models import Sum
from .admin import TransactionResource
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.hashers import check_password
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from helpers.jwt_token_helper import get_tokens_for_user
from finance.utils.forecasting import ml_forecast_next_month
from finance.utils.budget_advice import generate_budget_advice
from finance.utils.optimizer import recommend_saving_for_goal


# Create your views here.

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):

        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({
                "status": "success",
                "message": "User created successfully",
                "tokens": tokens,
                "user": {"id": user.id, "username": user.username}
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            try:
                user = User.objects.get(username=username)    
                if check_password(password, user.password):
                    tokens = get_tokens_for_user(user)
                    user_serializer = UserSerializer(user)
                    return Response({
                        "message": "Login successful",
                        "tokens": tokens,
                        "user": user_serializer.data
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)
                
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class DashboardView(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self, request, *args, **kwargs):
        user = request.user
        user_serializer = UserSerializer(user)
        today = timezone.now()

        # Month Filter
        month_year = request.GET.get("month_year")
        if month_year:
            year, month = map(int, month_year.split("-"))
        else:
            year = today.year
            month = today.month

        # Filter transactions for selected month
        transactions = Transaction.objects.filter(
            user=request.user,
            date__year=year,
            date__month=month
        )

        # Fetch goals
        goals = Goal.objects.filter(user=request.user)

        # Calculate basic financials
        total_income = transactions.filter(transaction_type='Income').aggregate(total=Sum('amount'))['total'] or 0
        total_expense = transactions.filter(transaction_type='Expense').aggregate(total=Sum('amount'))['total'] or 0
        net_savings = total_income - total_expense

        # Goal progress calculation (existing logic)
        remaining_savings = net_savings
        goal_progress = []
        for goal in goals:
            if remaining_savings >= goal.target_amount:
                progress = 100
                remaining_savings -= goal.target_amount
            elif remaining_savings > 0:
                progress = (remaining_savings / goal.target_amount) * 100
                remaining_savings = 0
            else:
                progress = 0
            
            goal_progress.append({
                'goal': goal,
                'progress': round(progress, 2)
            })

        # ML Forecasting
        user_id = request.user.id
        predicted_income = ml_forecast_next_month(request.user, "Income", method="prophet", user_id=user_id)
        predicted_expense = ml_forecast_next_month(request.user, "Expense", method="prophet", user_id=user_id)
        predicted_savings = predicted_income - predicted_expense

        # Personalized Forecast Advice
        budget_advice = generate_budget_advice(predicted_income, predicted_expense)

        # Goal Optimization Recommendations (NEW FEATURE)
        goal_recommendations = []
        for item in goal_progress:
            goal = item['goal']
            recommendation = recommend_saving_for_goal(request.user, goal, target_probability=0.80)
            recommendation.update({
                "goal_id": goal.id,
                "goal_name": goal.name,
                "goal_target": goal.target_amount,
                "goal_progress": item['progress']
            })
            goal_recommendations.append(recommendation)

        # Send all data to template
        context = {
            'transactions': transactions,
            'selected_month': f"{year}-{month:02d}",

            # Key Financials
            'total_income': round(total_income, 2),
            'total_expense': round(total_expense, 2),
            'net_savings': round(net_savings, 2),

            # Goal Progress + Recommendations
            'goal_progress': goal_progress,
            'goal_recommendations': goal_recommendations,

            # Forecast + Advice
            'predicted_income': round(predicted_income, 2),
            'predicted_expense': round(predicted_expense, 2),
            'predicted_savings': round(predicted_savings, 2),
            'budget_advice': budget_advice,
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
        return render(request, 'finance/goalUpdate.html', {
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
            form.save()  
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


