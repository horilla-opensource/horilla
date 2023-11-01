from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, date
import calendar
from notifications.signals import notify


def update_rotating_work_type_assign(rotating_work_type, new_date):
    """
    Here will update the employee work information details and send notification
    """
    from django.contrib.auth.models import User

    employee = rotating_work_type.employee_id
    employee_work_info = employee.employee_work_info
    work_type1 = rotating_work_type.rotating_work_type_id.work_type1
    work_type2 = rotating_work_type.rotating_work_type_id.work_type2
    new = rotating_work_type.next_work_type
    next = work_type2
    if new == next:
        next = work_type1
    employee_work_info.work_type_id = new
    employee_work_info.save()
    rotating_work_type.next_change_date = new_date
    rotating_work_type.current_work_type = new
    rotating_work_type.next_work_type = next
    rotating_work_type.save()
    bot = User.objects.filter(username="Horilla Bot").first()
    if bot is not None:
        employee = rotating_work_type.employee_id
        notify.send(
            bot,
            recipient=employee.employee_user_id,
            verb="Your Work Type has been changed.",
            verb_ar="لقد تغير نوع عملك.",
            verb_de="Ihre Art der Arbeit hat sich geändert.",
            verb_es="Su tipo de trabajo ha sido cambiado.",
            verb_fr="Votre type de travail a été modifié.",
            icon="infinite",
            redirect="/employee/employee-profile",
        )
    return


def work_type_rotate_after(rotating_work_work_type):
    """
    This method for rotate work type based on after day
    """
    date_today = datetime.now()
    switch_date = rotating_work_work_type.next_change_date
    if switch_date.strftime("%Y-%m-%d") == date_today.strftime("%Y-%m-%d"):
        # calculate the next work type switch date
        new_date = date_today + timedelta(days=rotating_work_work_type.rotate_after_day)
        update_rotating_work_type_assign(rotating_work_work_type, new_date)
    return


def work_type_rotate_weekend(rotating_work_type):
    """
    This method for rotate work type based on weekend
    """
    date_today = datetime.now()
    switch_date = rotating_work_type.next_change_date
    if switch_date.strftime("%Y-%m-%d") == date_today.strftime("%Y-%m-%d"):
        # calculate the next work type switch date
        day = datetime.now().strftime("%A").lower()
        switch_day = rotating_work_type.rotate_every_weekend
        if day == switch_day:
            new_date = date_today + timedelta(days=7)
            update_rotating_work_type_assign(rotating_work_type, new_date)
    return


def work_type_rotate_every(rotating_work_type):
    """
    This method for rotate work type based on every month
    """
    date_today = datetime.now()
    switch_date = rotating_work_type.next_change_date
    day_date = rotating_work_type.rotate_every
    if switch_date.strftime("%Y-%m-%d") == date_today.strftime("%Y-%m-%d"):
        # calculate the next work type switch date
        if day_date == switch_date.strftime("%d").lstrip("0"):
            new_date = date_today.replace(month=date_today.month + 1)
            update_rotating_work_type_assign(rotating_work_type, new_date)
        elif day_date == "last":
            year = date_today.strftime("%Y")
            month = date_today.strftime("%m")
            last_day = calendar.monthrange(int(year), int(month) + 1)[1]
            new_date = datetime(int(year), int(month) + 1, last_day)
            update_rotating_work_type_assign(rotating_work_type, new_date)
    return


def rotate_work_type():
    """
    This method will identify the based on condition to the rotating shift assign
    and redirect to the chunk method to execute.
    """
    from base.models import RotatingWorkTypeAssign

    rotating_work_types = RotatingWorkTypeAssign.objects.filter(is_active=True)
    for rotating_work_type in rotating_work_types:
        based_on = rotating_work_type.based_on
        if based_on == "after":
            work_type_rotate_after(rotating_work_type)
        elif based_on == "weekly":
            work_type_rotate_weekend(rotating_work_type)
        elif based_on == "monthly":
            work_type_rotate_every(rotating_work_type)
    return


