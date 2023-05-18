
import datetime
from typing import Any
from django.forms import widgets
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.models import Group, Permission
from base.models import Company, Department, JobPosition, JobRole, WorkType, EmployeeType, EmployeeShift, EmployeeShiftSchedule, RotatingShift, RotatingShiftAssign, RotatingWorkType, RotatingWorkTypeAssign, WorkTypeRequest, ShiftRequest, EmployeeShiftDay
from django.forms import DateInput
from django.core.exceptions import ValidationError
from employee.models import Employee
import uuid
import re
import calendar
from notifications.signals import notify
from datetime import timedelta
from django.utils.translation import gettext as _

# your form here


def validate_time_format(value):
    '''
    this method is used to validate the format of duration like fields.
    '''
    if len(value) > 6:
        raise ValidationError("Invalid format, it should be HH:MM format")
    try:
        hour, minute = value.split(":")
        hour = int(hour)
        minute = int(minute)
        if len(str(hour)) > 3 or minute not in range(60):
            raise ValidationError("Invalid time")
    except ValueError as e:
        raise ValidationError("Invalid format") from e


BASED_ON = [
    ('after', 'After'),
    ('weekly', 'Weekend'),
    ('monthly', 'Monthly'),
]


def get_next_week_date(target_day, start_date):
    """
    Calculates the date of the next occurrence of the target day within the next week.

    Parameters:
        target_day (int): The target day of the week (0-6, where Monday is 0 and Sunday is 6).
        start_date (datetime.date): The starting date.

    Returns:
        datetime.date: The date of the next occurrence of the target day within the next week.
"""
    if start_date.weekday() == target_day:
        return start_date
    days_until_target_day = (target_day - start_date.weekday()) % 7
    if days_until_target_day == 0:
        days_until_target_day = 7
    return start_date + timedelta(days=days_until_target_day)


def get_next_monthly_date(start_date, rotate_every):
    """
    Given a start date and a rotation day (specified as an integer between 1 and 31, or the string 'last'), calculates the
    next rotation date for a monthly rotation schedule.

    If the rotation day has not yet occurred in the current month, the next rotation date will be on the rotation day
    of the current month. If the rotation day has already occurred in the current month, the next rotation date will be on
    the rotation day of the next month.

    If 'last' is specified as the rotation day, the next rotation date will be on the last day of the current month.

    Parameters:
    - start_date: The start date of the rotation schedule, as a datetime.date object.
    - rotate_every: The rotation day, specified as an integer between 1 and 31, or the string 'last'.

    Returns:
    - A datetime.date object representing the next rotation date.
    """

    if rotate_every == 'last':
        # Set rotate_every to the last day of the current month
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        rotate_every = str(last_day)
    rotate_every = int(rotate_every)

    # Calculate the next change date
    if start_date.day <= rotate_every or rotate_every == 0:
        # If the rotation day has not occurred yet this month, or if it's the last day of the month, set the next change date to the rotation day of this month
        try:
            next_change = datetime.date(
                start_date.year, start_date.month, rotate_every)
        except ValueError:
            next_change = datetime.date(
                start_date.year, start_date.month + 1, 1)  # Advance to next month
            # Set day to rotate_every
            next_change = datetime.date(
                next_change.year, next_change.month, rotate_every)
    else:
        # If the rotation day has already occurred this month, set the next change date to the rotation day of the next month
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        next_month_start = start_date.replace(day=last_day) + timedelta(days=1)
        try:
            next_change = next_month_start.replace(day=rotate_every)
        except ValueError:
            next_change = (next_month_start.replace(
                month=next_month_start.month + 1) + timedelta(days=1)).replace(day=rotate_every)

    return next_change


class ModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget,(forms.NumberInput, forms.EmailInput, forms.TextInput, forms.FileInput)):
                if field.label is not None:
                    label = _(field.label.title())
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label})
            elif isinstance(widget, (forms.Select,)):
                label = ""
                if field.label is not None:
                    label = _(field.label)
                field.empty_label = _("---Choose {label}---").format(label=label)
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"})
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update({"class": "oh-input w-100","placeholder": _(field.label),"rows": 2,"cols": 40,})
            elif isinstance(widget,(forms.CheckboxInput,forms.CheckboxSelectMultiple,)):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})


