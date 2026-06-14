from rest_framework import serializers

from finance.models import User, Transaction, Goal, RecurringTransaction

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password') 
        extra_kwargs = {
            'password': {'write_only': True}
        }
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class TransactionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(decimal_places=2, max_digits=18)
    transaction_type = serializers.CharField(max_length=10)
    date = serializers.DateField()
    category = serializers.CharField(max_length=255)
    
    def create(self, validated_data):
        return Transaction.objects.create(user=self.context['user'], **validated_data)

class GoalCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    target_amount = serializers.DecimalField(decimal_places=2, max_digits=10)
    deadline = serializers.DateField()
    status = serializers.CharField(max_length=20, required=False)
    
    def create(self, validated_data):
        return Goal.objects.create(user=self.context['user'], **validated_data)

class GoalUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=100, required=False)
    target_amount = serializers.DecimalField(decimal_places=2, max_digits=10, required=False)
    deadline = serializers.DateField(required=False)
    status = serializers.CharField(max_length=20, required=False)
    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.target_amount = validated_data.get('target_amount', instance.target_amount)
        instance.deadline = validated_data.get('deadline', instance.deadline)
        instance.status = validated_data.get('status', instance.status)
        instance.save()
        return instance

class GoalDeleteSerializer(serializers.Serializer):
    id = serializers.IntegerField()

class TransactionUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField(max_length=255, required=False)
    amount = serializers.DecimalField(decimal_places=2, max_digits=18, required=False)
    transaction_type = serializers.CharField(max_length=10, required=False)
    date = serializers.DateField(required=False)
    category = serializers.CharField(max_length=255, required=False)
    
    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.amount = validated_data.get('amount', instance.amount)
        instance.transaction_type = validated_data.get('transaction_type', instance.transaction_type)
        instance.date = validated_data.get('date', instance.date)
        instance.category = validated_data.get('category', instance.category)
        instance.save()
        return instance

class TransactionDeleteSerializer(serializers.Serializer):
    id = serializers.IntegerField()

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('title', 'amount', 'transaction_type', 'date', 'category')


class RecurringTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringTransaction
        fields = (
            'id', 'title', 'amount', 'interval_bucket', 'mean_gap_days',
            'confidence', 'next_expected_date', 'recurring_type',
            'occurrences', 'last_date', 'is_active',
        )

class GoalListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ('id', 'name', 'target_amount', 'deadline','status')

