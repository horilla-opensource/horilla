import os
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from base.models import Company, Department, JobPosition
from employee.models import Employee, EmployeeWorkInformation
from hydra_coordination.models import Location, PersonAssignment, ScopeGrant, Section, Team
from hydra_housing.models import HousingFacility
from hydra_onboarding.models import Course
from hydra_ops.load_test import (
    ROLE_WEIGHTS,
    group_name,
    object_prefix,
    role_counts,
    username_for,
    validate_run_id,
)
from hydra_people.models import Person, RecruitmentStageTransitionRule
from hydra_people.recruitment_workflow import (
    default_transition_rule_values,
    transition_candidate,
)
from hydra_people.services import create_candidate_application
from hydra_tasks.models import HydraTask, HydraTaskEvent, TaskTargetKind
from recruitment.models import Candidate, Recruitment, Stage


User = get_user_model()

ROLE_PERMISSION_CODES = {
    "recruiter": (
        "hydra_people.change_person",
        "hydra_people.link_candidate",
        "recruitment.add_candidate",
        "recruitment.change_candidate",
    ),
    "hr_admin": ("hydra_people.change_person",),
    "coordination": (
        "hydra_coordination.change_personassignment",
        "hydra_coordination.assign_person",
    ),
    "employee": ("hydra_tasks.transition_hydratask",),
    "legal_housing": ("hydra_housing.change_housingfacility",),
    "onboarding": ("hydra_onboarding.change_course",),
    "dashboard": (),
}
VIEW_APPS = {
    "base",
    "employee",
    "recruitment",
    "hydra_arrivals",
    "hydra_coordination",
    "hydra_documents",
    "hydra_housing",
    "hydra_legalization",
    "hydra_notifications",
    "hydra_onboarding",
    "hydra_people",
    "hydra_reports",
    "hydra_tasks",
}


def _permissions_for_role(role):
    permissions = Permission.objects.filter(
        content_type__app_label__in=VIEW_APPS,
        codename__startswith="view_",
    )
    requested = []
    for value in ROLE_PERMISSION_CODES[role]:
        app_label, codename = value.split(".", 1)
        requested.append(
            Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            ).pk
        )
    return list(permissions) + list(Permission.objects.filter(pk__in=requested))


