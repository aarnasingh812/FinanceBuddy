def generate_budget_advice(predicted_income, predicted_expense):
    savings = predicted_income - predicted_expense

    if predicted_income == 0 and predicted_expense == 0:
        return "Not enough data to generate advice yet."

    if savings < 0:
        return "⚠️ You’re likely to overspend next month. Trim variable costs (eating out, subscriptions)."
    elif savings < (predicted_income * 0.1):
        return "💡 Savings will be low. Consider re-evaluating recurring subscriptions."
    else:
        return "✅ You're on track. Maintain your current saving habits!"
