"""
Factory Boy factories for asset module models.

Usage:
    category = AssetCategoryFactory()
    lot = AssetLotFactory()
    asset = AssetFactory(asset_category_id=category)
    assignment = AssetAssignmentFactory(asset_id=asset, assigned_to_employee_id=emp)
    request = AssetRequestFactory(requested_employee_id=emp, asset_category_id=category)
"""

from datetime import date, timedelta
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from asset.models import (
    Asset,
    AssetAssignment,
    AssetCategory,
    AssetLot,
    AssetReport,
    AssetRequest,
)
from employee.tests.factories import EmployeeFactory


class AssetCategoryFactory(DjangoModelFactory):
    class Meta:
        model = AssetCategory

    asset_category_name = factory.Sequence(lambda n: f"Category {n}")
    asset_category_description = factory.Faker("sentence")

    @factory.post_generation
    def company_id(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if hasattr(extracted, "__iter__"):
                for company in extracted:
                    self.company_id.add(company)
            else:
                self.company_id.add(extracted)


class AssetLotFactory(DjangoModelFactory):
    class Meta:
        model = AssetLot

    lot_number = factory.Sequence(lambda n: f"LOT-{n:05d}")
    lot_description = factory.Faker("sentence")

    @factory.post_generation
    def company_id(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if hasattr(extracted, "__iter__"):
                for company in extracted:
                    self.company_id.add(company)
            else:
                self.company_id.add(extracted)


class AssetFactory(DjangoModelFactory):
    class Meta:
        model = Asset

    asset_name = factory.Sequence(lambda n: f"Asset {n}")
    asset_tracking_id = factory.Sequence(lambda n: f"TRK-{n:06d}")
    asset_description = factory.Faker("sentence")
    asset_purchase_date = factory.LazyFunction(date.today)
    asset_purchase_cost = factory.LazyFunction(lambda: Decimal("999.99"))
    asset_category_id = factory.SubFactory(AssetCategoryFactory)
    asset_status = "Available"
    asset_lot_number_id = factory.SubFactory(AssetLotFactory)


class AssetReportFactory(DjangoModelFactory):
    class Meta:
        model = AssetReport

    title = factory.Sequence(lambda n: f"Report {n}")
    asset_id = factory.SubFactory(AssetFactory)


class AssetAssignmentFactory(DjangoModelFactory):
    class Meta:
        model = AssetAssignment

    asset_id = factory.SubFactory(AssetFactory)
    assigned_to_employee_id = factory.SubFactory(EmployeeFactory)
    assigned_by_employee_id = factory.SubFactory(EmployeeFactory)
    return_date = None
    return_condition = None
    return_status = None


class AssetRequestFactory(DjangoModelFactory):
    class Meta:
        model = AssetRequest

    requested_employee_id = factory.SubFactory(EmployeeFactory)
    asset_category_id = factory.SubFactory(AssetCategoryFactory)
    description = factory.Faker("sentence")
    asset_request_status = "Requested"
