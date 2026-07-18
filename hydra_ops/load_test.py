import re
from collections import OrderedDict


LOAD_TEST_PREFIX = "HYDRA_LOAD"
RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,30}$")
ROLE_WEIGHTS = OrderedDict(
    (
        ("recruiter", 25),
        ("hr_admin", 20),
        ("coordination", 15),
        ("employee", 15),
        ("legal_housing", 10),
        ("onboarding", 10),
        ("dashboard", 5),
    )
)
LOAD_STAGES = (20, 50, 100, 150, 200)


def validate_run_id(run_id):
    normalized = str(run_id or "").strip().lower()
    if not RUN_ID_PATTERN.fullmatch(normalized):
        raise ValueError("run id must contain 3-31 lowercase letters, digits, or hyphens")
    return normalized


def role_counts(total_users):
    total_users = int(total_users)
    if total_users not in LOAD_STAGES:
        raise ValueError("total users must be one of 20, 50, 100, 150, or 200")

    # Hamilton allocation preserves the requested percentages while ensuring
    # integer account counts add up to stages such as 50 and 150.
    counts = {
        role: total_users * weight // 100 for role, weight in ROLE_WEIGHTS.items()
    }
    missing = total_users - sum(counts.values())
    remainders = sorted(
        ROLE_WEIGHTS,
        key=lambda role: (-(total_users * ROLE_WEIGHTS[role] % 100), list(ROLE_WEIGHTS).index(role)),
    )
    for role in remainders[:missing]:
        counts[role] += 1
    return counts


def username_for(run_id, role, index):
    return f"hydra-load-{validate_run_id(run_id)}-{role}-{int(index):03d}"


def group_name(run_id, role):
    if role not in ROLE_WEIGHTS:
        raise ValueError("unknown load-test role")
    return f"{LOAD_TEST_PREFIX}:{validate_run_id(run_id)}:{role}"


def object_prefix(run_id):
    return f"{LOAD_TEST_PREFIX}_{validate_run_id(run_id).upper().replace('-', '_')}"
