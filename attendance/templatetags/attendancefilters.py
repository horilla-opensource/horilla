from django.template.defaultfilters import register
from django import template
from attendance.models import AttendanceValidationCondition, Attendance
from attendance.views import format_time, strtime_seconds
from employee.models import EmployeeWorkInformation
from django.contrib.auth.models import Permission
import datetime
from django.contrib.auth.models import User, Permission

from itertools import groupby
from django.template import TemplateSyntaxError

register = template.Library()

@register.filter(name='checkminimumot')
def checkminimumot(ot=None):
    """
    This filter method is used to check minimum overtime from the attendance validation condition 
    """    
    if ot is not None:
        condition = AttendanceValidationCondition.objects.all()
        if condition.exists():
            minimum_overtime_to_approve = condition[0].minimum_overtime_to_approve
            overtime_second = strtime_seconds(ot)
            minimum_ot_approve_seconds= strtime_seconds(minimum_overtime_to_approve)
            if overtime_second > minimum_ot_approve_seconds:
                return True
        return False

# @register.filter(name='is_reportingmanager')
# def is_reportingmanager(user):
#     """
#     This method returns true if the user employee has corresponding related reporting manager object in EmployeeWorkInformation model
#     args:
#         user    : request.user
#     """
    
#     employee =user.employee_get
#     employee_manages = employee.reporting_manager.all()
#     return employee_manages.exists()


@register.filter(name='checkmanager')
def checkmanager(user,employee):
    """
    This filter method is used to check request user is manager of the employee
    args:
        user        : request.user
        employee    : employee instance

    """
    
    employee_user = user.employee_get
    employee_manager = employee.employee_work_info.reporting_manager_id
    return bool(
        employee_user == employee_manager
        or user.is_superuser
        or user.has_perm('attendance.change_attendance')
    )


@register.filter(name='is_clocked_in')
def is_clocked_in(user):
    """
    This filter method is used to check the user is clocked in or not
    args:
        user    : request.user
    """
    
    try:
        employee = user.employee_get
        employee.employee_work_info
    except:
        return False
    date_today = datetime.date.today()
    last_attendance = employee.employee_attendances.all().order_by('attendance_date','id').last()
    if last_attendance is not None:
        last_activity = employee.employee_attendance_activities.filter(attendance_date = last_attendance.attendance_date).last()
        return False if last_activity is None else last_activity.clock_out is None
    return False




class DynamicRegroupNode(template.Node):
    def __init__(self, target, parser, expression, var_name):
        self.target = target
        self.expression = template.Variable(expression)
        self.var_name = var_name
        self.parser = parser

    def render(self, context):
        obj_list = self.target.resolve(context, True)
        if obj_list == None:
            # target variable wasn't found in context; fail silently.
            context[self.var_name] = []
            return ''
        # List of dictionaries in the format:
        # {'grouper': 'key', 'list': [list of contents]}.

        """
        Try to resolve the filter expression from the template context.
        If the variable doesn't exist, accept the value that passed to the
        template tag and convert it to a string
        """
        try:
            exp = self.expression.resolve(context)
        except template.VariableDoesNotExist:
            exp = str(self.expression)

        filter_exp = self.parser.compile_filter(exp)

        context[self.var_name] = [
            {'grouper': key, 'list': list(val)}
            for key, val in
            groupby(obj_list, lambda v, f=filter_exp.resolve: f(v, True))
        ]

        return ''

@register.tag
def dynamic_regroup(parser, token):
    firstbits = token.contents.split(None, 3)
    if len(firstbits) != 4:
        raise TemplateSyntaxError("'regroup' tag takes five arguments")
    target = parser.compile_filter(firstbits[1])
    if firstbits[2] != 'by':
        raise TemplateSyntaxError("second argument to 'regroup' tag must be 'by'")
    lastbits_reversed = firstbits[3][::-1].split(None, 2)
    if lastbits_reversed[1][::-1] != 'as':
        raise TemplateSyntaxError("next-to-last argument to 'regroup' tag must"
                                  " be 'as'")

    """
    Django expects the value of `expression` to be an attribute available on
    your objects. The value you pass to the template tag gets converted into a
    FilterExpression object from the literal.
    
    Sometimes we need the attribute to group on to be dynamic. So, instead
    of converting the value to a FilterExpression here, we're going to pass the
    value as-is and convert it in the Node.
    """
    expression = lastbits_reversed[2][::-1]
    var_name = lastbits_reversed[0][::-1]

    """
    We also need to hand the parser to the node in order to convert the value
    for `expression` to a FilterExpression.
    """
    return DynamicRegroupNode(target, parser, expression, var_name)


@register.filter(name='any_permission')
def any_permission(user,app_label):
    return user.has_module_perms(app_label)