def update_rotating_shift_assign(rotating_shift, new_date):
    """
    Here will update the employee work information and send notification
    """
    from django.contrib.auth.models import User

    employee = rotating_shift.employee_id
    employee_work_info = employee.employee_work_info
    shift1 = rotating_shift.rotating_shift_id.shift1
    shift2 = rotating_shift.rotating_shift_id.shift2
    new = rotating_shift.next_shift
    next = shift2
    if new == next:
        next = shift1
    employee_work_info.shift_id = new
    employee_work_info.save()
    rotating_shift.next_change_date = new_date
    rotating_shift.current_shift = new
    rotating_shift.next_shift = next
    rotating_shift.save()
    bot = User.objects.filter(username="Horilla Bot").first()
    if bot is not None:
        employee = rotating_shift.employee_id
        notify.send(
            bot,
            recipient=employee.employee_user_id,
            verb="Your shift has been changed.",
            verb_ar="تم تغيير التحول الخاص بك.",
            verb_de="Ihre Schicht wurde geändert.",
            verb_es="Tu turno ha sido cambiado.",
            verb_fr="Votre quart de travail a été modifié.",
            icon="infinite",
            redirect="/employee/employee-profile",
        )
    return


def shift_rotate_after_day(rotating_shift):
    """
    This method for rotate shift based on after day
    """
    date_today = datetime.now()
    switch_date = rotating_shift.next_change_date
    if switch_date.strftime("%Y-%m-%d") == date_today.strftime("%Y-%m-%d"):
        # calculate the next work type switch date
        new_date = date_today + timedelta(days=rotating_shift.rotate_after_day)
        update_rotating_shift_assign(rotating_shift, new_date)
    return


def shift_rotate_weekend(rotating_shift):
    """
    This method for rotate shift based on weekend
    """
    date_today = datetime.now()
    switch_date = rotating_shift.next_change_date
    if switch_date.strftime("%Y-%m-%d") == date_today.strftime("%Y-%m-%d"):
        # calculate the next work type switch date
        day = datetime.now().strftime("%A").lower()
        switch_day = rotating_shift.rotate_every_weekend
        if day == switch_day:
            new_date = date_today + timedelta(days=7)
            update_rotating_shift_assign(rotating_shift, new_date)
    return


def shift_rotate_every(rotating_shift):
    """
    This method for rotate shift based on every month
    """
    date_today = datetime.now()
    switch_date = rotating_shift.next_change_date
    day_date = rotating_shift.rotate_every
    if switch_date.strftime("%Y-%m-%d") == date_today.strftime("%Y-%m-%d"):
        # calculate the next work type switch date
        if day_date == switch_date.strftime("%d").lstrip("0"):
            new_date = date_today.replace(month=date_today.month + 1)
            update_rotating_shift_assign(rotating_shift, new_date)
        elif day_date == "last":
            year = date_today.strftime("%Y")
            month = date_today.strftime("%m")
            last_day = calendar.monthrange(int(year), int(month) + 1)[1]
            new_date = datetime(int(year), int(month) + 1, last_day)
            update_rotating_shift_assign(rotating_shift, new_date)
    return


def rotate_shift():
    """
    This method will identify the based on condition to the rotating shift assign
    and redirect to the chunk method to execute.
    """
    from base.models import RotatingShiftAssign

    rotating_shifts = RotatingShiftAssign.objects.filter(is_active=True)
    for rotating_shift in rotating_shifts:
        based_on = rotating_shift.based_on
        # after day condition
        if based_on == "after":
            shift_rotate_after_day(rotating_shift)
        # weekly condition
        elif based_on == "weekly":
            shift_rotate_weekend(rotating_shift)
        # monthly condition
        elif based_on == "monthly":
            shift_rotate_every(rotating_shift)

    return


def switch_shift():
    """
    This method change employees shift information regards to the shift request
    """
    from base.models import ShiftRequest
    from django.contrib.auth.models import User

    today = date.today()

    shift_requests = ShiftRequest.objects.filter(
        canceled=False, approved=True, requested_date__exact=today, shift_changed=False
    )
    if shift_requests:
        for request in shift_requests:
            work_info = request.employee_id.employee_work_info
            # updating requested shift to the employee work information.
            work_info.shift_id = request.shift_id
            work_info.save()
            request.approved = True
            request.shift_changed = True
            request.save()
            bot = User.objects.filter(username="Horilla Bot").first()
            if bot is not None:
                employee = request.employee_id
                notify.send(
                    bot,
                    recipient=employee.employee_user_id,
                    verb="Shift Changes notification",
                    verb_ar="التحول تغيير الإخطار",
                    verb_de="Benachrichtigung über Schichtänderungen",
                    verb_es="Notificación de cambios de turno",
                    verb_fr="Notification des changements de quart de travail",
                    icon="refresh",
                    redirect="/employee/employee-profile",
                )
    return


