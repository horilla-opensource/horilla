from django import template

register = template.Library()


@register.filter(name="paid_amount")
def paid_amount(installment):
    paid = [
        deduction.amount for deduction in installment if deduction.installment_payslip()
    ]

    return sum(paid)


@register.filter(name="balance_amount")
def balance_amount(amount, installment):
    balance = amount - paid_amount(installment)
    return balance


@register.filter
def can_approve(reimbursement, employee):
    """Return True if the employee can approve the reimbursement."""
    if not employee:
        return False
    return reimbursement.can_be_approved_by(employee)
