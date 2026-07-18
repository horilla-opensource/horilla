from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from employee.models import Employee, EmployeeWorkInformation
from hydra_people.identity import ensure_canonical_person
from hydra_people.models import EmployeeConversion, Person, PersonApplication
from recruitment.models import Candidate, Recruitment, Stage


CONVERSION_PERMISSIONS = (
    "hydra_people.view_person",
    "hydra_people.change_person",
    "hydra_people.convert_person_to_employee",
    "recruitment.view_candidate",
    "recruitment.change_candidate",
    "employee.view_employee",
    "employee.add_employee",
    "employee.add_employeeworkinformation",
)


def _require_permissions(actor, *permissions: str) -> None:
    if not actor.is_authenticated or not actor.has_perms(permissions):
        raise PermissionDenied


def _persist_candidate_link(*, person, candidate, actor, source):
    ensure_canonical_person(person)
    existing = (
        PersonApplication.objects.select_for_update()
        .filter(candidate=candidate)
        .first()
    )
    if existing:
        if existing.person_id == person.pk:
            return existing
        raise ValidationError(
            {"candidate": "This recruitment application is linked to another person."}
        )

    if candidate.recruitment_id_id and PersonApplication.objects.filter(
        person=person,
        candidate__recruitment_id_id=candidate.recruitment_id_id,
    ).exists():
        raise ValidationError(
            {"candidate": "This person already has an application in this recruitment."}
        )

    if (
        person.employee_id
        and candidate.converted_employee_id
        and person.employee_id != candidate.converted_employee_id
    ):
        raise ValidationError(
            {"candidate": "The candidate and person reference different employees."}
        )

    link = PersonApplication(
        person=person,
        candidate=candidate,
        link_source=source,
        created_by=actor,
        modified_by=actor,
    )
    link.full_clean()
    link.save()

    if person.lifecycle_state == Person.LifecycleState.PROSPECT:
        person.lifecycle_state = Person.LifecycleState.CANDIDATE
        person.modified_by = actor
        person.save(update_fields=("lifecycle_state", "modified_by"))

    return link


@transaction.atomic
def save_person(*, person: Person, actor) -> Person:
    permission = "hydra_people.add_person" if person._state.adding else "hydra_people.change_person"
    _require_permissions(actor, permission)
    if not person._state.adding:
        ensure_canonical_person(person)

    if not person._state.adding and not actor.is_superuser:
        from hydra_people.selectors import people_for_user

        if not people_for_user(user=actor, permission="change_person").filter(
            pk=person.pk
        ).exists():
            raise PermissionDenied

    if person._state.adding:
        person.created_by = actor
    person.modified_by = actor
    person.full_clean()
    person.save()
    from hydra_people.duplicate_services import (
        refresh_duplicate_suggestions_for_person,
    )

    refresh_duplicate_suggestions_for_person(person_id=person.pk, actor=actor)
    return person


@transaction.atomic
def link_candidate(
    *,
    person: Person,
    candidate: Candidate,
    actor,
    source=PersonApplication.LinkSource.MANUAL,
) -> PersonApplication:
    _require_permissions(
        actor,
        "hydra_people.view_person",
        "hydra_people.change_person",
        "hydra_people.link_candidate",
        "recruitment.view_candidate",
    )

    if not actor.is_superuser:
        from hydra_people.selectors import people_for_user
        from hydra_people.recruitment_selectors import (
            linked_candidates_for_user,
            unlinked_candidates_for_user,
        )

        if not people_for_user(user=actor, permission="change_person").filter(
            pk=person.pk
        ).exists():
            raise PermissionDenied
        candidate_is_visible = unlinked_candidates_for_user(user=actor).filter(
            pk=candidate.pk
        ).exists() or linked_candidates_for_user(user=actor).filter(
            pk=candidate.pk
        ).exists()
        if not candidate_is_visible:
            raise PermissionDenied

    locked_person = Person.objects.select_for_update().get(pk=person.pk)
    ensure_canonical_person(locked_person)
    locked_candidate = Candidate._base_manager.select_for_update().get(pk=candidate.pk)
    return _persist_candidate_link(
        person=locked_person,
        candidate=locked_candidate,
        actor=actor,
        source=source,
    )


