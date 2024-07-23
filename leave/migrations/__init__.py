from leave.models import EmployeePastLeaveRestrict

enabled_restriction = EmployeePastLeaveRestrict.objects.first()
if not enabled_restriction:
    enabled_restriction = EmployeePastLeaveRestrict.objects.create(enabled=True)
