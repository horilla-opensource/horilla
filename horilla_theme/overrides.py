from django.apps import apps
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


def get_horilla_model_class(app_label, model):
    try:
        return apps.get_model(app_label, model)
    except LookupError:
        return None


Recruitment = get_horilla_model_class(app_label="recruitment", model="recruitment")
AttendanceLateComeEarlyOut = get_horilla_model_class(
    app_label="attendance", model="attendancelatecomeearlyOut"
)


def tot_hires(self):
    """
    This method for get custom column for Total hires.
    """

    col = f"""
        {self.total_hires()} Hired of {self.candidate.all().count()} Candidates
    """

    return col


def managers_detail(self):
    """
    manager in detail view
    """
    employees = self.recruitment_managers.all()
    employee_names_string = ""
    if employees:
        employee_names_string = ",<br />".join(
            [str(employee) for employee in employees]
        )

    return employee_names_string


def open_job_detail(self):
    """
    open jobs in detail view
    """
    jobs = self.open_positions.all()
    jobs_names_string = ""

    if jobs:
        jobs_names_string = ",<br />".join([str(job) for job in jobs])

    return jobs_names_string


def penalities_column(self):
    """
    Returns an HTML snippet showing penalty status with Tailwind styling.
    """

    penalties_count = self.get_penalties_count()

    if penalties_count:
        url = reverse("view-penalties") + f"?late_early_id={self.id}"
        return format_html(
            '<div class="bg-red-100/10 border-2 border-red-300 rounded-xl px-4 py-2 w-32 text-xs text-center text-red-700 font-semibold" '
            'data-target="#penaltyViewModal" data-toggle="oh-modal-toggle" '
            'onclick="event.stopPropagation();"'
            'hx-get="{}" hx-target="#penaltyViewModalBody" align="center">'
            "Penalties :{}</div>",
            url,
            penalties_count,
        )
    else:
        return format_html(
            '<div class="bg-green-100/10 border-2 border-green-300 rounded-xl px-4 py-2 w-32 text-xs text-center text-green-700 font-semibold">'
            "No Penalties</div>"
        )


Recruitment.managers_detail = managers_detail
Recruitment.open_job_detail = open_job_detail
Recruitment.tot_hires = tot_hires

AttendanceLateComeEarlyOut.penalities_column = penalities_column