@transaction.atomic
def create_candidate_application(*, person: Person, candidate: Candidate, actor):
    """Create a Hydra application and its canonical Hydra Person link."""

    _require_permissions(
        actor,
        "hydra_people.view_person",
        "hydra_people.change_person",
        "hydra_people.link_candidate",
        "recruitment.add_candidate",
        "recruitment.view_candidate",
        "recruitment.view_recruitment",
    )
    if candidate.pk:
        raise ValidationError("A new candidate application was expected.")

    from hydra_people.selectors import people_for_user
    from hydra_people.recruitment_selectors import recruitments_for_user

    locked_person = Person.objects.select_for_update().get(pk=person.pk)
    ensure_canonical_person(locked_person)
    if not actor.is_superuser and not people_for_user(
        user=actor, permission="change_person"
    ).filter(pk=locked_person.pk).exists():
        raise PermissionDenied

    recruitment = (
        Recruitment._base_manager.select_for_update()
        .filter(pk=candidate.recruitment_id_id)
        .first()
    )
    if recruitment is None or not recruitments_for_user(
        user=actor, permission="view_recruitment"
    ).filter(pk=recruitment.pk).exists():
        raise PermissionDenied
    if recruitment.closed or not recruitment.is_active:
        raise ValidationError({"recruitment_id": "Choose an open recruitment."})

    if candidate.job_position_id_id is None or not recruitment.open_positions.filter(
        pk=candidate.job_position_id_id
    ).exists():
        raise ValidationError({"job_position_id": "Choose a position from this recruitment."})

    if PersonApplication.objects.select_for_update().filter(
        person=locked_person,
        candidate__recruitment_id=recruitment,
    ).exists():
        raise ValidationError(
            {"recruitment_id": "This person already has an application in this recruitment."}
        )
    if Candidate._base_manager.select_for_update().filter(
        recruitment_id=recruitment,
        email__iexact=candidate.email.strip(),
    ).exists():
        raise ValidationError(
            {"email": "This email already has an application in this recruitment."}
        )

    initial_stage = (
        Stage._base_manager.select_for_update()
        .filter(recruitment_id=recruitment, stage_type="initial", is_active=True)
        .order_by("sequence", "pk")
        .first()
    )
    if initial_stage is None:
        raise ValidationError(
            {"recruitment_id": "This recruitment has no active initial stage."}
        )

    candidate.name = locked_person.passport_name[:100]
    candidate.dob = locked_person.date_of_birth
    candidate.gender = (
        locked_person.gender
        if locked_person.gender in {"female", "male", "other"}
        else "other"
    )
    candidate.email = candidate.email.strip().lower()
    candidate.source = candidate.source or "software"
    candidate.recruitment_id = recruitment
    candidate.stage_id = initial_stage
    candidate.start_onboard = False
    candidate.hired = False
    candidate.created_by = actor
    candidate.modified_by = actor
    candidate.full_clean(exclude=("profile", "resume"))
    candidate.save()

    link = _persist_candidate_link(
        person=locked_person,
        candidate=candidate,
        actor=actor,
        source=PersonApplication.LinkSource.HYDRA_INTAKE,
    )
    return candidate, link


def _normalize_conversion_input(*, work_email, phone):
    normalized_email = work_email.strip().lower()
    normalized_phone = " ".join(phone.split())
    if not normalized_email:
        raise ValidationError({"work_email": "A work email is required."})
    if not normalized_phone:
        raise ValidationError({"phone": "A phone number is required."})
    return normalized_email, normalized_phone


