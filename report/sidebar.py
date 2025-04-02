

from django.utils.translation import gettext_lazy as trans
from django.urls import reverse_lazy


MENU = trans("Reports")
IMG_SRC = "images/ui/report.svg"
ACCESSIBILITY = "report.sidebar.menu_accessibility"


SUBMENUS = [
    {
        "menu":"Employee",
        "redirect":reverse_lazy("employee-report"),
    },
    {
        "menu":"Attendance",
        "redirect":reverse_lazy("attendance-report"),
    },
    {
        "menu":"Leave",
        "redirect":reverse_lazy("leave-report"),
    },
    {
        "menu":"Payroll",
        "redirect":reverse_lazy("payroll-report"),
    }
]

def menu_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser
