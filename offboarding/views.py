from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from employee.models import Employee
from horilla.decorators import login_required, permission_required
from offboarding.decorators import any_manager_can_enter, offboarding_manager_can_enter, offboarding_or_stage_manager_can_enter
from offboarding.forms import (
    NoteForm,
    OffboardingEmployeeForm,
    OffboardingForm,
    OffboardingStageForm,
    StageSelectForm,
    TaskForm,
)
from offboarding.models import (
    EmployeeTask,
    Offboarding,
    OffboardingEmployee,
    OffboardingNote,
    OffboardingStage,
    OffboardingStageMultipleFile,
    OffboardingTask,
)


# Create your views here.


@login_required
@any_manager_can_enter("offboarding.view_offboarding")
def pipeline(request):
    """
    Offboarding pipleine view
    """
    offboardings = Offboarding.objects.all()
    stage_forms = {}
    for offboarding in offboardings:
        stage_forms[str(offboarding.id)] = StageSelectForm(offboarding=offboarding)
    return render(
        request,
        "offboarding/pipeline/pipeline.html",
        {"offboardings": offboardings, "stage_forms": stage_forms},
    )


@login_required
@permission_required("offboarding.add_offboarding")
def create_offboarding(request):
    """
    Create offboarding view
    """
    instance_id = eval(str(request.GET.get("instance_id")))
    instance = None
    if instance_id and isinstance(instance_id, int):
        instance = Offboarding.objects.filter(id=instance_id).first()
    form = OffboardingForm(instance=instance)
    if request.method == "POST":
        form = OffboardingForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Offboarding saved")
            return HttpResponse("<script>window.location.reload()</script>")

    return render(
        request,
        "offboarding/pipeline/form.html",
        {
            "form": form,
        },
    )


@login_required
@permission_required("offboarding.delete_offboarding")
def delete_offboarding(request):
    """
    This method is used to delete offboardings
    """
    ids = request.GET.getlits("id")
    Offboarding.objects.filter(id__in=ids).delete()
    messages.success(request, "Offboarding deleted")
    return redirect(pipeline)


@login_required
@offboarding_manager_can_enter("offboarding.add_offboardingstage")
def create_stage(request):
    """
    This method is used to create stages for offboardings
    """
    offboarding_id = request.GET["offboarding_id"]
    instance_id = eval(str(request.GET.get("instance_id")))
    instance = None
    if instance_id and isinstance(instance_id, int):
        instance = OffboardingStage.objects.get(id=instance_id)
    offboarding = Offboarding.objects.get(id=offboarding_id)
    form = OffboardingStageForm(instance=instance)
    form.instance.offboarding_id = offboarding
    if request.method == "POST":
        form = OffboardingStageForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.offboarding_id = offboarding
            instance.save()
            instance.managers.set(form.data.getlist("managers"))
            messages.success(request, "Stage saved")
            return HttpResponse("<script>window.location.reload()</script>")
    return render(request, "offboarding/stage/form.html", {"form": form})


@login_required
@any_manager_can_enter("offboarding.add_offboardingemployee")
def add_employee(request):
    """
    This method is used to add employee to the stage
    """
    stage_id = request.GET["stage_id"]
    instance_id = eval(str(request.GET.get("instance_id")))
    instance = None
    if instance_id and isinstance(instance_id, int):
        instance = OffboardingEmployee.objects.get(id=instance_id)
    stage = OffboardingStage.objects.get(id=stage_id)
    form = OffboardingEmployeeForm(initial={"stage_id": stage}, instance=instance)
    form.instance.stage_id = stage
    if request.method == "POST":
        form = OffboardingEmployeeForm(
            request.POST,
             instance=instance
        )
        if form.is_valid():
            instance = form.save(commit=False)
            instance.stage_id = stage
            instance.save()
            messages.success(request, "Employee added to the stage")
            return HttpResponse("<script>window.location.reload()</script>")
    return render(request, "offboarding/employee/form.html", {"form": form})


@login_required
@permission_required("offboarding.delete_offboardingemployee")
def delete_employee(request):
    """
    This method is used to delete the offboarding employee
    """
    employee_ids = request.GET.getlist("employee_ids")
    OffboardingEmployee.objects.filter(id__in=employee_ids).delete()
    messages.success(request, "Offboarding employee deleted")
    return redirect(pipeline)


@login_required
@permission_required("offboarding.delete_offboardingstage")
def delete_stage(request):
    """
    This method  is used to delete the offboarding stage
    """
    ids = request.GET.getlist("ids")
    OffboardingStage.objects.filter(id__in=ids).delete()
    messages.success(request, "Stage deleted")
    return redirect(pipeline)


@login_required
@any_manager_can_enter("offboarding.change_offboarding")
def change_stage(request):
    """
    This method is used to update the stages of the employee
    """
    employee_ids = request.GET.getlist("employee_ids")
    stage_id = request.GET["stage_id"]
    employees = OffboardingEmployee.objects.filter(id__in=employee_ids)
    stage = OffboardingStage.objects.get(id=stage_id)
    # This wont trigger the save method inside the offboarding employee
    # employees.update(stage_id=stage)
    for employee in employees:
        employee.stage_id = stage
        employee.save()
    if stage.type == "archived":
        Employee.objects.filter(
            id__in=employees.values_list("employee_id__id", flat=True)
        ).update(is_active=False)
    stage_forms = {}
    stage_forms[str(stage.offboarding_id.id)] = StageSelectForm(
        offboarding=stage.offboarding_id
    )
    return render(
        request,
        "offboarding/stage/offboarding_body.html",
        {"offboarding": stage.offboarding_id, "stage_forms": stage_forms},
    )


