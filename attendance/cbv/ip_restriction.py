from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import get_session_company
from base.models import AttendanceAllowedIP
from horilla_views.cbv_methods import (
    login_required,
    permission_required,
    render_template,
)
from horilla_views.generic.cbv.views import HorillaListView, HorillaNavView


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("base.view_attendanceallowedip"),
    name="dispatch",
)
class IpRestrictionList(HorillaListView):
    """
    List view of the page
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.view_id = "all-container"

    model = AttendanceAllowedIP
    bulk_select_option = False
    show_toggle_form = False

    columns = [
        (_("IPs"), "ip"),
    ]

    action_method = "action_col"

    def get_queryset(self, *args, **kwargs):
        self._saved_filters = self.request.GET.copy()
        company = get_session_company(self.request)
        qs = self.model.objects.filter(company_id=company).first()

        class IP:
            def __init__(self, ip, idx):
                self.ip = ip
                self.pk = idx

            def action_col(self):
                """
                detail view actions
                """
                return render_template(
                    path="attendance/ip_restriction/action_col.html",
                    context={"instance": self},
                )

        ip_list = (qs.additional_data or {}).get("allowed_ips", []) if qs else []
        self.queryset = [IP(ip, idx) for idx, ip in enumerate(ip_list)]
        return self.queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("base.view_attendanceallowedip"),
    name="dispatch",
)
class IpRestrictionnav(HorillaNavView):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # self.search_url = reverse("grace-time-list")
        self.create_attrs = f"""
            onclick = "event.stopPropagation();"
            data-toggle="oh-modal-toggle"
            data-target="#objectDetailsModalW25"
            hx-target="#objectDetailsModalW25Target"
            hx-get="{reverse('create-allowed-ip')}"
        """
