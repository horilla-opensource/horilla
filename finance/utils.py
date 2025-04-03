from decimal import Decimal

def calculate_total_profit(finance):
    estimated_cost = finance.estimated_revenue - finance.estimated_expense
    total_dynamic_cost = sum(Decimal(cost.percentage) / Decimal(100) * estimated_cost for cost in finance.project.distributions.all())

    total_profit = estimated_cost - total_dynamic_cost
    return total_profit
