"""
employee/work_structure.py

Work Structure landing page with tabbed shift, schedule, work type, and tag sections.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def work_structure_view(request):
    """
    Work Structure landing page with tabbed master-data sections.
    """
    return render(request, "work_structure/work_structure.html")


@login_required
def work_structure_shift_tab(request):
    """HTMX tab body for employee shifts under work structure."""
    return render(request, "work_structure/work_structure_shift_tab.html")


@login_required
def work_structure_shift_schedule_tab(request):
    """HTMX tab body for shift schedules under work structure."""
    return render(request, "work_structure/work_structure_shift_schedule_tab.html")


@login_required
def work_structure_rotating_shift_tab(request):
    """HTMX tab body for rotating shifts under work structure."""
    return render(request, "work_structure/work_structure_rotating_shift_tab.html")


@login_required
def work_structure_work_type_tab(request):
    """HTMX tab body for work types under work structure."""
    return render(request, "work_structure/work_structure_work_type_tab.html")


@login_required
def work_structure_rotating_work_type_tab(request):
    """HTMX tab body for rotating work types under work structure."""
    return render(request, "work_structure/work_structure_rotating_work_type_tab.html")


@login_required
def work_structure_employee_type_tab(request):
    """HTMX tab body for employee types under work structure."""
    return render(request, "work_structure/work_structure_employee_type_tab.html")


@login_required
def work_structure_employee_tags_tab(request):
    """HTMX tab body for employee tags under work structure."""
    return render(request, "work_structure/work_structure_employee_tags_tab.html")