class Form(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)):
                label = _(field.label)
                field.widget.attrs.update({"class": "oh-input w-100", "placeholder": label})
            elif isinstance(widget, (forms.Select,)):
                label = ""
                if field.label is not None:
                    label = field.label.replace("id", " ")
                field.empty_label = _("---Choose {label}---").format(label=label)
                field.widget.attrs.update({"class": "oh-select oh-select-2 select2-hidden-accessible"})
            elif isinstance(widget, (forms.Textarea)):
                label = _(field.label)
                field.widget.attrs.update({"class": "oh-input w-100","placeholder": label,"rows": 2,"cols": 40,})
            elif isinstance(widget,(forms.CheckboxInput,forms.CheckboxSelectMultiple,)):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})



class UserGroupForm(ModelForm):
    class Meta:
        model = Group
        fields = '__all__'


class AssignUserGroup(Form):
    employee = forms.ModelMultipleChoiceField(queryset=Employee.objects.all())
    group = forms.ModelMultipleChoiceField(queryset=Group.objects.all())

    def save(self):
        employees = self.cleaned_data['employee']
        group = self.cleaned_data['group']
        for employee in employees:
            employee.employee_user_id.groups.add(*group)

        return group


class AssignPermission(Form):
    employee = forms.ModelMultipleChoiceField(queryset=Employee.objects.all())
    permission = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all())

    def save(self):
        employees = self.cleaned_data['employee']
        permissions = self.cleaned_data['permission']
        for emp in employees:
            user = emp.employee_user_id
            user.user_permissions.add(*permissions)
        return


class CompanyForm(ModelForm):
    class Meta:
        model = Company
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CompanyForm, self).__init__(*args, **kwargs)


class DepartmentForm(ModelForm):
    class Meta:
        model = Department
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(DepartmentForm, self).__init__(*args, **kwargs)


class JobPositionForm(ModelForm):
    class Meta:
        model = JobPosition
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(JobPositionForm, self).__init__(*args, **kwargs)


class JobRoleForm(ModelForm):
    class Meta:
        model = JobRole
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(JobRoleForm, self).__init__(*args, **kwargs)


class WorkTypeForm(ModelForm):
    class Meta:
        model = WorkType
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(WorkTypeForm, self).__init__(*args, **kwargs)


