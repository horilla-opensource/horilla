from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.translation import get_language, gettext_lazy as _

from hydra_links.forms import PublicHydraLinkForm
from hydra_links.models import PublicHydraLink
from hydra_links.public_urls import resolve_public_links
from hydra_links.selectors import public_link_for_user, public_links_for_user
from hydra_links.services import save_public_hydra_link


def _add_validation_errors(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            for item in errors:
                form.add_error(field if field in form.fields else None, item)
    else:
        form.add_error(None, error)


@login_required
@permission_required("hydra_links.view_publichydralink", raise_exception=True)
def public_link_list(request):
    include_inactive = request.user.has_perm(
        "hydra_links.change_publichydralink"
    )
    records = public_links_for_user(
        user=request.user,
        include_inactive=include_inactive,
    )
    return render(
        request,
        "hydra_links/public_link_list.html",
        {
            "public_links": resolve_public_links(
                links=records,
                language_code=get_language() or "ru",
            ),
        },
    )

def _public_link_form_view(request, *, link, page_title):
    form = PublicHydraLinkForm(
        request.POST or None,
        instance=link,
        actor=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            link = save_public_hydra_link(
                link=form.save(commit=False),
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Public Hydra link saved."))
            return redirect("hydra-public-link-list")
    return render(
        request,
        "hydra_links/public_link_form.html",
        {"form": form, "public_link": link, "page_title": page_title},
    )


@login_required
@permission_required("hydra_links.add_publichydralink", raise_exception=True)
def public_link_create(request):
    return _public_link_form_view(
        request,
        link=PublicHydraLink(kind=PublicHydraLink.Kind.LOCATION_TRAINING),
        page_title=_("Create public Hydra link"),
    )


@login_required
@permission_required("hydra_links.change_publichydralink", raise_exception=True)
def public_link_update(request, link_uuid):
    link = public_link_for_user(user=request.user, link_uuid=link_uuid)
    return _public_link_form_view(
        request,
        link=link,
        page_title=_("Edit public Hydra link"),
    )