@login_required
@any_manager_can_enter("offboarding.view_offboardingnote")
def view_notes(request):
    """
    This method is used to render all the notes of the employee
    """
    if request.FILES:
        files = request.FILES.getlist("files")
        note_id = request.GET["note_id"]
        note = OffboardingNote.objects.get(id=note_id)
        attachments = []
        for file in files:
            attachment = OffboardingStageMultipleFile()
            attachment.attachment = file
            attachment.save()
            attachments.append(attachment)
        note.attachments.add(*attachments)
    offboarding_employee_id = request.GET["employee_id"]
    employee = OffboardingEmployee.objects.get(id=offboarding_employee_id)
    return render(
        request,
        "offboarding/note/view_notes.html",
        {
            "employee": employee,
        },
    )


@login_required
@any_manager_can_enter("offboarding.add_offboardingnote")
def add_note(request):
    """
    This method is used to create note for the offboarding employee
    """
    employee_id = request.GET["employee_id"]
    employee = OffboardingEmployee.objects.get(id=employee_id)
    form = NoteForm()
    if request.method == "POST":
        form = NoteForm(request.POST, request.FILES)
        form.instance.employee_id = employee
        if form.is_valid():
            form.save()
            return HttpResponse(
                f"""
                    <div id="asfdoiioe09092u09un320" hx-get="/offboarding/view-offboarding-note?employee_id={employee.pk}"
                        hx-target="#noteContainer" 
                    >
                    </div>
                    <script>
                        $("#asfdoiioe09092u09un320").click()
                        $(".oh-modal--show").removeClass("oh-modal--show")
                    </script>
                """
            )
    return render(
        request, "offboarding/note/form.html", {"form": form, "employee": employee}
    )


@login_required
@permission_required("offboarding.delete_offboardingnote")
def delete_attachment(request):
    """
    Used to delete attachment
    """
    ids = request.GET.getlist("ids")
    OffboardingStageMultipleFile.objects.filter(id__in=ids).delete()
    offboarding_employee_id = request.GET["employee_id"]
    employee = OffboardingEmployee.objects.get(id=offboarding_employee_id)
    return render(
        request,
        "offboarding/note/view_notes.html",
        {
            "employee": employee,
        },
    )


@login_required
@offboarding_or_stage_manager_can_enter("offboarding.add_offboardingtask")
def add_task(request):
    """
    This method is used to add offboarding tasks
    """
    stage_id = request.GET.get("stage_id")
    instance_id = eval(str(request.GET.get("instance_id")))
    employees = OffboardingEmployee.objects.filter(stage_id=stage_id)
    instance = None
    if instance_id:
        instance = OffboardingTask.objects.filter(id=instance_id).first()
    form = TaskForm(
        initial={
            "stage_id": stage_id,
            "tasks_to": employees,
        },
        instance=instance,
    )
    if request.method == "POST":
        form = TaskForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Task Added")
            return HttpResponse("<script>window.location.reload()</script>")
    return render(request, "offboarding/task/form.html", {"form": form})


@login_required
@any_manager_can_enter("offboarding.change_employeetask")
def update_task_status(request):
    """
    This method is used to update the assigned tasks status
    """
    stage_id = request.GET["stage_id"]
    employee_ids = request.GET.getlist("employee_ids")
    task_id = request.GET["task_id"]
    status = request.GET["task_status"]
    EmployeeTask.objects.filter(
        employee_id__id__in=employee_ids, task_id__id=task_id
    ).update(status=status)

    stage = OffboardingStage.objects.get(id=stage_id)
    stage_forms = {}
    stage_forms[str(stage.offboarding_id.id)] = StageSelectForm(
        offboarding=stage.offboarding_id
    )
    return render(
        request,
        "offboarding/stage/offboarding_body.html",
        {"offboarding": stage.offboarding_id, "stage_forms": stage_forms},
    )


@login_required
@any_manager_can_enter("offboarding.add_employeetask")
def task_assign(request):
    """
    This method is used to assign task to employees
    """
    employee_ids = request.GET.getlist("employee_ids")
    task_id = request.GET["task_id"]
    employees = OffboardingEmployee.objects.filter(id__in=employee_ids)
    task = OffboardingTask.objects.get(id=task_id)
    for employee in employees:
        assinged_task = EmployeeTask()
        assinged_task.employee_id = employee
        assinged_task.task_id = task
        assinged_task.save()
    offboarding = employees.first().stage_id.offboarding_id
    stage_forms = {}
    stage_forms[str(offboarding.id)] = StageSelectForm(offboarding=offboarding)
    return render(
        request,
        "offboarding/stage/offboarding_body.html",
        {"offboarding": offboarding, "stage_forms": stage_forms},
    )


@login_required
@permission_required("offboarding.delete_offboardingtask")
def delete_task(request):
    """
    This method is used to delete the task
    """
    task_ids = request.GET.getlist("task_ids")
    OffboardingTask.objects.filter(id__in=task_ids).delete()
    messages.success(request, "Task deleted")
    return redirect(pipeline)