def _validate_conversion_candidate(*, person, candidate):
    try:
        linked_person_id = candidate.hydra_person_link.person_id
    except PersonApplication.DoesNotExist as error:
        raise ValidationError(
            {"candidate": "The application must be linked to a Hydra Person."}
        ) from error
    if linked_person_id != person.pk:
        raise ValidationError(
            {"candidate": "The application belongs to another Person."}
        )
    if not candidate.is_active or candidate.canceled:
        raise ValidationError({"candidate": "Choose an active application."})
    if not candidate.hired:
        raise ValidationError(
            {"candidate": "Only a hired application can become an employee."}
        )
    if candidate.recruitment_id_id is None:
        raise ValidationError({"candidate": "The application has no recruitment."})
    if candidate.recruitment_id.company_id_id is None:
        raise ValidationError({"candidate": "The recruitment has no company."})
    if candidate.job_position_id_id is None:
        raise ValidationError({"candidate": "The application has no job position."})
    if candidate.job_position_id.department_id_id is None:
        raise ValidationError({"candidate": "The job position has no department."})


def _conversion_snapshot(
    *, person, candidate, employee, work_info, submitted, pre_conversion
):
    return {
        "pre_conversion": pre_conversion,
        "person": {
            "id": person.pk,
            "uuid": str(person.uuid),
            "hydra_id": person.hydra_id,
            "passport_name": person.passport_name,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "date_of_birth": person.date_of_birth.isoformat(),
            "gender": person.gender,
            "citizenship": person.citizenship,
            "email": person.email,
            "phone": person.phone,
            "lifecycle_state": person.lifecycle_state,
        },
        "candidate": {
            "id": candidate.pk,
            "email": candidate.email,
            "mobile": candidate.mobile,
            "joining_date": (
                candidate.joining_date.isoformat() if candidate.joining_date else None
            ),
            "recruitment_id": candidate.recruitment_id_id,
            "company_id": candidate.recruitment_id.company_id_id,
            "job_position_id": candidate.job_position_id_id,
            "department_id": candidate.job_position_id.department_id_id,
            "hired": candidate.hired,
        },
        "submitted": submitted,
        "employee": {
            "id": employee.pk,
            "user_id": employee.employee_user_id_id,
            "first_name": employee.employee_first_name,
            "last_name": employee.employee_last_name,
            "email": employee.email,
            "phone": employee.phone,
            "date_of_birth": employee.dob.isoformat() if employee.dob else None,
            "gender": employee.gender,
            "company_id": work_info.company_id_id,
            "department_id": work_info.department_id_id,
            "job_position_id": work_info.job_position_id_id,
            "date_joining": (
                work_info.date_joining.isoformat() if work_info.date_joining else None
            ),
        },
    }


def _field_decisions(*, existing_employee):
    if existing_employee:
        return {
            "employee": "retained_existing_candidate_employee",
            "person_link": "linked_without_overwriting_employee_fields",
            "candidate_link": "retained_explicit_candidate_employee_link",
            "lifecycle_state": "set_to_employee",
        }
    return {
        "employee_first_name": "person.first_name",
        "employee_last_name": "person.last_name",
        "employee_dob": "person.date_of_birth",
        "employee_gender": "person.gender",
        "employee_email": "operator.work_email",
        "employee_phone": "operator.phone",
        "company": "candidate.recruitment.company",
        "department": "candidate.job_position.department",
        "job_position": "candidate.job_position",
        "date_joining": "operator.joining_date",
        "user_account": "inactive_with_unusable_password",
        "lifecycle_state": "set_to_employee",
    }


def _validate_existing_employee(*, employee, candidate, work_email, phone, joining_date):
    work_info = EmployeeWorkInformation._base_manager.select_for_update().get(
        employee_id=employee
    )
    candidate_company_id = candidate.recruitment_id.company_id_id
    if work_info.company_id_id and work_info.company_id_id != candidate_company_id:
        raise ValidationError(
            {"candidate": "The existing employee belongs to another company."}
        )
    if employee.email.strip().lower() != work_email:
        raise ValidationError(
            {"work_email": "Use the existing employee email for this link."}
        )
    if " ".join(employee.phone.split()) != phone:
        raise ValidationError(
            {"phone": "Use the existing employee phone for this link."}
        )
    if work_info.date_joining and work_info.date_joining != joining_date:
        raise ValidationError(
            {"joining_date": "Use the existing employee joining date for this link."}
        )
    return work_info


