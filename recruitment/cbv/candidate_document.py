"""
this page is handling the cbv methods of the candidate documents tab
"""

from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView
from recruitment.cbv_decorators import all_manager_can_enter
from recruitment.filters import CandidateDocumentFilter
from recruitment.models import Candidate, CandidateDocument


@method_decorator(login_required, name="dispatch")
@method_decorator(
    all_manager_can_enter(perm="recruitment.view_candidate"), name="dispatch"
)
class CandidateDocumentListView(HorillaListView):
    """
    Documents list view for the candidate profile tab
    """

    model = CandidateDocument
    filter_class = CandidateDocumentFilter
    show_filter_tags = False
    filter_selected = False
    bulk_select_option = False
    template_name = "cbv/candidate_documents/list_tab.html"
    show_toggle_form = False
    action_method = "document_actions"

    columns = [
        (_("Document"), "title"),
        (_("Status"), "status_col"),
    ]

    sortby_mapping = [
        (_("Document"), "title"),
        (_("Status"), "status"),
    ]

    row_attrs = """
                hx-get='{view_file_url}'
                hx-target="#viewFile"
                data-toggle="oh-modal-toggle"
                data-target="#viewFileModal"
                style="cursor:pointer"
                """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fixed (not auto-random) so pagination/sort/search requests -
        # which all hx-target="#{{view_id}}" from generic/horilla_list_table.html -
        # can be recognized below and answered with just that fragment. Without
        # this, every such request re-renders the full tab (header + Create
        # button included) and htmx's outerHTML swap dumps that whole response
        # in place of the table, duplicating the header on each page/sort/search.
        self.view_id = "candidateDocumentsList"

    def get_template_names(self):
        if self.request.headers.get("HX-Target") == self.view_id:
            return ["generic/horilla_list_table.html"]
        return [self.template_name]

    def get_queryset(self):
        queryset = super().get_queryset()
        cand_id = self.kwargs.get("pk")
        return queryset.filter(candidate_id=cand_id).order_by("-id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["candidate"] = Candidate.objects.get(id=self.kwargs.get("pk"))
        return context
