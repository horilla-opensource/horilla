import itertools
import os
import random
import uuid

from locust import HttpUser, LoadTestShape, between, events, task
from locust.exception import StopUser

from load_tests.cookies import prepare_internal_http_cookies


RUN_ID = os.environ["HYDRA_LOAD_TEST_RUN_ID"]
PASSWORD = os.environ["HYDRA_LOAD_TEST_PASSWORD"]
SHAPE = os.environ.get("HYDRA_LOAD_SHAPE", "standard")
REQUESTED_USERS = int(os.environ.get("HYDRA_LOAD_USERS", "200"))
HOST_HEADER = os.environ.get("HYDRA_LOAD_HOST_HEADER", "localhost")
THINK_TIME_MIN_SECONDS = float(os.environ["HYDRA_LOAD_THINK_TIME_MIN_SECONDS"])
THINK_TIME_MAX_SECONDS = float(os.environ["HYDRA_LOAD_THINK_TIME_MAX_SECONDS"])
if not 1 <= THINK_TIME_MIN_SECONDS <= THINK_TIME_MAX_SECONDS <= 120:
    raise RuntimeError("Hydra load think time must be between 1 and 120 seconds")
ROLE_CAPACITY = {
    "recruiter": 50,
    "hr_admin": 40,
    "coordination": 30,
    "employee": 30,
    "legal_housing": 20,
    "onboarding": 20,
    "dashboard": 10,
}
ALLOCATORS = {role: itertools.count(1) for role in ROLE_CAPACITY}


def _stage_role_counts(total):
    if total not in {20, 50, 100, 150, 200}:
        raise RuntimeError("HYDRA_LOAD_USERS must be a supported Hydra stage")
    weights = list(ROLE_CAPACITY)
    percentages = (25, 20, 15, 15, 10, 10, 5)
    counts = {
        role: total * percentage // 100
        for role, percentage in zip(weights, percentages)
    }
    missing = total - sum(counts.values())
    order = sorted(
        range(len(weights)),
        key=lambda index: (-(total * percentages[index] % 100), index),
    )
    for index in order[:missing]:
        counts[weights[index]] += 1
    return counts


STANDARD_COUNTS = _stage_role_counts(REQUESTED_USERS)


def _fixed_count(role):
    return STANDARD_COUNTS[role] if SHAPE == "standard" else 0


_stats_reset = False
_environment = None


@events.init.add_listener
def remember_environment(environment, **_kwargs):
    global _environment
    _environment = environment


@events.spawning_complete.add_listener
def reset_warmup_stats(user_count, **_kwargs):
    """Reset the spike baseline once; standard stages retain every login."""

    global _stats_reset
    if (
        SHAPE == "spike"
        and not _stats_reset
        and user_count >= 50
        and _environment is not None
    ):
        _environment.stats.reset_all()
        _stats_reset = True


class HydraBusinessUser(HttpUser):
    abstract = True
    role = ""
    weight = 0
    wait_time = between(THINK_TIME_MIN_SECONDS, THINK_TIME_MAX_SECONDS)

    def on_start(self):
        # Docker's internal hop is HTTP, but Nginx represents the TLS
        # terminator used in staging. Preserve Django's HTTPS/CSRF semantics
        # while allowing Requests to return Secure cookies on this private hop.
        self.client.headers.update(
            {
                "Host": HOST_HEADER,
                "X-Forwarded-Proto": "https",
                "Referer": f"https://{HOST_HEADER}/",
            }
        )
        index = next(ALLOCATORS[self.role])
        if index > ROLE_CAPACITY[self.role]:
            raise StopUser
        self.username = f"hydra-load-{RUN_ID}-{self.role}-{index:03d}"
        self.request_prefix = f"load-{RUN_ID}-{self.role}-{index:03d}"
        with self.client.get("/login/", name="GET /login/ [login]", catch_response=True) as response:
            csrf = response.cookies.get("hydra_csrftoken") or self.client.cookies.get(
                "hydra_csrftoken"
            )
            if response.status_code != 200 or not csrf:
                response.failure("login page or CSRF cookie unavailable")
                raise StopUser
        self._prepare_internal_request()
        with self.client.post(
            "/login/",
            data={"username": self.username, "password": PASSWORD, "csrfmiddlewaretoken": csrf},
            headers={"X-CSRFToken": csrf, "X-Request-ID": self._request_id()},
            allow_redirects=False,
            name="POST /login/ [login]",
            catch_response=True,
        ) as response:
            session = self.client.cookies.get("hydra_sessionid")
            if response.status_code != 302 or not session:
                response.failure("authenticated session was not established")
                raise StopUser
        self._prepare_internal_request()

    def _prepare_internal_request(self):
        prepare_internal_http_cookies(self.client.cookies)

    def _request_id(self):
        return f"{self.request_prefix}-{uuid.uuid4().hex[:12]}"

    @task(8)
    def read_business_data(self):
        self._prepare_internal_request()
        query = random.choice(("", "HYDRA_LOAD", "Load", str(random.randint(1, 9))))
        marker = "typical-read" if self.role == "dashboard" else "list-filter"
        with self.client.get(
            f"/internal/load-test/{self.role}/read/",
            params={"q": query},
            headers={"X-Request-ID": self._request_id()},
            name=f"GET /internal/load-test/{self.role}/read/ [{marker}]",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"read returned {response.status_code}")

    @task(2)
    def write_business_data(self):
        if self.role == "dashboard":
            self.read_business_data()
            return
        self._prepare_internal_request()
        csrf = self.client.cookies.get("hydra_csrftoken")
        with self.client.post(
            f"/internal/load-test/{self.role}/write/",
            data={"csrfmiddlewaretoken": csrf},
            headers={"X-CSRFToken": csrf, "X-Request-ID": self._request_id()},
            name=f"POST /internal/load-test/{self.role}/write/ [business-write]",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"write returned {response.status_code}")
            elif "action" not in response.text:
                response.failure("write response omitted action evidence")


class RecruiterUser(HydraBusinessUser):
    role = "recruiter"
    weight = 25
    fixed_count = _fixed_count(role)


class HrAdminUser(HydraBusinessUser):
    role = "hr_admin"
    weight = 20
    fixed_count = _fixed_count(role)


class CoordinationUser(HydraBusinessUser):
    role = "coordination"
    weight = 15
    fixed_count = _fixed_count(role)


class EmployeeUser(HydraBusinessUser):
    role = "employee"
    weight = 15
    fixed_count = _fixed_count(role)


class LegalHousingUser(HydraBusinessUser):
    role = "legal_housing"
    weight = 10
    fixed_count = _fixed_count(role)


class OnboardingUser(HydraBusinessUser):
    role = "onboarding"
    weight = 10
    fixed_count = _fixed_count(role)


class DashboardUser(HydraBusinessUser):
    role = "dashboard"
    weight = 5
    fixed_count = _fixed_count(role)


if SHAPE == "spike":

    class HydraSpikeShape(LoadTestShape):
        """Establish 50 sessions, ramp to 200 in exactly 60 seconds, then hold."""

        use_common_options = True

        def tick(self):
            elapsed = self.get_run_time()
            if elapsed < 5:
                return 50, 10
            if elapsed < 65:
                users = 50 + int(150 * ((elapsed - 5) / 60))
                return min(users, 200), 2.5
            if elapsed < 365:
                return 200, 2.5
            return None