def _create_employee(*, person, candidate, work_email, phone, joining_date):
    if Employee._base_manager.filter(email__iexact=work_email).exists():
        raise ValidationError(
            {"work_email": "An employee already uses this email; link it explicitly first."}
        )
    if User._default_manager.filter(
        Q(username__iexact=work_email) | Q(email__iexact=work_email)
    ).exists():
        raise ValidationError({"work_email": "A user already uses this email."})

    user = User(
        username=work_email,
        email=work_email,
        is_active=False,
        is_new_employee=True,
    )
    user.set_unusable_password()
    user.full_clean()
    user.save()

    gender = person.gender if person.gender in {"female", "male", "other"} else "other"
    employee = Employee(
        employee_user_id=user,
        employee_first_name=person.first_name,
        employee_last_name=person.last_name,
        email=work_email,
        phone=phone,
        dob=person.date_of_birth,
        gender=gender,
        is_directly_converted=True,
    )
    employee.save()

    own_profile_permissions = Permission.objects.filter(
        content_type__app_label="employee",
        codename__in=("change_ownprofile", "view_ownprofile"),
    )
    user.user_permissions.add(*own_profile_permissions)

    work_info = EmployeeWorkInformation._base_manager.select_for_update().get(
        employee_id=employee
    )
    work_info.company_id = candidate.recruitment_id.company_id
    work_info.department_id = candidate.job_position_id.department_id
    work_info.job_position_id = candidate.job_position_id
    work_info.date_joining = joining_date
    work_info.email = work_email
    work_info.save()
    employee.refresh_from_db()
    work_info.refresh_from_db()
    return employee, work_info


def _persist_conversion_links(*, person, candidate, employee, actor):
    other_person = (
        Person.objects.select_for_update()
        .filter(employee=employee)
        .exclude(pk=person.pk)
        .first()
    )
    if other_person:
        raise ValidationError(
            {"candidate": "This employee is already linked to another Person."}
        )
    if candidate.converted_employee_id_id not in (None, employee.pk):
        raise ValidationError(
            {"candidate": "The application references a different employee."}
        )
    if person.employee_id not in (None, employee.pk):
        raise ValidationError("This Person references a different employee.")

    candidate.converted_employee_id = employee
    candidate.converted = True
    candidate.modified_by = actor
    candidate.save(
        update_fields=("converted_employee_id", "converted", "modified_by")
    )
    person.employee = employee
    person.lifecycle_state = Person.LifecycleState.EMPLOYEE
    person.modified_by = actor
    person.save(update_fields=("employee", "lifecycle_state", "modified_by"))


def _create_conversion_record(
    *,
    person,
    candidate,
    employee,
    work_info,
    actor,
    source,
    submitted,
    pre_conversion,
    existing_employee,
):
    existing = EmployeeConversion.objects.select_for_update().filter(
        person=person
    ).first()
    if existing:
        if existing.candidate_id != candidate.pk or existing.employee_id != employee.pk:
            raise ValidationError("This Person already has another conversion record.")
        return existing

    conversion = EmployeeConversion(
        person=person,
        candidate=candidate,
        employee=employee,
        actor=actor,
        source=source,
        source_snapshot=_conversion_snapshot(
            person=person,
            candidate=candidate,
            employee=employee,
            work_info=work_info,
            submitted=submitted,
            pre_conversion=pre_conversion,
        ),
        field_decisions=_field_decisions(existing_employee=existing_employee),
    )
    conversion.full_clean()
    conversion.save(force_insert=True)
    return conversion


