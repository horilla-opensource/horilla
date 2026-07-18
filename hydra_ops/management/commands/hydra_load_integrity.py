import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Exists, F, Max, OuterRef, Q

from employee.models import EmployeeWorkInformation
from hydra_coordination.models import PersonAssignment, ScopeGrant
from hydra_housing.models import HousingFacility
from hydra_onboarding.models import Course
from hydra_ops.load_test import ROLE_WEIGHTS, group_name, role_counts, validate_run_id
from hydra_people.models import CandidateStageTransition, Person, PersonApplication
from hydra_tasks.models import HydraTask
from recruitment.models import Candidate


User = get_user_model()


class Command(BaseCommand):
    help = "Fail unless an isolated Hydra load-test data set remains internally consistent."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--users", type=int, default=200)
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        run_id = validate_run_id(options["run_id"])
        expected = role_counts(options["users"])
        prefix = f"hydra-load-{run_id}-"
        users = User.objects.filter(username__startswith=prefix)
        failures = []
        if users.count() != options["users"]:
            failures.append("account_count")
        if users.filter(is_active=False).exists():
            failures.append("inactive_account")
        if users.filter(employee_get__isnull=True).exists():
            failures.append("missing_employee")
        if users.annotate(grants=Count("hydra_scope_grants")).exclude(grants=1).exists():
            failures.append("scope_grant_count")
        load_group_prefix = f"HYDRA_LOAD:{run_id}:"
        if users.annotate(
            load_groups=Count(
                "groups",
                filter=Q(groups__name__startswith=load_group_prefix),
            )
        ).exclude(load_groups=1).exists():
            failures.append("load_group_count")
        if ScopeGrant.objects.filter(user__in=users).exclude(company__company__startswith="HYDRA_LOAD_").exists():
            failures.append("organization_isolation")
        for role in ROLE_WEIGHTS:
            actual = users.filter(groups__name=group_name(run_id, role)).count()
            if actual != expected[role]:
                failures.append(f"role_count:{role}")
        people = Person._base_manager.filter(created_by__in=users)
        if people.count() != options["users"] or (
            people.values("created_by").annotate(total=Count("pk")).exclude(total=1).exists()
        ):
            failures.append("person_count")
        assignments = PersonAssignment._base_manager.filter(created_by__in=users)
        if assignments.count() != options["users"]:
            failures.append("assignment_count")
        if assignments.filter(
            valid_until__lt=F("valid_from")
        ).exists():
            failures.append("assignment_dates")
        matching_grant = ScopeGrant._base_manager.filter(
            user_id=OuterRef("created_by_id"),
            company_id=OuterRef("team__section__location__company_id"),
        )
        if assignments.annotate(has_matching_grant=Exists(matching_grant)).filter(
            has_matching_grant=False
        ).exists():
            failures.append("assignment_organization_isolation")
        work_information = EmployeeWorkInformation._base_manager.filter(
            employee_id__employee_user_id__in=users
        )
        if work_information.count() != options["users"] or work_information.exclude(
            company_id__company__startswith="HYDRA_LOAD_"
        ).exists():
            failures.append("employee_work_organization")

        candidates = Candidate._base_manager.filter(created_by__in=users)
        if candidates.count() != expected["recruiter"]:
            failures.append("candidate_count")
        if candidates.exclude(hydra_person_link__isnull=False).exists():
            failures.append("candidate_person_link")
        if PersonApplication.objects.filter(candidate__in=candidates).count() != candidates.count():
            failures.append("candidate_link_count")
        for candidate in candidates.select_related("stage_id"):
            latest = CandidateStageTransition.objects.filter(candidate=candidate).order_by(
                "-occurred_at", "-pk"
            ).first()
            if latest is None or latest.to_stage_id != candidate.stage_id_id:
                failures.append("candidate_transition_atomicity")
                break

        tasks = HydraTask._base_manager.filter(created_by__in=users)
        if tasks.count() != expected["employee"]:
            failures.append("task_count")
        invalid_tasks = tasks.annotate(
            event_count=Count("events"),
            latest_sequence=Max("events__sequence"),
        ).exclude(event_count=F("version"), latest_sequence=F("version"))
        if invalid_tasks.exists() or tasks.filter(version__lt=1).exists():
            failures.append("task_version")
        if HousingFacility._base_manager.filter(created_by__in=users).count() != expected[
            "legal_housing"
        ]:
            failures.append("housing_facility_count")
        if Course._base_manager.filter(created_by__in=users).count() != expected[
            "onboarding"
        ]:
            failures.append("onboarding_course_count")
        duplicate_usernames = (
            users.values("username").annotate(total=Count("pk")).filter(total__gt=1).exists()
        )
        if duplicate_usernames:
            failures.append("duplicate_username")

        payload = {
            "status": "ok" if not failures else "failed",
            "run_id": run_id,
            "users": users.count(),
            "candidates": candidates.count(),
            "people": people.count(),
            "assignments": assignments.count(),
            "tasks": tasks.count(),
            "failures": failures,
        }
        if options["json"]:
            self.stdout.write(json.dumps(payload, sort_keys=True))
        else:
            self.stdout.write(
                f"Hydra load integrity {payload['status']}: {payload['users']} users"
            )
        if failures:
            raise CommandError("Load-test integrity failed: " + ", ".join(failures))
