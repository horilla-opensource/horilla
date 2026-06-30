"""
employee/knowledge.py

Knowledge Base ("База знань") — a Policies-like section with spaces split into
"Available to everyone" (public, readable by all) and "Available to me"
(private, readable only by HR-assigned employees). HR manages spaces and
assigns per-space access; assigned users get either "view & comment" or "full"
(view, comment, add, delete) access.
"""

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from base.access import (
    is_hr,
    kb_accessible_spaces,
    kb_can_manage,
    kb_space_level,
)
from employee.models import (
    Employee,
    KnowledgeComment,
    KnowledgeDocument,
    KnowledgeSpace,
    KnowledgeSpaceAccess,
)
from horilla.decorators import hx_request_required, login_required


class KnowledgeSpaceForm(forms.ModelForm):
    class Meta:
        model = KnowledgeSpace
        fields = ["title", "description", "is_public"]


class KnowledgeDocumentForm(forms.ModelForm):
    class Meta:
        model = KnowledgeDocument
        fields = ["title", "description", "attachment"]


class KnowledgeAccessForm(forms.ModelForm):
    class Meta:
        model = KnowledgeSpaceAccess
        fields = ["employee_id", "level"]


def _hr_only(request):
    if not kb_can_manage(request.user):
        messages.error(request, _("Only HR can manage the knowledge base."))
        return False
    return True


@login_required
def knowledge_base(request):
    """List accessible spaces, split into public and private (assigned)."""
    spaces = kb_accessible_spaces(request.user)
    return render(
        request,
        "knowledge/knowledge_base.html",
        {
            "public_spaces": spaces.filter(is_public=True),
            "private_spaces": spaces.filter(is_public=False),
            "can_manage": kb_can_manage(request.user),
        },
    )


@login_required
def knowledge_space(request, space_id):
    """View a space's documents + comments (if the user can access it)."""
    space = get_object_or_404(KnowledgeSpace, id=space_id)
    level = kb_space_level(request.user, space)
    if level is None:
        return render(request, "404.html", status=404)
    return render(
        request,
        "knowledge/knowledge_space.html",
        {
            "space": space,
            "documents": space.documents.all().prefetch_related("comments"),
            "level": level,
            "can_edit": level == "full",
            "can_manage": kb_can_manage(request.user),
        },
    )


@login_required
def create_space(request):
    """HR: create a knowledge space (optionally editing one via ?id=)."""
    if not _hr_only(request):
        return redirect("knowledge-base")
    instance = KnowledgeSpace.objects.filter(id=request.GET.get("id")).first()
    form = KnowledgeSpaceForm(instance=instance)
    if request.method == "POST":
        form = KnowledgeSpaceForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Knowledge space saved."))
            return redirect("knowledge-base")
    return render(request, "knowledge/space_form.html", {"form": form})


@login_required
def delete_space(request, space_id):
    if not _hr_only(request):
        return redirect("knowledge-base")
    KnowledgeSpace.objects.filter(id=space_id).delete()
    messages.success(request, _("Knowledge space deleted."))
    return redirect("knowledge-base")


@login_required
def assign_access(request, space_id):
    """HR: assign / list employee access for a private space."""
    if not _hr_only(request):
        return redirect("knowledge-base")
    space = get_object_or_404(KnowledgeSpace, id=space_id)
    form = KnowledgeAccessForm()
    if request.method == "POST":
        form = KnowledgeAccessForm(request.POST)
        if form.is_valid():
            access = form.save(commit=False)
            access.space_id = space
            # upsert: update level if the employee is already assigned
            existing = KnowledgeSpaceAccess.objects.filter(
                space_id=space, employee_id=access.employee_id
            ).first()
            if existing:
                existing.level = access.level
                existing.save()
            else:
                access.save()
            messages.success(request, _("Access updated."))
            return redirect("knowledge-space-access", space_id=space.id)
    return render(
        request,
        "knowledge/access.html",
        {"space": space, "form": form, "accesses": space.accesses.all()},
    )


@login_required
def remove_access(request, access_id):
    if not _hr_only(request):
        return redirect("knowledge-base")
    access = get_object_or_404(KnowledgeSpaceAccess, id=access_id)
    space_id = access.space_id_id
    access.delete()
    messages.success(request, _("Access removed."))
    return redirect("knowledge-space-access", space_id=space_id)


@login_required
def create_document(request, space_id):
    """HR or a full-access user: add a document to a space."""
    space = get_object_or_404(KnowledgeSpace, id=space_id)
    if kb_space_level(request.user, space) != "full":
        return render(request, "404.html", status=404)
    form = KnowledgeDocumentForm()
    if request.method == "POST":
        form = KnowledgeDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.space_id = space
            doc.save()
            messages.success(request, _("Document added."))
            return redirect("knowledge-space", space_id=space.id)
    return render(
        request, "knowledge/document_form.html", {"form": form, "space": space}
    )


@login_required
def delete_document(request, doc_id):
    doc = get_object_or_404(KnowledgeDocument, id=doc_id)
    if kb_space_level(request.user, doc.space_id) != "full":
        return render(request, "404.html", status=404)
    space_id = doc.space_id_id
    doc.delete()
    messages.success(request, _("Document deleted."))
    return redirect("knowledge-space", space_id=space_id)


@login_required
def add_comment(request, doc_id):
    """Any user with at least 'view' access may comment."""
    doc = get_object_or_404(KnowledgeDocument, id=doc_id)
    if kb_space_level(request.user, doc.space_id) is None:
        return render(request, "404.html", status=404)
    text = (request.POST.get("comment") or "").strip()
    if text:
        KnowledgeComment.objects.create(document_id=doc, comment=text)
        messages.success(request, _("Comment added."))
    return redirect("knowledge-space", space_id=doc.space_id_id)