@transaction.atomic
def convert_person_to_employee(
    *, person, candidate, work_email, phone, joining_date, actor
):
    """Create/link one Hydra Employee and preserve the conversion decision."""

    _require_permissions(actor, *CONVERSION_PERMISSIONS)
    if joining_date is None:
        raise ValidationError({"joining_date": "A joining date is required."})
    work_email, phone = _normalize_conversion_input(
        work_email=work_email,
        phone=phone,
    )

    from hydra_people.recruitment_selectors import linked_candidates_for_user
    from hydra_people.selectors import people_for_user

    if not people_for_user(user=actor, permission="change_person").filter(
        pk=person.pk
    ).exists():
        raise PermissionDenied
    if not linked_candidates_for_user(user=actor).filter(
        pk=candidate.pk,
        hydra_person_link__person_id=person.pk,
    ).exists():
        raise PermissionDenied

    locked_person = Person.objects.select_for_update().get(pk=person.pk)
    ensure_canonical_person(locked_person)
    locked_candidate = Candidate._base_manager.select_for_update().get(
        pk=candidate.pk
    )
    _validate_conversion_candidate(
        person=locked_person,
        candidate=locked_candidate,
    )
    pre_conversion = {
        "person_lifecycle_state": locked_person.lifecycle_state,
        "person_employee_id": locked_person.employee_id,
        "candidate_converted": locked_candidate.converted,
        "candidate_employee_id": locked_candidate.converted_employee_id_id,
    }

    target_employee = locked_person.employee or locked_candidate.converted_employee_id
    employee_created = target_employee is None
    if target_employee:
        employee = Employee._base_manager.select_for_update().get(pk=target_employee.pk)
        work_info = _validate_existing_employee(
            employee=employee,
            candidate=locked_candidate,
            work_email=work_email,
            phone=phone,
            joining_date=joining_date,
        )
    else:
        employee, work_info = _create_employee(
            person=locked_person,
            candidate=locked_candidate,
            work_email=work_email,
            phone=phone,
            joining_date=joining_date,
        )

    _persist_conversion_links(
        person=locked_person,
        candidate=locked_candidate,
        employee=employee,
        actor=actor,
    )
    submitted = {
        "work_email": work_email,
        "phone": phone,
        "joining_date": joining_date.isoformat(),
    }
    conversion = _create_conversion_record(
        person=locked_person,
        candidate=locked_candidate,
        employee=employee,
        work_info=work_info,
        actor=actor,
        source=EmployeeConversion.Source.HYDRA_OPERATOR,
        submitted=submitted,
        pre_conversion=pre_conversion,
        existing_employee=not employee_created,
    )
    from hydra_arrivals.onboarding import reconcile_person_onboarding_handoff

    reconcile_person_onboarding_handoff(person=locked_person, actor=actor)
    return employee, conversion, employee_created


@transaction.atomic
def synchronize_onboarding_employee(*, candidate, employee, actor):
    """Record a completed Hydra onboarding conversion for a linked Person."""

    locked_candidate = Candidate._base_manager.select_for_update().get(
        pk=candidate.pk
    )
    try:
        person = locked_candidate.hydra_person_link.person
    except PersonApplication.DoesNotExist:
        return None
    locked_person = Person.objects.select_for_update().get(pk=person.pk)
    ensure_canonical_person(locked_person)
    locked_employee = Employee._base_manager.select_for_update().get(pk=employee.pk)
    _validate_conversion_candidate(person=locked_person, candidate=locked_candidate)
    pre_conversion = {
        "person_lifecycle_state": locked_person.lifecycle_state,
        "person_employee_id": locked_person.employee_id,
        "candidate_converted": locked_candidate.converted,
        "candidate_employee_id": locked_candidate.converted_employee_id_id,
    }
    work_info = EmployeeWorkInformation._base_manager.select_for_update().get(
        employee_id=locked_employee
    )
    if (
        work_info.company_id_id
        and work_info.company_id_id != locked_candidate.recruitment_id.company_id_id
    ):
        raise ValidationError("The onboarding employee belongs to another company.")
    _persist_conversion_links(
        person=locked_person,
        candidate=locked_candidate,
        employee=locked_employee,
        actor=actor,
    )
    conversion = _create_conversion_record(
        person=locked_person,
        candidate=locked_candidate,
        employee=locked_employee,
        work_info=work_info,
        actor=actor,
        source=EmployeeConversion.Source.HYDRA_ONBOARDING,
        submitted={"onboarding_employee_id": locked_employee.pk},
        pre_conversion=pre_conversion,
        existing_employee=True,
    )
    from hydra_arrivals.onboarding import reconcile_person_onboarding_handoff

    reconcile_person_onboarding_handoff(person=locked_person, actor=actor)
    return conversion
