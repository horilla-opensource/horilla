"""
Enterprise demo-data seeder for Horilla HR.

Keeps the people layer (users/employees/avatars) from fixtures and
standardizes org taxonomy, module catalogs, media, and dynamic copy.
"""

from base.demo_data.runner import run_enterprise_demo_seeder

__all__ = ["run_enterprise_demo_seeder"]