class RotatingWorkTypeForm(ModelForm):
    class Meta:
        model = RotatingWorkType
        fields = '__all__'
        exclude = ('employee_id',)
        widgets = {
            'start_date': DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(RotatingWorkTypeForm, self).__init__(*args, **kwargs)


class RotatingWorkTypeAssignForm(forms.ModelForm):
    employee_id = forms.ModelMultipleChoiceField(
        label="Employee", queryset=Employee.objects.filter(employee_work_info__isnull=False))
    based_on = forms.ChoiceField(choices=BASED_ON, initial='daily')
    rotate_after_day = forms.IntegerField(initial=5,)
    start_date = forms.DateField(
        initial=datetime.date.today, widget=forms.DateInput)

    class Meta:
        model = RotatingWorkTypeAssign
        fields = '__all__'
        exclude = ('next_change_date', 'current_work_type', 'next_work_type')
        widgets = {
            'start_date': DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'rotating_work_type_id': 'Rotating work type',
        }

    def __init__(self, *args, **kwargs):
        super(RotatingWorkTypeAssignForm, self).__init__(*args, **kwargs)

        self.fields['rotate_every_weekend'].widget.attrs.update(
            {'class': 'w-100', 'style': 'display:none; height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);', 'data-hidden': True})
        self.fields['rotate_every'].widget.attrs.update(
            {'class': 'w-100', 'style': 'display:none; height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);', 'data-hidden': True})
        self.fields['rotate_after_day'].widget.attrs.update(
            {'class': 'w-100 oh-input', 'style': ' height:50px; border-radius:0;', })
        self.fields['based_on'].widget.attrs.update(
            {'class': 'w-100', 'style': ' height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);', })
        self.fields['start_date'].widget = forms.DateInput(
            attrs={'class': 'w-100 oh-input', 'type': 'date', 'style': ' height:50px; border-radius:0;', })
        self.fields['rotating_work_type_id'].widget.attrs.update(
            {'class': 'oh-select oh-select-2', })
        self.fields['employee_id'].widget.attrs.update(
            {'class': 'oh-select oh-select-2', })

    def clean_employee_id(self):
        employee_ids = self.cleaned_data.get('employee_id')
        if employee_ids:
            return employee_ids[0]
        else:
            return ValidationError('This field is required')

    def clean(self):
        cleaned_data = super().clean()
        if 'rotate_after_day' in self.errors:
            del self.errors['rotate_after_day']
        return cleaned_data

    def save(self, commit=False, manager=None):
        employee_ids = self.data.getlist('employee_id')
        rotating_work_type = RotatingWorkType.objects.get(
            id=self.data['rotating_work_type_id'])

        day_name = self.cleaned_data['rotate_every_weekend']
        day_names = ["monday", "tuesday", "wednesday",
                     "thursday", "friday", "saturday", "sunday"]
        target_day = day_names.index(day_name.lower())

        for employee_id in employee_ids:
            employee = Employee.objects.filter(id=employee_id).first()
            rotating_work_type_assign = RotatingWorkTypeAssign()
            rotating_work_type_assign.rotating_work_type_id = rotating_work_type
            rotating_work_type_assign.employee_id = employee
            rotating_work_type_assign.based_on = self.cleaned_data['based_on']
            rotating_work_type_assign.start_date = self.cleaned_data['start_date']
            rotating_work_type_assign.next_change_date = self.cleaned_data['start_date']
            rotating_work_type_assign.rotate_after_day = self.data.get(
                'rotate_after_day')
            rotating_work_type_assign.rotate_every = self.cleaned_data['rotate_every']
            rotating_work_type_assign.rotate_every_weekend = self.cleaned_data[
                'rotate_every_weekend']
            rotating_work_type_assign.next_change_date = self.cleaned_data['start_date']
            rotating_work_type_assign.current_work_type = employee.employee_work_info.work_type_id
            rotating_work_type_assign.next_work_type = rotating_work_type.work_type2
            based_on = self.cleaned_data['based_on']
            start_date = self.cleaned_data['start_date']
            if based_on == "weekly":
                next_date = get_next_week_date(target_day, start_date)
                rotating_work_type_assign.next_change_date = next_date
            elif based_on == "monthly":
                # 0, 1, 2, ..., 31, or "last"
                rotate_every = self.cleaned_data['rotate_every']
                start_date = self.cleaned_data['start_date']
                next_date = get_next_monthly_date(start_date, rotate_every)
                rotating_work_type_assign.next_change_date = next_date
            elif based_on == "after":
                rotating_work_type_assign.next_change_date = rotating_work_type_assign.start_date + \
                    datetime.timedelta(
                        days=int(self.data.get('rotate_after_day')))

            rotating_work_type_assign.save()


class RotatingWorkTypeAssignUpdateForm(forms.ModelForm):
    class Meta:
        model = RotatingWorkTypeAssign
        fields = '__all__'
        exclude = ('next_change_date', 'current_work_type', 'next_work_type')
        widgets = {
            'start_date': DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(RotatingWorkTypeAssignUpdateForm, self).__init__(*args, **kwargs)

        self.fields['rotate_every_weekend'].widget.attrs.update(
            {'class': 'w-100', 'style': 'display:none; height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);', 'data-hidden': True})
        self.fields['rotate_every'].widget.attrs.update(
            {'class': 'w-100', 'style': 'display:none; height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);', 'data-hidden': True})
        self.fields['rotate_after_day'].widget.attrs.update(
            {'class': 'w-100 oh-input', 'style': ' height:50px; border-radius:0;', })
        self.fields['based_on'].widget.attrs.update(
            {'class': 'w-100', 'style': ' height:50px; border-radius:0; border:1px solid hsl(213deg,22%,84%);', })
        self.fields['start_date'].widget = forms.DateInput(
            attrs={'class': 'w-100 oh-input', 'type': 'date', 'style': ' height:50px; border-radius:0;', })
        self.fields['rotating_work_type_id'].widget.attrs.update(
            {'class': 'oh-select oh-select-2', })
        self.fields['employee_id'].widget.attrs.update(
            {'class': 'oh-select oh-select-2', })

    def save(self, *args, **kwargs):

        day_name = self.cleaned_data['rotate_every_weekend']
        day_names = ["monday", "tuesday", "wednesday",
                     "thursday", "friday", "saturday", "sunday"]
        target_day = day_names.index(day_name.lower())

        based_on = self.cleaned_data['based_on']
        start_date = self.instance.start_date
        if based_on == "weekly":
            next_date = get_next_week_date(target_day, start_date)
            self.instance.next_change_date = next_date
        elif based_on == "monthly":
            rotate_every = self.instance.rotate_every  # 0, 1, 2, ..., 31, or "last"
            start_date = self.instance.start_date
            next_date = get_next_monthly_date(start_date, rotate_every)
            self.instance.next_change_date = next_date
        elif based_on == "after":
                self.instance.next_change_date = self.instance.start_date + \
                    datetime.timedelta(
                        days=int(self.data.get('rotate_after_day')))
        return super().save()


class EmployeeTypeForm(ModelForm):
    class Meta:
        model = EmployeeType
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(EmployeeTypeForm, self).__init__(*args, **kwargs)


class EmployeeShiftForm(ModelForm):
    class Meta:
        model = EmployeeShift
        fields = '__all__'
        exclude = ('days',)

    def __init__(self, *args, **kwargs):
        super(EmployeeShiftForm, self).__init__(*args, **kwargs)

    def clean_full_time(self):
        full_time = self.cleaned_data['full_time']
        validate_time_format(full_time)
        return full_time


class EmployeeShiftScheduleUpdateForm(ModelForm):

    class Meta:
        fields = '__all__'
        widgets = {
            'start_time': DateInput(attrs={'type': 'time'}),
            'end_time': DateInput(attrs={'type': 'time'}),

        }
        model = EmployeeShiftSchedule

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get('instance'):
            '''
            django forms not showing value inside the date, time html element. 
            so here overriding default forms instance method to set initial value
            '''
            initial = {
                'start_time': instance.start_time.strftime('%H:%M'),
                'end_time': instance.end_time.strftime('%H:%M'),
            }
            kwargs['initial'] = initial
        super().__init__(*args, **kwargs)


class EmployeeShiftScheduleForm(ModelForm):
    day = forms.ModelMultipleChoiceField(
        queryset=EmployeeShiftDay.objects.all(),)

    class Meta:

        model = EmployeeShiftSchedule
        fields = '__all__'
        widgets = {
            'start_time': DateInput(attrs={'type': 'time'}),
            'end_time': DateInput(attrs={'type': 'time'}),

        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get('instance'):
            '''
            django forms not showing value inside the date, time html element. 
            so here overriding default forms instance method to set initial value
            '''
            initial = {
                'start_time': instance.start_time.strftime('%H:%M'),
                'end_time': instance.end_time.strftime('%H:%M'),
            }
            kwargs['initial'] = initial
        super(EmployeeShiftScheduleForm, self).__init__(*args, **kwargs)
        self.fields['day'].widget.attrs.update({'id': str(uuid.uuid4())})
        self.fields['shift_id'].widget.attrs.update({'id': str(uuid.uuid4())})

    def save(self, commit=True):
        instance = super().save(commit=False)
        for day in self.data.getlist('day'):
            if int(day) != int(instance.day.id):
                data_copy = self.data.copy()
                data_copy.update({'day': str(day)})
                shift_schedule = EmployeeShiftScheduleUpdateForm(
                    data_copy).save(commit=False)
                shift_schedule.save()
        if commit:
            instance.save()
        return instance

    def clean_day(self):
        days = self.cleaned_data['day']
        for day in days:
            attendance = EmployeeShiftSchedule.objects.filter(
                day=day, shift_id=self.data['shift_id']).first()
            if attendance is not None:
                raise ValidationError(
                    f'Shift schedule is already exist for {day}')
        if days.first() is None:
            raise ValidationError('Employee not chosen')

        return days.first()


class RotatingShiftForm(ModelForm):
    class Meta:
        model = RotatingShift
        fields = '__all__'
        exclude = ('employee_id',)

    def __init__(self, *args, **kwargs):
        super(RotatingShiftForm, self).__init__(*args, **kwargs)


class RotatingShiftAssignForm(forms.ModelForm):
    employee_id = forms.ModelMultipleChoiceField(
        label="Employee", queryset=Employee.objects.filter(employee_work_info__isnull=False))
    based_on = forms.ChoiceField(choices=BASED_ON, initial='daily')
    rotate_after_day = forms.IntegerField(initial=5,)
    start_date = forms.DateField(
        initial=datetime.date.today, widget=forms.DateInput)

    class Meta:
        model = RotatingShiftAssign
        fields = '__all__'
        exclude = ('next_change_date', 'current_shift', 'next_shift')
        widgets = {
            'start_date': DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'rotating_shift_id': 'Rotating shift',
        }

    def __init__(self, *args, **kwargs):
        super(RotatingShiftAssignForm, self).__init__(*args, **kwargs)
        self.fields['rotate_every_weekend'].widget.attrs.update(
            {'class': 'w-100 ', 'style': 'display:none; height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);', 'data-hidden': True})
        self.fields['rotate_every'].widget.attrs.update(
            {'class': 'w-100 ', 'style': 'display:none; height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);', 'data-hidden': True})
        self.fields['rotate_after_day'].widget.attrs.update(
            {'class': 'w-100 oh-input', 'style': ' height:50px; border-radius:0;', })
        self.fields['based_on'].widget.attrs.update(
            {'class': 'w-100', 'style': ' height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);', })
        self.fields['start_date'].widget = forms.DateInput(
            attrs={'class': 'w-100 oh-input', 'type': 'date', 'style': ' height:50px; border-radius:0;', })
        self.fields['rotating_shift_id'].widget.attrs.update(
            {'class': 'oh-select oh-select-2', })
        self.fields['employee_id'].widget.attrs.update(
            {'class': 'oh-select oh-select-2', })

    def clean_employee_id(self):
        employee_ids = self.cleaned_data.get('employee_id')
        if employee_ids:
            return employee_ids[0]
        else:
            return ValidationError('This field is required')

    def clean(self):
        cleaned_data = super().clean()
        if 'rotate_after_day' in self.errors:
            del self.errors['rotate_after_day']
        return cleaned_data

    def save(self, commit=False,):
        employee_ids = self.data.getlist('employee_id')
        rotating_shift = RotatingShift.objects.get(
            id=self.data['rotating_shift_id'])

        day_name = self.cleaned_data['rotate_every_weekend']
        day_names = ["monday", "tuesday", "wednesday",
                     "thursday", "friday", "saturday", "sunday"]
        target_day = day_names.index(day_name.lower())

        for employee_id in employee_ids:
            employee = Employee.objects.filter(id=employee_id).first()
            rotating_shift_assign = RotatingShiftAssign()
            rotating_shift_assign.rotating_shift_id = rotating_shift
            rotating_shift_assign.employee_id = employee
            rotating_shift_assign.based_on = self.cleaned_data['based_on']
            rotating_shift_assign.start_date = self.cleaned_data['start_date']
            rotating_shift_assign.next_change_date = self.cleaned_data['start_date']
            rotating_shift_assign.rotate_after_day = self.data.get(
                'rotate_after_day')
            rotating_shift_assign.rotate_every = self.cleaned_data['rotate_every']
            rotating_shift_assign.rotate_every_weekend = self.cleaned_data['rotate_every_weekend']
            rotating_shift_assign.next_change_date = self.cleaned_data['start_date']
            rotating_shift_assign.current_shift = employee.employee_work_info.shift_id
            rotating_shift_assign.next_shift = rotating_shift.shift2
            based_on = self.cleaned_data['based_on']
            start_date = self.cleaned_data['start_date']
            if based_on == "weekly":
                next_date = get_next_week_date(target_day, start_date)
                rotating_shift_assign.next_change_date = next_date
            elif based_on == "monthly":
                # 0, 1, 2, ..., 31, or "last"
                rotate_every = self.cleaned_data['rotate_every']
                start_date = self.cleaned_data['start_date']
                next_date = get_next_monthly_date(start_date, rotate_every)
                rotating_shift_assign.next_change_date = next_date
            elif based_on == "after":
                rotating_shift_assign.next_change_date = rotating_shift_assign.start_date + \
                    datetime.timedelta(
                        days=int(self.data.get('rotate_after_day')))

            rotating_shift_assign.save()


class RotatingShiftAssignUpdateForm(forms.ModelForm):

    class Meta:
        model = RotatingShiftAssign
        fields = '__all__'
        exclude = ('next_change_date', 'current_shift', 'next_shift')
        widgets = {
            'start_date': DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(RotatingShiftAssignUpdateForm, self).__init__(*args, **kwargs)
        self.fields['rotate_every_weekend'].widget.attrs.update(
            {'class': 'w-100 ', 'style': 'display:none; height:50px; border-radius:0; border:1px solid hsl(213deg,22%,84%);', 'data-hidden': True})
        self.fields['rotate_every'].widget.attrs.update(
            {'class': 'w-100 ', 'style': 'display:none; height:50px; border-radius:0; border:1px solid hsl(213deg,22%,84%);', 'data-hidden': True})
        self.fields['rotate_after_day'].widget.attrs.update(
            {'class': 'w-100 oh-input', 'style': ' height:50px; border-radius:0;', })
        self.fields['based_on'].widget.attrs.update(
            {'class': 'w-100', 'style': ' height:50px; border-radius:0; border:1px solid hsl(213deg,22%,84%);', })
        self.fields['start_date'].widget = forms.DateInput(
            attrs={'class': 'w-100 oh-input', 'type': 'date', 'style': ' height:50px; border-radius:0;', })
        self.fields['rotating_shift_id'].widget.attrs.update(
            {'class': 'oh-select oh-select-2', })
        self.fields['employee_id'].widget.attrs.update(
            {'class': 'oh-select oh-select-2', })

    def save(self, *args, **kwargs):

        day_name = self.cleaned_data['rotate_every_weekend']
        day_names = ["monday", "tuesday", "wednesday",
                     "thursday", "friday", "saturday", "sunday"]
        target_day = day_names.index(day_name.lower())

        based_on = self.cleaned_data['based_on']
        start_date = self.instance.start_date
        if based_on == "weekly":
            next_date = get_next_week_date(target_day, start_date)
            self.instance.next_change_date = next_date
        elif based_on == "monthly":
            rotate_every = self.instance.rotate_every  # 0, 1, 2, ..., 31, or "last"
            start_date = self.instance.start_date
            next_date = get_next_monthly_date(start_date, rotate_every)
            self.instance.next_change_date = next_date
        elif based_on == "after":
                self.instance.next_change_date = self.instance.start_date + \
                    datetime.timedelta(
                        days=int(self.data.get('rotate_after_day')))
        return super().save()


class ShiftRequestForm(ModelForm):

    class Meta:
        model = ShiftRequest
        fields = '__all__'
        exclude = ('approved', 'canceled', 'previous_shift_id',
                   'is_active', 'shift_changed')
        widgets = {
            'requested_date': DateInput(attrs={'type': 'date'}),
            'requested_till': DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'employee_id': 'Employee',
            'shift_id': 'Shift'
        }

    def save(self, commit: bool = ...):
        if not self.instance.approved:
            employee = self.instance.employee_id
            self.instance.previous_shift_id = employee.employee_work_info.shift_id
        return super().save(commit)

    # here set default filter for all the employees those have work information filled.


class WorkTypeRequestForm(ModelForm):
    class Meta:
        model = WorkTypeRequest
        fields = '__all__'
        exclude = ('approved', 'canceled', 'previous_work_type_id',
                   'is_active', 'work_type_changed')
        widgets = {
            'requested_date': DateInput(attrs={'type': 'date'}),
            'requested_till': DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'employee_id': 'Employee',
            'work_type_id': 'Work type'
        }

    def save(self, commit: bool = ...):
        if not self.instance.approved:
            employee = self.instance.employee_id
            self.instance.previous_work_type_id = employee.employee_work_info.work_type_id
        return super().save(commit)


class ResetPasswordForm(forms.Form):
    password = forms.CharField(
        label="New password",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password',
                                   'placeholder': 'Enter Strong Password', 'class': 'oh-input oh-input--password w-100 mb-2'}),
        help_text="Enter your new password.",
    )
    confirm_password = forms.CharField(
        label="New password confirmation",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password',
                                   'placeholder': 'Re-Enter Password', 'class': 'oh-input oh-input--password w-100 mb-2'}),
        help_text="Enter the same password as before, for verification.",
    )

    def clean_password(self):
        password = self.cleaned_data.get('password')
        try:

            if len(password) < 7:
                raise ValidationError(
                    'Password must contain at least 8 characters.')
            elif not any(char.isupper() for char in password):
                raise ValidationError(
                    'Password must contain at least one uppercase letter.')
            elif not any(char.islower() for char in password):
                raise ValidationError(
                    'Password must contain at least one lowercase letter.')
            elif not any(char.isdigit() for char in password):
                raise ValidationError(
                    'Password must contain at least one digit.')
            elif all(
                char not in '!@#$%^&*()_+-=[]{}|;:,.<>?\'\"`~\\/'
                for char in password
            ):
                raise ValidationError(
                    'Password must contain at least one special character.')
        except ValidationError as e:
            raise forms.ValidationError(list(e)[0])
        return password

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password == confirm_password:
            return confirm_password
        raise forms.ValidationError('Password must be same.')

    def save(self, *args, user=None, **kwargs):
        if user is not None:
            user.set_password(self.data['password'])
            user.save()
