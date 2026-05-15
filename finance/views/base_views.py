from django.shortcuts import render, redirect, HttpResponse
from django.views import View
from finance.models import Transaction, Goal, User
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from serializers.base_serializers import (
RegisterSerializer, LoginSerializer, UserSerializer, 
TransactionCreateSerializer, GoalCreateSerializer, GoalUpdateSerializer, 
GoalDeleteSerializer, TransactionUpdateSerializer, TransactionDeleteSerializer,
TransactionSerializer
)
from helpers.bulk_upload_helper import generate_transaction_template, process_bulk_upload
from helpers.jwt_token_helper import get_tokens_for_user
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

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
                if user.check_password(password):
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

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if not refresh_token:
                return Response({"error": "refresh_token is required"}, status=status.HTTP_400_BAD_REQUEST)
                
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"status": "success", "message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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

        return Response({
            "status": "success",
            "message": "Transactions fetched successfully",
        }, status=status.HTTP_200_OK)

                              

class TransactionView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        serializer = TransactionCreateSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "success",
                "message": "Transaction created successfully",
                "transaction": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def put(self, request, *args, **kwargs):
        serializer = TransactionUpdateSerializer(data=request.data)
        if serializer.is_valid():
            transaction_id = serializer.validated_data['id']
            try:
                transaction = Transaction.objects.get(id=transaction_id, user=request.user)
            except Transaction.DoesNotExist:
                return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer.update(transaction, serializer.validated_data)
            return Response({
                "status": "success",
                "message": "Transaction updated successfully"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        serializer = TransactionDeleteSerializer(data=request.data)
        if serializer.is_valid():
            transaction_id = serializer.validated_data['id']
            try:
                transaction = Transaction.objects.get(id=transaction_id, user=request.user)
                transaction.delete()
                return Response({
                    "status": "success",
                    "message": "Transaction deleted successfully"
                }, status=status.HTTP_200_OK)
            except Transaction.DoesNotExist:
                return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
            
class TransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        transactions = Transaction.objects.filter(user=request.user).order_by('-date')
        
        month_filter = request.GET.get('month')
        if month_filter:
            try:
                year, month = map(int, month_filter.split('-'))
                transactions = transactions.filter(date__year=year, date__month=month)
            except ValueError:
                return Response({"error": "Invalid format for month filter. Use YYYY-MM"}, status=status.HTTP_400_BAD_REQUEST)
                
        serializer = TransactionSerializer(transactions, many=True)
        return Response({
            "status": "success",
            "transactions": serializer.data
        }, status=status.HTTP_200_OK)
        

class GoalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = GoalCreateSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "success",
                "message": "Goal created successfully",
                "goal": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        serializer = GoalUpdateSerializer(data=request.data)
        if serializer.is_valid():
            goal_id = serializer.validated_data['id']
            try:
                goal = Goal.objects.get(id=goal_id, user=request.user)
            except Goal.DoesNotExist:
                return Response({"error": "Goal not found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer.update(goal, serializer.validated_data)
            return Response({
                "status": "success",
                "message": "Goal updated successfully"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, *args, **kwargs):
        serializer = GoalDeleteSerializer(data=request.data)
        if serializer.is_valid():
            goal_id = serializer.validated_data['id']
            try:
                goal = Goal.objects.get(id=goal_id, user=request.user)
                goal.delete()
                return Response({
                    "status": "success",
                    "message": "Goal deleted successfully"
                }, status=status.HTTP_200_OK)
            except Goal.DoesNotExist:
                return Response({"error": "Goal not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        mode = request.GET.get('mode')
        if mode != 'download':
            return Response({'error': 'Invalid mode. Use ?mode=download to get the template.'},status=status.HTTP_400_BAD_REQUEST)
        return generate_transaction_template()

    def post(self, request, *args, **kwargs):
        
        mode = request.GET.get('mode')
        if mode != 'upload':
            return Response({'error': 'Invalid mode. Use ?mode=upload to upload transactions.'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided. Send the file with key "file".'}, status=status.HTTP_400_BAD_REQUEST)

        if not file.name.endswith('.xlsx'):
            return Response({'error': 'Invalid file type. Only .xlsx files are accepted.'}, status=status.HTTP_400_BAD_REQUEST)

        success, data = process_bulk_upload(file, request.user)

        if success:
            return Response({'status': 'success', **data}, status=status.HTTP_201_CREATED)
        else:
            return Response({'status': 'error', **data}, status=status.HTTP_400_BAD_REQUEST)


