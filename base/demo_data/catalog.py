"""Canonical enterprise taxonomy and rename maps for demo data."""

from __future__ import annotations

# pk → standard department name (in-place rename preserves FKs)
DEPARTMENT_RENAMES: dict[int, str] = {
    1: "Engineering",
    2: "Sales",
    3: "Human Resources",
    4: "Marketing",
    5: "Finance",
    6: "Operations",
}

# pk → standard job position name
JOB_POSITION_RENAMES: dict[int, str] = {
    1: "Software Engineer",
    2: "Backend Engineer",
    3: "Sales Associate",
    4: "Training and Development Coordinator",
    5: "Compensation and Benefits Specialist",
    6: "Recruiter",
    7: "Marketing Specialist",
    8: "Digital Marketing Specialist",
    9: "Content Creator",
    10: "Social Media Coordinator",
    11: "Chief Financial Officer",
    12: "Financial Analyst",
    13: "Accounts Payable Clerk",
    14: "Tax Accountant",
    15: "System Administrator",
    16: "Frontend Engineer",
    17: "Mobile Engineer",
    18: "Sales Representative",
    19: "Sales Manager",
    20: "Business Development Manager",
    21: "Field Sales Executive",
    22: "HR Manager",
    23: "HR Business Partner",
    24: "Senior Manager",
}

# pk → standard job role name
JOB_ROLE_RENAMES: dict[int, str] = {
    1: "Junior Software Engineer",
    2: "Junior Backend Engineer",
    # 3 Intern — already fine
    # 4 Sales Manager role under Sales Associate — leave unless informal
}

# Additional role renames by exact current label
JOB_ROLE_LABEL_RENAMES: dict[str, str] = {
    "Jnr Dev": "Junior Engineer",
    "Jnr Manager": "Junior Manager",
    "Sales Man": "Sales Associate",
    "Sales Manage": "Sales Manager",
}

COMPANY_PROFILES: dict[str, dict] = {
    "Your Company": {
        "hq": True,
        "address": "100 Market Street, Suite 400",
        "country": "United States",
        "state": "Nevada",
        "city": "Las Vegas",
        "zip": "89101",
        "is_active": True,
    },
    "Your Company Inc.": {
        "hq": False,
        "address": "The Estate, 8th Floor, MG Road",
        "country": "India",
        "state": "Karnataka",
        "city": "Bengaluru",
        "zip": "560001",
        "is_active": True,
    },
    "Your Company Ltd.": {
        "hq": False,
        "address": "Alpha House, 25 Borough High Street",
        "country": "United Kingdom",
        "state": "England",
        "city": "London",
        "zip": "SE1 1LB",
        "is_active": True,
    },
}

# Global string scrub applied to selected Char/Text fields and side fixtures
STRING_REPLACEMENTS: list[tuple[str, str]] = [
    ("Cybrosys", "Partner Co"),
    ("cybrosys.in", "example.com"),
    ("cybrosys.com", "example.com"),
    ("Horilla Next Inc.", "Your Company"),
    ("Horilla OpenSource HRMS", "Enterprise HR Platform"),
    ("Horilla Family Day", "Company Family Day"),
    ("Horilla Technical Meeting", "Engineering Sync"),
    ("S/W Dept", "Engineering"),
    ("Hr Dept", "Human Resources"),
    ("Sales Dept", "Sales"),
    ("Marketing Dept", "Marketing"),
    ("Finance Dept", "Finance"),
    ("Odoo Dev", "Software Engineer"),
    ("Django Dev", "Backend Engineer"),
    ("React Dev", "Frontend Engineer"),
    ("Flutter Dev", "Mobile Engineer"),
    ("Sales Man", "Sales Associate"),
    ("Sales Manage", "Sales Manager"),
    ("System Admin", "System Administrator"),
    ("Jnr Dev", "Junior Engineer"),
    ("Jnr Manager", "Junior Manager"),
    ("Odoo Developer Template", "Software Engineer Assessment"),
    ("working with Odoo", "professional software development"),
    ("Odoo's ORM", "an ORM framework"),
    ("Odoo module", "application module"),
    ("Odoo report", "business report"),
    ("Odoo Studio", "low-code customization tools"),
    ("Odoo development", "Python development"),
    ("OdooÆs ORM", "a modern ORM"),
    ("Odoo", "application"),
]
