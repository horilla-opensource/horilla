"""
Module for managing announcements, including creation, updates, comments, and views.
"""

import json

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.forms import AnnouncementCommentForm, AnnouncementForm
from base.methods import closest_numbers, filter_own_records
from base.models import Announcement, AnnouncementComment, AnnouncementView
from employee.models import Employee
from horilla.decorators import login_required, permission_required
from notifications.signals import notify


@login_required
def announcement_view(request):
    """
    This method is used to render all announcemnts.
    """

    announcement_list = Announcement.objects.all().order_by("-created_at")

    # Set the number of items per page
    items_per_page = 10

    paginator = Paginator(announcement_list, items_per_page)

    page = request.GET.get("page")
    try:
        announcements = paginator.page(page)
    except PageNotAnInteger:
        # If the page is not an integer, deliver the first page.
        announcements = paginator.page(1)
    except EmptyPage:
        # If the page is out of range (e.g., 9999), deliver the last page of results.
        announcements = paginator.page(paginator.num_pages)

    return render(
        request, "announcement/announcement.html", {"announcements": announcements}
    )


@login_required
def create_announcement(request):
    """
    This method renders form and template to update Announcement
    """

    form = AnnouncementForm()
    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            anou, attachment_ids = form.save(commit=False)
            anou.save()
            anou.attachments.set(attachment_ids)
            employees = form.cleaned_data["employees"]
            departments = form.cleaned_data["department"]
            job_positions = form.cleaned_data["job_position"]
            anou.department.set(departments)
            anou.job_position.set(job_positions)
            messages.success(request, _("Announcement created successfully."))

            emp_dep = User.objects.filter(
                employee_get__employee_work_info__department_id__in=departments
            )
            emp_jobs = User.objects.filter(
                employee_get__employee_work_info__job_position_id__in=job_positions
            )
            employees = employees | Employee.objects.filter(
                employee_work_info__department_id__in=departments
            )
            employees = employees | Employee.objects.filter(
                employee_work_info__job_position_id__in=job_positions
            )
            anou.employees.add(*employees)

            notify.send(
                request.user.employee_get,
                recipient=emp_dep,
                verb="Your department was mentioned in a post.",
                verb_ar="تم ذكر قسمك في منشور.",
                verb_de="Ihr Abteilung wurde in einem Beitrag erwähnt.",
                verb_es="Tu departamento fue mencionado en una publicación.",
                verb_fr="Votre département a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            notify.send(
                request.user.employee_get,
                recipient=emp_jobs,
                verb="Your job position was mentioned in a post.",
                verb_ar="تم ذكر وظيفتك في منشور.",
                verb_de="Ihre Arbeitsposition wurde in einem Beitrag erwähnt.",
                verb_es="Tu puesto de trabajo fue mencionado en una publicación.",
                verb_fr="Votre poste de travail a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )
            form = AnnouncementForm()
    return render(request, "announcement/announcement_form.html", {"form": form})


@login_required
def delete_announcement(request, anoun_id):
    """
    This method is used to delete announcements.
    """
    announcement = Announcement.find(anoun_id)
    if announcement:
        announcement.delete()
        messages.success(request, _("Announcement deleted successfully."))

    instance_ids = request.GET.get("instance_ids")
    instance_ids_list = json.loads(instance_ids)
    __, next_instance_id = (
        closest_numbers(instance_ids_list, anoun_id)
        if instance_ids_list
        else (None, None)
    )

    if anoun_id in instance_ids_list:
        instance_ids_list.remove(anoun_id)

    if next_instance_id and next_instance_id != anoun_id:
        url = reverse("announcement-single-view", kwargs={"anoun_id": next_instance_id})
        return redirect(f"{url}?instance_ids={json.dumps(instance_ids_list)}")
    return redirect(announcement_single_view)


@login_required
def update_announcement(request, anoun_id):
    """
    This method renders form and template to update Announcement
    """

    announcement = Announcement.objects.get(id=anoun_id)
    form = AnnouncementForm(instance=announcement)
    instance_ids = request.GET.get("instance_ids")
    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            anou, attachment_ids = form.save(commit=False)
            announcement = anou.save()
            anou.attachments.set(attachment_ids)
            employees = form.cleaned_data["employees"]
            departments = form.cleaned_data["department"]
            job_positions = form.cleaned_data["job_position"]
            anou.department.set(departments)
            anou.job_position.set(job_positions)
            messages.success(request, _("Announcement updated successfully."))

            emp_dep = User.objects.filter(
                employee_get__employee_work_info__department_id__in=departments
            )
            emp_jobs = User.objects.filter(
                employee_get__employee_work_info__job_position_id__in=job_positions
            )
            employees = employees | Employee.objects.filter(
                employee_work_info__department_id__in=departments
            )
            employees = employees | Employee.objects.filter(
                employee_work_info__job_position_id__in=job_positions
            )
            anou.employees.add(*employees)

            notify.send(
                request.user.employee_get,
                recipient=emp_dep,
                verb="Your department was mentioned in a post.",
                verb_ar="تم ذكر قسمك في منشور.",
                verb_de="Ihr Abteilung wurde in einem Beitrag erwähnt.",
                verb_es="Tu departamento fue mencionado en una publicación.",
                verb_fr="Votre département a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            notify.send(
                request.user.employee_get,
                recipient=emp_jobs,
                verb="Your job position was mentioned in a post.",
                verb_ar="تم ذكر وظيفتك في منشور.",
                verb_de="Ihre Arbeitsposition wurde in einem Beitrag erwähnt.",
                verb_es="Tu puesto de trabajo fue mencionado en una publicación.",
                verb_fr="Votre poste de travail a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )
    return render(
        request,
        "announcement/announcement_update_form.html",
        {"form": form, "instance_ids": instance_ids},
    )


@login_required
def create_announcement_comment(request, anoun_id):
    """
    This method renders form and template to create Announcement comments
    """
    anoun = Announcement.objects.filter(id=anoun_id).first()
    emp = request.user.employee_get
    form = AnnouncementCommentForm(
        initial={"employee_id": emp.id, "request_id": anoun_id}
    )
    comments = AnnouncementComment.objects.filter(announcement_id=anoun_id)
    commentators = []
    if comments:
        for i in comments:
            commentators.append(i.employee_id.employee_user_id)
    unique_users = list(set(commentators))

    if request.method == "POST":
        form = AnnouncementCommentForm(request.POST)
        if form.is_valid():
            form.instance.employee_id = emp
            form.instance.announcement_id = anoun
            form.save()
            form = AnnouncementCommentForm(
                initial={"employee_id": emp.id, "request_id": anoun_id}
            )
            messages.success(request, _("You commented a post."))
            notify.send(
                request.user.employee_get,
                recipient=unique_users,
                verb=f"Comment under the announcement {anoun.title}.",
                verb_ar=f"تعليق تحت الإعلان {anoun.title}.",
                verb_de=f"Kommentar unter der Ankündigung {anoun.title}.",
                verb_es=f"Comentario bajo el anuncio {anoun.title}.",
                verb_fr=f"Commentaire sous l'annonce {anoun.title}.",
                redirect="/",
                icon="chatbox-ellipses",
            )
        return redirect("announcement-view-comment", anoun_id=anoun_id)

    return render(
        request,
        "announcement/comment_view.html",
        {"form": form, "request_id": anoun_id},
    )


@login_required
def comment_view(request, anoun_id):
    """
    This method is used to view all comments in the announcements
    """
    comments = AnnouncementComment.objects.filter(announcement_id=anoun_id).order_by(
        "-created_at"
    )
    announcement = Announcement.objects.get(id=anoun_id)
    comments = filter_own_records(request, comments, "base.view_announcementcomment")
    no_comments = False
    if not comments.exists():
        no_comments = True

    return render(
        request,
        "announcement/comment_view.html",
        {
            "comments": comments,
            "no_comments": no_comments,
            "request_id": anoun_id,
            "announcement": announcement,
        },
    )


@login_required
def delete_announcement_comment(request, comment_id):
    """
    This method is used to delete announcement comments
    """
    comment = AnnouncementComment.objects.get(id=comment_id)
    comment.delete()
    messages.success(request, _("Comment deleted successfully!"))
    return HttpResponse()


@login_required
def announcement_single_view(request, anoun_id=None):
    """
    This method is used to render single announcements.
    """
    announcement_instance = Announcement.find(anoun_id)
    instance_ids = request.GET.get("instance_ids")
    instance_ids_list = json.loads(instance_ids) if instance_ids else []
    previous_instance_id, next_instance_id = (
        closest_numbers(instance_ids_list, anoun_id)
        if instance_ids_list
        else (None, None)
    )
    if announcement_instance:
        announcement_view_obj, _ = AnnouncementView.objects.get_or_create(
            user=request.user, announcement=announcement_instance
        )
        announcement_view_obj.viewed = True
        announcement_view_obj.save()

    context = {
        "announcement": announcement_instance,
        "instance_ids": instance_ids,
        "previous_instance_id": previous_instance_id,
        "next_instance_id": next_instance_id,
    }

    return render(request, "announcement/announcement_one.html", context)


@login_required
@permission_required("base.view_announcement")
def viewed_by(request):
    """
    This method is used to view the employees
    """
    announcement_id = request.GET.get("announcement_id")
    viewed_users = AnnouncementView.objects.filter(
        announcement_id__id=announcement_id, viewed=True
    )
    return render(request, "announcement/viewed_by.html", {"viewed_by": viewed_users})