def undo_shift():
    """
    This method undo previous employees shift information regards to the shift request
    """
    from base.models import ShiftRequest
    from django.contrib.auth.models import User

    today = date.today()
    # here will get all the active shift requests
    shift_requests = ShiftRequest.objects.filter(
        canceled=False,
        approved=True,
        requested_till__lt=today,
        is_active=True,
        shift_changed=True,
    )
    if shift_requests:
        for request in shift_requests:
            work_info = request.employee_id.employee_work_info
            work_info.shift_id = request.previous_shift_id
            work_info.save()
            # making the instance in-active
            request.is_active = False
            request.save()
            bot = User.objects.filter(username="Horilla Bot").first()
            if bot is not None:
                employee = request.employee_id
                notify.send(
                    bot,
                    recipient=employee.employee_user_id,
                    verb="Shift changes notification, Requested date expired.",
                    verb_ar="التحول يغير الإخطار ، التاريخ المطلوب انتهت صلاحيته.",
                    verb_de="Benachrichtigung über Schichtänderungen, gewünschtes Datum abgelaufen.",
                    verb_es="Notificación de cambios de turno, Fecha solicitada vencida.",
                    verb_fr="Notification de changement d'équipe, la date demandée a expiré.",
                    icon="refresh",
                    redirect="/employee/employee-profile",
                )
    return


def switch_work_type():
    """
    This method change employees work type information regards to the work type request
    """
    from django.contrib.auth.models import User
    from base.models import WorkTypeRequest

    today = date.today()
    work_type_requests = WorkTypeRequest.objects.filter(
        canceled=False,
        approved=True,
        requested_date__exact=today,
        work_type_changed=False,
    )
    for request in work_type_requests:
        work_info = request.employee_id.employee_work_info
        # updating requested work type to the employee work information.
        work_info.work_type_id = request.work_type_id
        work_info.save()
        request.approved = True
        request.work_type_changed = True
        request.save()
        bot = User.objects.filter(username="Horilla Bot").first()
        if bot is not None:
            employee = request.employee_id
            notify.send(
                bot,
                recipient=employee.employee_user_id,
                verb="Work Type Changes notification",
                verb_ar="إخطار تغييرات نوع العمل",
                verb_de="Benachrichtigung über Änderungen des Arbeitstyps",
                verb_es="Notificación de cambios de tipo de trabajo",
                verb_fr="Notification de changement de type de travail",
                icon="swap-horizontal",
                redirect="/employee/employee-profile",
            )
    return


def undo_work_type():
    """
    This method undo previous employees work type information regards to the work type request
    """
    from base.models import WorkTypeRequest
    from django.contrib.auth.models import User

    today = date.today()
    # here will get all the active work type requests
    work_type_requests = WorkTypeRequest.objects.filter(
        canceled=False,
        approved=True,
        requested_till__lt=today,
        is_active=True,
        work_type_changed=True,
    )
    for request in work_type_requests:
        work_info = request.employee_id.employee_work_info
        # updating employee work information's work type to previous work type
        work_info.work_type_id = request.previous_work_type_id
        work_info.save()
        # making the instance is in-active
        request.is_active = False
        request.save()
        bot = User.objects.filter(username="Horilla Bot").first()
        if bot is not None:
            employee = request.employee_id
            notify.send(
                bot,
                recipient=employee.employee_user_id,
                verb="Work type changes notification, Requested date expired.",
                verb_ar="إعلام بتغيير نوع العمل ، انتهاء صلاحية التاريخ المطلوب.",
                verb_de="Benachrichtigung über Änderungen des Arbeitstyps, angefordertes Datum abgelaufen.",
                verb_es="Notificación de cambios de tipo de trabajo, fecha solicitada vencida.",
                verb_fr="Notification de changement de type de travail, la date demandée a expiré.",
                icon="swap-horizontal",
                redirect="/employee/employee-profile",
            )
    return


scheduler = BackgroundScheduler()

# Set the initial start time to the current time
start_time = datetime.now()

# Add jobs with next_run_time set to the end of the previous job
scheduler.add_job(
    rotate_shift, "interval", seconds=10, id="job1" )
scheduler.add_job(
    rotate_work_type,
    "interval",
    seconds=10,
    id="job2",
)
scheduler.add_job(
    undo_shift,
    "interval",
    seconds=15,
    id="job3",
)
scheduler.add_job(
    switch_shift,
    "interval",
    seconds=20,
    id="job4",
)
scheduler.add_job(
    undo_work_type,
    "interval",
    seconds=25,
    id="job6",
)
scheduler.add_job(
    switch_work_type,
    "interval",
    seconds=30,
    id="job5",
)

scheduler.start()
