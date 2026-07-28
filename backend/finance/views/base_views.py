from finance.models import Transaction, Goal, User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from serializers.base_serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    TransactionCreateSerializer, GoalCreateSerializer, GoalUpdateSerializer,
    GoalDeleteSerializer, TransactionUpdateSerializer, TransactionDeleteSerializer,
    TransactionSerializer, GoalListSerializer,
)
from serializers.auth_serializers import LogoutRequestSerializer, LogoutResponseSerializer
from helpers.bulk_upload_helper import generate_transaction_template, process_bulk_upload
from helpers.jwt_token_helper import get_tokens_for_user
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.conf import settings
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken

class RegisterView(APIView):
    
    permission_classes = [AllowAny]
    def post(self, request):

        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            response = Response({
                "status": "success",
                "message": "User created successfully",
                "tokens": {
                    "access": tokens["access"]
                },
                "user": {"id": user.id, "username": user.username}
            }, status=status.HTTP_201_CREATED)
            response.set_cookie(
                key='refresh_token',
                value=tokens['refresh'],
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=7 * 24 * 60 * 60, # 7 days
            )
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(APIView):
    permission_classes = [AllowAny]
    # Explicitly throttle this view even when authenticated views opt-out.
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            # authenticate() returns None for both "no such user" and
            # "wrong password" — one identical code path, no enumeration oracle.
            from django.contrib.auth import authenticate
            user = authenticate(request, username=username, password=password)

            if user is None:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            tokens = get_tokens_for_user(user)
            user_serializer = UserSerializer(user)
            response = Response({
                "message": "Login successful",
                "tokens": {
                    "access": tokens["access"]
                },
                "user": user_serializer.data
            }, status=status.HTTP_200_OK)
            response.set_cookie(
                key='refresh_token',
                value=tokens['refresh'],
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=7 * 24 * 60 * 60,  # 7 days
            )
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            serializer = LogoutRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            refresh_token = serializer.validated_data["refresh_token"]

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            response_data = {"status": "success", "message": "Logout successful"}
            response = Response(
                LogoutResponseSerializer(response_data).data,
                status=status.HTTP_205_RESET_CONTENT,
            )
            response.delete_cookie('refresh_token')
            return response
        except TokenError:
            response = Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
            response.delete_cookie('refresh_token')
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            refresh_token = request.data.get('refresh')
            
        if not refresh_token:
            return Response({"error": "Refresh token not found in cookies or request data"}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = self.get_serializer(data={"refresh": refresh_token})
        
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
            
        res_data = serializer.validated_data
        response = Response({"access": res_data.get("access")}, status=status.HTTP_200_OK)
        
        if "refresh" in res_data:
            response.set_cookie(
                key='refresh_token',
                value=res_data["refresh"],
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=7 * 24 * 60 * 60, # 7 days
            )
        return response
                              

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
        month_param = request.GET.get('month')  # YYYY-MM
        year_param  = request.GET.get('year')   # YYYY

        if month_param:
            # Filter by specific month and year, e.g. ?month=2026-06
            try:
                year, month = map(int, month_param.split('-'))
                if not (1 <= month <= 12):
                    raise ValueError
                transactions = transactions.filter(date__year=year, date__month=month)
            except ValueError:
                return Response(
                    {"error": "Invalid format for 'month' parameter. Use YYYY-MM (e.g. 2026-06)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif year_param:
            # Filter by entire year, e.g. ?year=2026
            try:
                year = int(year_param)
                transactions = transactions.filter(date__year=year)
            except ValueError:
                return Response(
                    {"error": "Invalid format for 'year' parameter. Use YYYY (e.g. 2026)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Default: show current month's transactions
            now = timezone.now()
            transactions = transactions.filter(date__year=now.year, date__month=now.month)

        serializer = TransactionSerializer(transactions, many=True)
        return Response({
            "status": "success",
            "transactions": serializer.data,
            "filter_applied": {
                "month": month_param or None,
                "year": year_param or None,
                "default": not month_param and not year_param,
            }
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

class GoalListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        goals = Goal.objects.filter(user=request.user).order_by('deadline')
        serializer = GoalListSerializer(goals, many=True)

        # Compute total savings (all-time income − expense)
        from django.db.models import Sum, Q, DecimalField
        from django.db.models.functions import Coalesce

        totals = Transaction.objects.filter(user=request.user).aggregate(
            total_income=Coalesce(
                Sum('amount', filter=Q(transaction_type='Income')),
                0, output_field=DecimalField()
            ),
            total_expense=Coalesce(
                Sum('amount', filter=Q(transaction_type='Expense')),
                0, output_field=DecimalField()
            ),
        )
        total_savings = float(totals['total_income'] - totals['total_expense'])

        # Sum of target amounts for current goals
        current_goals = Goal.objects.filter(user=request.user, status='current')
        total_target = float(
            current_goals.aggregate(
                total=Coalesce(Sum('target_amount'), 0, output_field=DecimalField())
            )['total']
        )

        return Response({
            "status": "success",
            "goals": serializer.data,
            "total_savings": total_savings,
            "total_target": total_target,
        }, status=status.HTTP_200_OK)


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


