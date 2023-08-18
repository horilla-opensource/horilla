"""
surveys.py

This module is used to write views related to the survey features
"""
import json
from django.core import serializers
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from horilla.decorators import login_required, permission_required
from recruitment.models import Recruitment
from recruitment.forms import ApplicationForm, SurveyForm, QuestionForm
from recruitment.models import (
    RecruitmentSurvey,
    Candidate,
    JobPosition,
    Stage,
    RecruitmentSurveyAnswer,
)
from recruitment.filters import SurveyFilter
from recruitment.views.paginator_qry import paginator_qry


def survey_form(request):
    """
    This method is used to render survey wform
    """
    recruitment_id = request.GET["recId"]
    recruitment = Recruitment.objects.get(id=recruitment_id)
    form = SurveyForm(recruitment=recruitment).form
    return render(request, "survey/form.html", {"form": form})


def candidate_survey(request):
    """
    Used to render survey form to the candidate
    """

    candidate_json = request.session["candidate"]
    candidate_dict = json.loads(candidate_json)
    rec_id = candidate_dict[0]["fields"]["recruitment_id"]
    job_id = candidate_dict[0]["fields"]["job_position_id"]
    job = JobPosition.objects.get(id=job_id)
    recruitment = Recruitment.objects.get(id=rec_id)
    stage_id = candidate_dict[0]["fields"]["stage_id"]
    candidate_dict[0]["fields"]["recruitment_id"] = recruitment
    candidate_dict[0]["fields"]["job_position_id"] = job
    candidate_dict[0]["fields"]["stage_id"] = Stage.objects.get(id=stage_id)
    candidate = Candidate(**candidate_dict[0]["fields"])
    form = SurveyForm(recruitment=recruitment).form
    if request.method == "POST":
        if not Candidate.objects.filter(
            email=candidate.email, recruitment_id=candidate.recruitment_id
        ).exists():
            candidate.save()
            answer = RecruitmentSurveyAnswer()
            answer.candidate_id = candidate
            answer.answer_json = json.dumps(request.POST)
            answer.save()
            messages.success(request, "Your answers are submitted.")
        return render(request, "candidate/success.html")
    return render(
        request,
        "survey/candidate-survey-form.html",
        {"form": form, "candidate": candidate},
    )


@login_required
@permission_required("recruitment.view_recruitmentsurvey")
def view_question_template(request):
    """
    This method is used to view the question template
    """
    questions = RecruitmentSurvey.objects.all()
    filter_obj = SurveyFilter()
    return render(
        request,
        "survey/view-question-templates.html",
        {
            "questions": paginator_qry(questions, request.GET.get("page")),
            "f": filter_obj,
        },
    )


@login_required
@permission_required("recruitment.change_recruitmentsurvey")
def update_question_template(request, survey_id):
    """
    This view method is used to update question template
    """
    instance = RecruitmentSurvey.objects.get(id=survey_id)
    form = QuestionForm(
        instance=instance,
        initial={
            "recruitment": instance.recruitment_ids.all(),
            "job_positions": instance.job_position_ids.all(),
        },
    )
    if request.method == "POST":
        form = QuestionForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            instance.recruitment_ids.set(form.recruitment)
            instance.job_position_ids.set(form.job_positions)
            messages.success(request, "New survey question updated.")
            return HttpResponse(
                render(
                    request, "survey/template-update-form.html", {"form": form}
                ).content.decode("utf-8")
                + "<script>location.reload();</script>"
            )
    return render(request, "survey/template-update-form.html", {"form": form})


@login_required
@permission_required("recruitment.add_recruitmentsurvey")
def create_question_template(request):
    """
    This view method is used to create question template
    """
    form = QuestionForm()
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            instance.recruitment_ids.set(form.recruitment)
            instance.job_position_ids.set(form.job_positions)
            messages.success(request, "New survey question created.")
            return HttpResponse(
                render(
                    request, "survey/template-form.html", {"form": form}
                ).content.decode("utf-8")
                + "<script>location.reload();</script>"
            )
    return render(request, "survey/template-form.html", {"form": form})


@login_required
@permission_required("recriutment.delete_recruitmentsurvey")
def delete_survey_question(request, survey_id):
    """
    This method is used to delete the survey instance
    """
    RecruitmentSurvey.objects.get(id=survey_id).delete()
    messages.success(request, "Question was deleted successfully")
    return redirect(view_question_template)


def application_form(request):
    """
    This method renders candidate form to create candidate
    """
    form = ApplicationForm()
    recruitment = None
    recruitment_id = request.GET.get("recruitmentId")
    if recruitment_id is not None:
        recruitment = Recruitment.objects.filter(id=recruitment_id)
        if recruitment.exists():
            recruitment = recruitment.first()
    if request.POST:
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            candidate_obj = form.save(commit=False)
            recruitment_obj = candidate_obj.recruitment_id
            stages = recruitment_obj.stage_set.all()
            if stages.filter(stage_type="initial").exists():
                candidate_obj.stage_id = stages.filter(stage_type="initial").first()
            else:
                candidate_obj.stage_id = stages.order_by("sequence").first()
            # candidate_obj.save()
            messages.success(request, _("Application saved."))
            request.session["candidate"] = serializers.serialize(
                "json", [candidate_obj]
            )
            return redirect(candidate_survey)
        form.fields[
            "job_position_id"
        ].queryset = form.instance.recruitment_id.open_positions.all()
    return render(
        request,
        "candidate/application_form.html",
        {"form": form, "recruitment": recruitment},
    )
