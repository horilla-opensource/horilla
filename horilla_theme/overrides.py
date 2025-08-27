from django.apps import apps
from django.utils.translation import gettext_lazy as _


def get_horilla_model_class(app_label, model):
    try:
        return apps.get_model(app_label, model)
    except LookupError:
        return None

Recruitment = get_horilla_model_class(app_label="recruitment", model="recruitment")


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


Recruitment.managers_detail = managers_detail
Recruitment.open_job_detail = open_job_detail
Recruitment.tot_hires = tot_hires