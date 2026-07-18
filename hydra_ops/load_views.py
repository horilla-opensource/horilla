from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from hydra_ops.load_test import ROLE_WEIGHTS, group_name, object_prefix, validate_run_id


def _guard(request, role):
    run_id = getattr(settings, "HYDRA_LOAD_TEST_RUN_ID", "")
    enabled = getattr(settings, "HYDRA_LOAD_TEST_ENABLED", False)
    environment = getattr(settings, "HYDRA_ENVIRONMENT", "development")
    user = request.user
    if (
        not enabled
        or environment not in {"staging", "test"}
        or not run_id
        or role not in ROLE_WEIGHTS
        or not user.is_authenticated
        or not user.is_active
        or not user.username.startswith(f"hydra-load-{run_id}-{role}-")
    ):
        raise Http404
    try:
        run_id = validate_run_id(run_id)
    except ValueError as exc:
        raise Http404 from exc
    if not user.groups.filter(name=group_name(run_id, role)).exists():
        raise Http404
    return user, object_prefix(run_id)


def _sample(queryset, field="uuid", limit=20):
    return {
        "count": queryset.count(),
        "sample": [str(value) for value in queryset.values_list(field, flat=True)[:limit]],
    }


def _read_profile(*, user, role, query):
    if role == "recruiter":
        from hydra_people.recruitment_selectors import linked_candidates_for_user

        return _sample(linked_candidates_for_user(user=user, query=query), field="pk")
    if role == "hr_admin":
        from hydra_reports.selectors import operational_people_for_user

        return _sample(operational_people_for_user(user=user, filters={"q": query}))
    if role == "coordination":
        from hydra_arrivals.selectors import arrival_plans_for_user
        from hydra_coordination.selectors import teams_for_user

        teams = _sample(teams_for_user(user=user), field="pk")
        teams["arrivals"] = arrival_plans_for_user(user=user).count()
        return teams
    if role == "employee":
        from hydra_notifications.selectors import unread_notification_count
        from hydra_tasks.selectors import tasks_for_user

        tasks = _sample(tasks_for_user(user=user, query=query))
        tasks["unread_notifications"] = unread_notification_count(user=user)
        return tasks
    if role == "legal_housing":
        from hydra_housing.selectors import housing_facilities_for_user
        from hydra_legalization.selectors import legalization_cases_for_user

        facilities = _sample(housing_facilities_for_user(user=user))
        facilities["legalization_cases"] = legalization_cases_for_user(
            user=user, query=query
        ).count()
        return facilities
    if role == "onboarding":
        from hydra_notifications.selectors import unread_notification_count
        from hydra_onboarding.selectors import assignments_for_user, courses_for_user

        courses = _sample(courses_for_user(user=user))
        courses["assignments"] = assignments_for_user(user=user).count()
        courses["unread_notifications"] = unread_notification_count(user=user)
        return courses

    from hydra_coordination.selectors import teams_for_user
    from hydra_people.selectors import people_for_user
    from hydra_tasks.selectors import tasks_for_user

    return {
        "people": people_for_user(user=user).count(),
        "teams": teams_for_user(user=user).count(),
        "tasks": tasks_for_user(user=user).count(),
    }


def _recruiter_write(*, user, prefix):
    from hydra_people.recruitment_selectors import linked_candidates_for_user
    from hydra_people.recruitment_workflow import transition_candidate
    from recruitment.models import Stage

    candidate = linked_candidates_for_user(user=user, query=prefix).filter(
        created_by=user
    ).first()
    if candidate is None:
        raise Http404
    stages = list(
        Stage._base_manager.filter(
            recruitment_id=candidate.recruitment_id,
            stage_type__in=("initial", "applied"),
            is_active=True,
        ).order_by("sequence", "pk")
    )
    target = next((stage for stage in stages if stage.pk != candidate.stage_id_id), None)
    if target is None:
        raise Http404
    reason = "Load-test controlled backward transition" if target.sequence <= candidate.stage_id.sequence else ""
    candidate, event = transition_candidate(
        candidate=candidate,
        target_stage=target,
        actor=user,
        reason=reason,
    )
    return {"action": "candidate_stage", "version": event.pk, "state": candidate.stage_id.stage_type}