class Command(BaseCommand):
    help = "Seed an isolated, prefixed Hydra authenticated load-test data set."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--users", type=int, default=200)

    @transaction.atomic
    def handle(self, *args, **options):
        run_id = validate_run_id(options["run_id"])
        counts = role_counts(options["users"])
        password = os.environ.get("HYDRA_LOAD_TEST_PASSWORD", "")
        if len(password) < 16 or "replace" in password.lower():
            raise CommandError(
                "HYDRA_LOAD_TEST_PASSWORD must contain at least 16 non-placeholder characters."
            )
        username_prefix = f"hydra-load-{run_id}-"
        if User.objects.filter(username__startswith=username_prefix).exists():
            raise CommandError("This load-test run id already exists; choose a new run id.")

        prefix = object_prefix(run_id)
        company = Company.objects.create(
            company=f"{prefix} Company",
            address=f"{prefix} isolated staging",
            country="PL",
            state="Mazowieckie",
            city="Warsaw",
            zip="00-001",
        )
        # Department.save() in the inherited application passes keyword
        # arguments to clean(), so Manager.create(force_insert=True) is unsafe.
        department = Department(department=f"{prefix} Operations")
        department.save()
        department.company_id.add(company)
        position = JobPosition._base_manager.create(
            job_position=f"{prefix} Worker",
            department_id=department,
        )
        position.company_id.add(company)
        location = Location._base_manager.create(
            company=company,
            name=f"{prefix} Location",
            code=f"LT{company.pk}",
            address=f"{prefix} address",
        )
        section = Section._base_manager.create(
            location=location,
            department=department,
            name=f"{prefix} Section",
            code=f"LS{company.pk}",
        )
        team = Team._base_manager.create(
            section=section,
            name=f"{prefix} Team",
            code=f"TM{company.pk}",
        )
        recruitment = Recruitment._base_manager.create(
            title=f"{prefix} Recruitment",
            description="Isolated Hydra load-test recruitment",
            company_id=company,
            vacancy=max(counts["recruiter"], 1),
            is_published=False,
            optional_profile_image=True,
            optional_resume=True,
        )
        recruitment.open_positions.add(position)
        initial_stage = Stage._base_manager.create(
            recruitment_id=recruitment,
            stage=f"{prefix} Initial",
            stage_type="initial",
            sequence=1,
        )
        applied_stage = Stage._base_manager.create(
            recruitment_id=recruitment,
            stage=f"{prefix} Applied",
            stage_type="applied",
            sequence=2,
        )
        for source, target in (
            (initial_stage, applied_stage),
            (applied_stage, initial_stage),
        ):
            RecruitmentStageTransitionRule.objects.update_or_create(
                recruitment=recruitment,
                from_stage=source,
                to_stage=target,
                defaults={
                    **default_transition_rule_values(
                        from_stage=source,
                        to_stage=target,
                    ),
                    "is_active": True,
                },
            )

        groups = {}
        for role in ROLE_WEIGHTS:
            group, _created = Group.objects.get_or_create(name=group_name(run_id, role))
            group.permissions.set(_permissions_for_role(role))
            groups[role] = group

        encoded_password = make_password(password)
        created = 0
        for role, role_total in counts.items():
            for index in range(1, role_total + 1):
                username = username_for(run_id, role, index)
                user_values = {
                    "username": username,
                    "email": f"{username}@example.invalid",
                    "password": encoded_password,
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                }
                if any(field.name == "is_new_employee" for field in User._meta.fields):
                    user_values["is_new_employee"] = False
                user = User.objects.create(**user_values)
                user.groups.add(groups[role])
                employee = Employee._base_manager.create(
                    employee_user_id=user,
                    employee_first_name="Hydra",
                    employee_last_name=f"Load {created + 1}",
                    email=user.email,
                    phone=f"+487{created + 1:08d}",
                    is_active=True,
                )
                # Employee post-save creates this OneToOne projection.
                work_info, _created = EmployeeWorkInformation._base_manager.get_or_create(
                    employee_id=employee
                )
                work_info.department_id = department
                work_info.job_position_id = position
                work_info.company_id = company
                work_info.email = user.email
                work_info.mobile = employee.phone
                work_info.date_joining = timezone.localdate()
                work_info.save()
                ScopeGrant._base_manager.create(
                    user=user,
                    company=company,
                    valid_from=timezone.localdate(),
                    created_by=user,
                    modified_by=user,
                )
                person = Person(
                    passport_name=f"{prefix} Person {created + 1}",
                    first_name="Hydra",
                    last_name=f"Load {created + 1}",
                    date_of_birth=date(1990, 1, (created % 27) + 1),
                    citizenship="PL",
                    preferred_language=Person.PreferredLanguage.ENGLISH,
                    email=f"person-{created + 1}@example.invalid",
                    phone=f"+486{created + 1:08d}",
                    lifecycle_state=Person.LifecycleState.CANDIDATE,
                    created_by=user,
                    modified_by=user,
                )
                person.full_clean()
                person.save()
                assignment = PersonAssignment(
                    person=person,
                    team=team,
                    department=department,
                    valid_from=timezone.localdate(),
                    is_primary=True,
                    created_by=user,
                    modified_by=user,
                )
                assignment.full_clean()
                assignment.save()

                if role == "recruiter":
                    recruitment.recruitment_managers.add(employee)
                    candidate = Candidate(
                        recruitment_id=recruitment,
                        job_position_id=position,
                        email=f"candidate-{created + 1}@example.invalid",
                        mobile=f"+485{created + 1:08d}",
                        resume=f"load-tests/{run_id}/{created + 1}.pdf",
                        source="software",
                    )
                    candidate, _link = create_candidate_application(
                        person=person,
                        candidate=candidate,
                        actor=user,
                    )
                    transition_candidate(
                        candidate=candidate,
                        target_stage=applied_stage,
                        actor=user,
                    )
                elif role == "employee":
                    task = HydraTask(
                        company=company,
                        person=person,
                        assignee=user,
                        title=f"{prefix} Employee task {created + 1}",
                        description="Isolated load-test task",
                        target_kind=TaskTargetKind.PERSON,
                        target_uuid=person.uuid,
                        target_label=person.hydra_id,
                        created_by=user,
                        modified_by=user,
                    )
                    task.full_clean()
                    task.save()
                    HydraTaskEvent.objects.create(
                        task=task,
                        sequence=1,
                        action=HydraTaskEvent.Action.CREATED,
                        actor=user,
                        to_status=task.status,
                        to_assignee=user,
                        to_priority=task.priority,
                        changed_fields=["status", "assignee"],
                    )
                elif role == "legal_housing":
                    facility = HousingFacility(
                        location=location,
                        name=f"{prefix} Facility {created + 1}",
                        address=f"{prefix} address {created + 1}",
                        notes="Load-test review A",
                        created_by=user,
                        modified_by=user,
                    )
                    facility.full_clean()
                    facility.save()
                elif role == "onboarding":
                    course = Course(
                        company=company,
                        code=f"LT{created + 1}",
                        name=f"{prefix} Course {created + 1}",
                        description="Load-test onboarding revision A",
                        default_language=Person.PreferredLanguage.ENGLISH,
                        created_by=user,
                        modified_by=user,
                    )
                    course.full_clean()
                    course.save()
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created} isolated Hydra load-test accounts for run {run_id}."
            )
        )
