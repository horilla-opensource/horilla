"""Assets: the asset register itself, with no employee needed. Categories and batches are made as needed."""

import re

from django.db import transaction
from django.utils import timezone

from asset.models import Asset, AssetCategory, AssetItem, AssetLot
from employee.methods.methods import import_valid_date

from .asset_allocation import AssetAllocationDataset
from .base import Checked, Context, Dataset, Field


class AssetsDataset(Dataset):
    key = "assets"
    label = "Assets"
    subtitle = "Asset register: category, batch, cost and warranty"
    icon = "cube-outline"
    permission = "asset.add_asset"
    update_permissions = ["asset.change_asset"]
    supports_update = True
    match_choices = ["Serial No."]
    default_match_keys = ["Serial No."]
    locked_match_keys = ["Serial No."]
    match_help = (
        "Each row must find one asset by its Serial No. Only what the sheet fills in is changed; "
        "blank cells leave the current value alone, and a quantity can only be raised."
    )
    hint_create = (
        "Adds assets to the register. A Serial No. that already exists is refused."
    )
    hint_update = (
        "Finds each asset by Serial No. and changes only what the sheet fills in."
    )
    hint_both = "Updates assets that exist, and creates the rest with their categories and batches, in one import."
    created_models = {"categories": AssetCategory, "batches": AssetLot, "assets": Asset}
    preview_columns = [
        "Serial No.",
        "Asset Name",
        "Category",
        "Purchase Date",
        "Purchase Cost",
        "Quantity",
    ]
    upload_note = (
        "Each row is one asset, found by its Serial No. A Quantity above 1 makes that many units. "
        "Categories and batches that do not exist yet are created from their names. To give assets to "
        "employees, use Asset Allocation."
    )

    fields = [
        Field(
            "Serial No.",
            required=True,
            group="Asset",
            sample="LAP-1001",
            aliases=(
                "serial",
                "serial number",
                "serial no",
                "tracking id",
                "asset tracking id",
                "asset id",
                "id",
            ),
        ),
        Field(
            "Asset Name",
            required=True,
            group="Asset",
            sample="Laptop 14-inch",
            aliases=("asset", "name", "item", "asset title"),
        ),
        Field(
            "Asset Description",
            group="Asset",
            sample="16GB RAM, 512GB SSD",
            aliases=("description", "asset details", "details"),
        ),
        Field(
            "Category",
            required=True,
            group="Category",
            sample="Electronics",
            aliases=("asset category", "category name", "type"),
            kind="suggest",
            suggest="categories",
        ),
        Field(
            "Category Description",
            group="Category",
            sample="Laptops, monitors and phones",
            aliases=("asset category description",),
        ),
        Field(
            "Purchase Date",
            required=True,
            group="Purchase",
            sample="2024-01-10",
            aliases=("bought on", "date of purchase", "purchased"),
            kind="date",
        ),
        Field(
            "Purchase Cost",
            required=True,
            group="Purchase",
            sample="78000.50",
            aliases=("cost", "price", "amount", "purchase price"),
            kind="number",
        ),
        Field(
            "Quantity",
            group="Purchase",
            sample="1",
            aliases=("qty", "units", "count"),
            kind="number",
        ),
        Field(
            "Batch Number",
            group="Batch",
            sample="B-2024-01",
            aliases=("batch", "lot", "lot number", "batch no"),
            kind="suggest",
            suggest="batches",
        ),
        Field(
            "Batch Description",
            group="Batch",
            sample="",
            aliases=("lot description", "batch details"),
        ),
        Field(
            "Warranty Expiry Date",
            group="Warranty",
            sample="2027-01-10",
            aliases=("warranty", "expiry date", "warranty end", "expiry"),
            kind="date",
        ),
        Field(
            "Notify Before (Days)",
            group="Warranty",
            sample="30",
            aliases=("notify before", "notify days", "warranty notify"),
            kind="number",
        ),
    ]

    def suggestions(self):
        return {
            "categories": sorted(
                AssetCategory.objects.entire().values_list(
                    "asset_category_name", flat=True
                )
            ),
            "batches": sorted(
                AssetLot.objects.entire().values_list("lot_number", flat=True)
            ),
        }

    def prepare(self, rows, ctx):
        for row in rows:
            for key in ("Serial No.", "Batch Number"):
                value = row.get(key)
                if isinstance(value, float) and value.is_integer():
                    value = int(value)
                row[key] = str(value).strip() if value not in (None, "") else None
            for key in ("Purchase Date", "Warranty Expiry Date"):
                value = row.get(key)
                if isinstance(value, str) and re.match(
                    r"^\d{4}-\d{2}-\d{2}[ T]", value
                ):
                    row[key] = value[:10]
        return rows

    # -------------------------------------------------------------- check
    def check(
        self, rows, ctx: Context, progress=None, mode="create", match_keys=()
    ) -> Checked:
        rows = self.prepare(rows, ctx)
        result = Checked()
        today = timezone.now().date()
        assets = {
            a.asset_tracking_id: a
            for a in Asset.objects.entire().select_related(
                "asset_category_id", "asset_lot_number_id"
            )
        }
        categories = {c.asset_category_name for c in AssetCategory.objects.entire()}
        lots = {l.lot_number for l in AssetLot.objects.entire()}
        item_ids = set(AssetItem.objects.entire().values_list("tracking_id", flat=True))
        seen = set()
        total = len(rows) or 1

        for position, row in enumerate(rows, start=1):
            if progress and (position % 25 == 0 or position == total):
                progress(5 + int(position / total * 90))
            errors = {}
            errors.update(AssetAllocationDataset._too_long(row))
            serial = row.get("Serial No.")
            asset = assets.get(serial) if serial else None
            if not serial:
                errors["Serial No. Error"] = "Serial No. is required."
            elif serial in seen:
                errors["Serial No. Error"] = (
                    "This Serial No. appears more than once in the file."
                )
            elif asset is not None and mode == "create":
                errors["Serial No. Error"] = (
                    "An asset with this Serial No. already exists."
                )
            elif asset is None and mode == "update":
                errors["Serial No. Error"] = "This asset does not exist."
            if serial:
                seen.add(serial)

            if "Serial No. Error" in errors or (not serial):
                result.errors.append(self._error_entry(row, errors))
                continue

            if asset is not None:  # update
                apply = {"asset": {}, "category": None, "lot": None}
                changes = []

                def note(label, old, new, changes=changes):
                    changes.append(
                        f"{label}: {old if old not in (None, '') else '-'} → {new}"
                    )

                def date(label, row=row, errors=errors):
                    date_errors = {}
                    parsed = import_valid_date(
                        row[label], label, date_errors, f"{label} Error"
                    )
                    errors.update(date_errors)
                    return parsed

                AssetAllocationDataset._asset_changes(
                    row,
                    asset,
                    categories,
                    lots,
                    item_ids,
                    errors,
                    apply,
                    note,
                    date,
                    today,
                )
                if errors:
                    result.errors.append(self._error_entry(row, errors))
                elif not changes:
                    result.unchanged.append(row)
                else:
                    row.update(
                        {
                            "__op": "update",
                            "__pk": asset.pk,
                            "__apply": apply,
                            "__changes": changes,
                        }
                    )
                    result.valid.append(row)
                continue

            if (
                not AssetAllocationDataset._new_asset_problems(
                    row, serial, item_ids, errors
                )
                or errors
            ):
                result.errors.append(self._error_entry(row, errors))
                continue
            row["__op"] = "create"
            row["__create_asset"] = True
            row["__changes"] = ["New asset"] if mode == "both" else []
            result.valid.append(row)

        result.errors.sort(key=lambda e: e["row"])
        result.will_create = AssetAllocationDataset._will_create(result.valid)
        if progress:
            progress(100)
        return result

    @staticmethod
    def _error_entry(row, errors):
        keys = {f.key for f in AssetsDataset.fields}
        by_field = {
            k[: -len(" Error")]: v
            for k, v in errors.items()
            if k[: -len(" Error")] in keys
        }
        return {
            "row": int(row.get("__row") or 0),
            "name": row.get("Asset Name") or "-",
            "badge": row.get("Serial No.") or "-",
            "messages": list(errors.values()),
            "by_field": by_field,
            "data": {k: v for k, v in row.items() if k in keys},
        }

    # ------------------------------------------------------------- commit
    def commit(self, rows, ctx: Context, mode="create", progress=None) -> dict:
        counts = {"categories": 0, "batches": 0}
        made = changed = 0
        total = len(rows) or 1
        with transaction.atomic():
            categories = {
                c.asset_category_name: c for c in AssetCategory.objects.entire()
            }
            lots = {l.lot_number: l for l in AssetLot.objects.entire()}
            for position, row in enumerate(rows, start=1):
                if row.get("__op") == "update":
                    asset = Asset.objects.entire().get(pk=row["__pk"])
                    AssetAllocationDataset._apply_asset(
                        asset, row["__apply"], row, ctx, categories, lots, counts
                    )
                    changed += 1
                else:
                    AssetAllocationDataset._make_asset(
                        row, ctx, categories, lots, counts
                    )
                    made += 1
                if progress and (position % 10 == 0 or position == total):
                    progress(5 + int(position / total * 90))
        if progress:
            progress(100)
        return {
            "assigned": made,
            "updated": changed,
            "assets": made,
            "categories": counts["categories"],
            "batches": counts["batches"],
        }
