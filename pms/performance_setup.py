"""
pms/performance_setup.py

Performance Setup landing page with tabbed objective template, question template,
and period sections.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def performance_setup_view(request):
    """
    Performance Setup landing page with tabbed configuration sections.
    """
    return render(request, "performance/performance_setup.html")
