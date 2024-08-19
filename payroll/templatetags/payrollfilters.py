from django import template

register = template.Library()


@register.filter(name="balance_amount")
def balance_amount(amount, installment):
    balance = amount - sum(installment.values_list("amount", flat=True))
    return balance