@transaction.atomic
def _hr_write(*, user, prefix):
    from hydra_people.models import Person

    person = (
        Person._base_manager.select_for_update()
        .filter(created_by=user, passport_name__startswith=prefix)
        .first()
    )
    if person is None:
        raise Http404
    suffix = f"{user.pk % 100000000:08d}"
    person.phone = f"+481{suffix}" if not person.phone.startswith("+481") else f"+482{suffix}"
    person.modified_by = user
    person.full_clean()
    person.save(update_fields=("phone", "modified_by"))
    return {"action": "person_contact", "state": person.phone[:4]}


def _coordination_write(*, user, prefix):
    from django.utils import timezone

    from hydra_coordination.models import PersonAssignment
    from hydra_coordination.services import assign_person

    assignment = (
        PersonAssignment._base_manager.select_related("person", "team", "department")
        .filter(created_by=user, person__passport_name__startswith=prefix)
        .first()
    )
    if assignment is None:
        raise Http404
    assignment.valid_until = (
        None if assignment.valid_until else timezone.localdate() + timedelta(days=30)
    )
    assignment.modified_by = user
    assignment = assign_person(assignment=assignment, actor=user)
    return {
        "action": "team_assignment",
        "state": assignment.valid_until.isoformat() if assignment.valid_until else "open",
    }


def _employee_write(*, user, prefix):
    from hydra_tasks.models import HydraTask
    from hydra_tasks.services import transition_task

    task = (
        HydraTask._base_manager.filter(
            assignee=user,
            title__startswith=prefix,
            status__in=(HydraTask.Status.OPEN, HydraTask.Status.IN_PROGRESS),
        )
        .order_by("pk")
        .first()
    )
    if task is None:
        raise Http404
    target = (
        HydraTask.Status.IN_PROGRESS
        if task.status == HydraTask.Status.OPEN
        else HydraTask.Status.OPEN
    )
    task = transition_task(
        actor=user,
        task_uuid=task.uuid,
        expected_version=task.version,
        to_status=target,
    )
    return {"action": "task_status", "state": task.status, "version": task.version}


def _housing_write(*, user, prefix):
    from hydra_housing.models import HousingFacility
    from hydra_housing.services import save_housing_facility

    facility = HousingFacility._base_manager.filter(
        created_by=user, name__startswith=prefix
    ).first()
    if facility is None:
        raise Http404
    facility.notes = "Load-test review B" if facility.notes.endswith("A") else "Load-test review A"
    facility = save_housing_facility(facility=facility, actor=user)
    return {"action": "housing_review", "state": facility.notes[-1]}


def _onboarding_write(*, user, prefix):
    from hydra_onboarding.models import Course
    from hydra_onboarding.services import save_course

    course = Course._base_manager.filter(created_by=user, name__startswith=prefix).first()
    if course is None:
        raise Http404
    course.description = (
        "Load-test onboarding revision B"
        if course.description.endswith("A")
        else "Load-test onboarding revision A"
    )
    course = save_course(course=course, actor=user)
    return {"action": "onboarding_content", "state": course.description[-1]}


@require_GET
def load_test_read(request, role):
    user, _prefix = _guard(request, role)
    query = request.GET.get("q", "")[:80]
    return JsonResponse({"role": role, **_read_profile(user=user, role=role, query=query)})


@require_POST
def load_test_write(request, role):
    user, prefix = _guard(request, role)
    writers = {
        "recruiter": _recruiter_write,
        "hr_admin": _hr_write,
        "coordination": _coordination_write,
        "employee": _employee_write,
        "legal_housing": _housing_write,
        "onboarding": _onboarding_write,
    }
    writer = writers.get(role)
    if writer is None:
        raise Http404
    return JsonResponse({"role": role, **writer(user=user, prefix=prefix)})
