"""Asset allocation: which employee holds which asset. Assets and categories are made as needed."""

import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from asset.models import Asset, AssetAssignment, AssetCategory, AssetItem, AssetLot
from employee.methods.methods import clean_badge_id, import_valid_date
from employee.models import Employee

from .base import Checked, Context, Dataset, Field

STATUSES = {
    "minor damage": "Minor damage",
    "major damage": "Major damage",
    "healthy": "Healthy",
    "lost": "Lost",
}

# Where each column ends up, so a value too long for it is that row's problem.
LIMITS = {
    "Serial No.": (Asset, "asset_tracking_id"),
    "Asset Name": (Asset, "asset_name"),
    "Asset Description": (Asset, "asset_description"),
    "Category": (AssetCategory, "asset_category_name"),
    "Category Description": (AssetCategory, "asset_category_description"),
    "Batch Number": (AssetLot, "lot_number"),
}


def _whole(value, label, errors, minimum):
    """A whole number of at least ``minimum``; blank is None."""
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors[f"{label} Error"] = f"{label} must be a whole number."
        return None
    if number != int(number) or number < minimum:
        errors[f"{label} Error"] = (
            f"{label} must be a whole number of {minimum} or more."
        )
        return None
    return int(number)


class AssetAllocationDataset(Dataset):
    key = "asset_allocation"
    label = "Asset Allocation"
    subtitle = "Assets given to employees"
    icon = "laptop-outline"
    permission = "asset.add_assetassignment"
    update_permissions = ["asset.change_assetassignment", "asset.change_asset"]
    supports_update = True
    match_choices = ["Badge ID", "Serial No."]
    default_match_keys = ["Badge ID", "Serial No."]
    locked_match_keys = ["Badge ID", "Serial No."]
    match_help = (
        "Each row must find one allocation: the employee's hold on that asset. Only what the sheet fills in "
        "is changed, on the allocation (dates, return) and on the asset itself. Blank cells leave values alone."
    )
    hint_create = "Gives assets to employees, creating the asset, category and batch when they are new."
    hint_update = "Finds each allocation by Badge ID and Serial No., and changes only what the sheet fills in, on the allocation or the asset."
    hint_both = "Updates allocations that exist, and gives out the rest (creating assets, categories and batches as needed), in one import."
    created_models = {"categories": AssetCategory, "batches": AssetLot, "assets": Asset}
    preview_columns = [
        "Badge ID",
        "Serial No.",
        "Asset Name",
        "Category",
        "Assigned Date",
    ]
    upload_note = (
        "Each row gives one asset to one employee. An asset is found by its Serial No.; one that does not exist "
        "yet is created from the asset columns, with its category and batch if they are new too. Asset columns "
        "are ignored for assets that already exist. A row with a Return Date is recorded as already returned."
    )

    fields = [
        Field(
            "Badge ID",
            required=True,
            group="Allocation",
            sample="E-1048",
            aliases=(
                "employee badge id",
                "employee id",
                "emp id",
                "assigned to",
                "employee",
                "staff id",
                "badge",
            ),
        ),
        Field(
            "Serial No.",
            required=True,
            group="Allocation",
            sample="LAP-0001",
            aliases=(
                "serial",
                "serial number",
                "serial no",
                "tracking id",
                "asset tracking id",
                "asset serial no",
                "asset id",
            ),
        ),
        Field(
            "Assigned By",
            group="Allocation",
            sample="E-1001",
            aliases=("assigned by badge id", "given by", "allocated by"),
        ),
        Field(
            "Assigned Date",
            group="Allocation",
            sample="2024-02-01",
            aliases=("allocation date", "given on", "issue date", "date assigned"),
            kind="date",
        ),
        Field(
            "Return Date",
            group="Allocation",
            sample="",
            aliases=("returned on", "date returned"),
            kind="date",
        ),
        Field(
            "Return Status",
            group="Allocation",
            sample="",
            aliases=("return condition status", "returned as"),
            kind="choice",
            choices=("Minor damage", "Major damage", "Healthy", "Lost"),
        ),
        Field(
            "Return Condition",
            group="Allocation",
            sample="",
            aliases=("return notes", "return remarks", "condition"),
        ),
        Field(
            "Asset Name",
            group="Asset",
            sample="Laptop",
            aliases=("asset", "name", "item", "asset title"),
        ),
        Field(
            "Asset Description",
            group="Asset",
            sample="14-inch, 16GB",
            aliases=("description", "asset details"),
        ),
        Field(
            "Category",
            group="Asset",
            sample="Electronics",
            aliases=("asset category", "category name", "type"),
            kind="suggest",
            suggest="categories",
        ),
        Field(
            "Category Description",
            group="Asset",
            sample="",
            aliases=("asset category description",),
        ),
        Field(
            "Purchase Date",
            group="Asset",
            sample="2024-01-10",
            aliases=("bought on", "date of purchase", "purchased"),
            kind="date",
        ),
        Field(
            "Purchase Cost",
            group="Asset",
            sample="55000",
            aliases=("cost", "price", "amount", "purchase price"),
            kind="number",
        ),
        Field(
            "Quantity",
            group="Asset",
            sample="1",
            aliases=("qty", "units", "count"),
            kind="number",
        ),
        Field(
            "Batch Number",
            group="Asset",
            sample="B-01",
            aliases=("batch", "lot", "lot number", "batch no"),
            kind="suggest",
            suggest="batches",
        ),
        Field(
            "Warranty Expiry Date",
            group="Asset",
            sample="",
            aliases=("warranty", "expiry date", "warranty end", "expiry"),
            kind="date",
        ),
        Field(
            "Notify Before (Days)",
            group="Asset",
            sample="",
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
            for key in ("Badge ID", "Assigned By"):
                row[key] = clean_badge_id(row.get(key)) if row.get(key) else None
            for key in ("Serial No.", "Batch Number"):
                value = row.get(key)
                if isinstance(value, float) and value.is_integer():
                    value = int(value)
                row[key] = str(value).strip() if value not in (None, "") else None
            for key in (
                "Assigned Date",
                "Return Date",
                "Purchase Date",
                "Warranty Expiry Date",
            ):
                value = row.get(key)
                if isinstance(value, str) and re.match(
                    r"^\d{4}-\d{2}-\d{2}[ T]", value
                ):
                    row[key] = value[:10]
            status = row.get("Return Status")
            if status:
                row["Return Status"] = STATUSES.get(
                    str(status).strip().lower(), str(status).strip()
                )
        return rows

    # -------------------------------------------------------------- check
    def check(
        self, rows, ctx: Context, progress=None, mode="create", match_keys=()
    ) -> Checked:
        rows = self.prepare(rows, ctx)
        result = Checked()
        today = timezone.now().date()
        employees = {
            str(e.badge_id).strip().lower(): e
            for e in Employee.objects.entire()
            .select_related("employee_work_info")
            .filter(badge_id__isnull=False)
        }
        assets = {
            a.asset_tracking_id: a
            for a in Asset.objects.entire().select_related(
                "asset_category_id", "asset_lot_number_id"
            )
        }
        categories = {c.asset_category_name for c in AssetCategory.objects.entire()}
        lots = {l.lot_number for l in AssetLot.objects.entire()}
        holdings = {}
        for held in AssetAssignment.objects.entire().order_by("-id"):
            holdings.setdefault(
                (held.assigned_to_employee_id_id, held.asset_id_id), []
            ).append(held)
        seen = set()
        free = {}
        for asset_id, status in AssetItem.objects.entire().values_list(
            "asset_id_id", "status"
        ):
            if status == "Available":
                free[asset_id] = free.get(asset_id, 0) + 1
        item_ids = set(AssetItem.objects.entire().values_list("tracking_id", flat=True))
        planned = {}  # serial -> units still free on an asset this file creates
        importer = (
            getattr(ctx.user, "employee_get", None) if ctx.user is not None else None
        )
        total = len(rows) or 1

        for position, row in enumerate(rows, start=1):
            if progress and (position % 25 == 0 or position == total):
                progress(5 + int(position / total * 90))
            errors = {}
            errors.update(self._too_long(row))
            employee = self._employee(row.get("Badge ID"), employees, ctx, errors)

            # An allocation this employee already has of this asset: the live one, else (updating) the latest.
            serial = row.get("Serial No.")
            known_asset = assets.get(serial) if serial else None
            held = (
                holdings.get((employee.pk, known_asset.pk), [])
                if employee is not None and known_asset is not None
                else []
            )
            alloc = next((h for h in held if h.return_date is None), None)
            if alloc is None and mode == "update" and held:
                alloc = held[0]
            if mode == "update" and alloc is None:
                if not serial:
                    errors["Serial No. Error"] = "Serial No. is required."
                elif known_asset is None:
                    errors["Serial No. Error"] = "This asset does not exist."
                elif employee is not None:
                    errors["Serial No. Error"] = (
                        "This employee has no allocation of this asset."
                    )
            if alloc is not None and mode in ("update", "both"):
                if (employee.pk, known_asset.pk) in seen:
                    errors["Serial No. Error"] = (
                        "This employee and asset appear more than once in the file."
                    )
                seen.add((employee.pk, known_asset.pk))
                apply, changes = self._update_row(
                    row,
                    alloc,
                    known_asset,
                    employees,
                    categories,
                    lots,
                    item_ids,
                    errors,
                )
                if errors:
                    result.errors.append(self._error_entry(row, errors, employee))
                elif not changes:
                    result.unchanged.append(row)
                else:
                    row.update(
                        {
                            "__op": "update",
                            "__pk": alloc.pk,
                            "__apply": apply,
                            "__changes": changes,
                        }
                    )
                    result.valid.append(row)
                continue
            if mode == "update":
                result.errors.append(self._error_entry(row, errors, employee))
                continue

            assigner = importer
            if row.get("Assigned By"):
                assigner = employees.get(str(row["Assigned By"]).strip().lower())
                if assigner is None:
                    errors["Assigned By Error"] = "No employee has this Badge ID."
            elif assigner is None:
                errors["Assigned By Error"] = (
                    "Assigned By is needed: your own login has no employee profile."
                )

            assigned = returned = None
            if row.get("Assigned Date"):
                date_errors = {}
                assigned = import_valid_date(
                    row["Assigned Date"],
                    "Assigned Date",
                    date_errors,
                    "Assigned Date Error",
                )
                errors.update(date_errors)
                if assigned and assigned > today:
                    errors["Assigned Date Error"] = (
                        "Assigned date cannot be in the future."
                    )
            if row.get("Return Date"):
                date_errors = {}
                returned = import_valid_date(
                    row["Return Date"], "Return Date", date_errors, "Return Date Error"
                )
                errors.update(date_errors)
                if returned and assigned and returned < assigned:
                    errors["Return Date Error"] = (
                        "Return date cannot be before the assigned date."
                    )
            status = row.get("Return Status")
            if status and status not in STATUSES.values():
                errors["Return Status Error"] = (
                    "Use Minor damage, Major damage, Healthy or Lost."
                )
            if (status or row.get("Return Condition")) and not row.get("Return Date"):
                errors["Return Date Error"] = (
                    "A return status or condition needs a return date."
                )

            asset = None
            creates = False
            if not serial:
                errors["Serial No. Error"] = "Serial No. is required."
            else:
                asset = assets.get(serial)
                if asset is None:
                    if serial in planned:
                        pass  # made by an earlier row of this file
                    else:
                        creates = self._new_asset_problems(
                            row, serial, item_ids, errors
                        )
                # A returned allocation uses no unit; a live one needs a free unit.
                if not row.get("Return Date") and "Serial No. Error" not in errors:
                    left = (
                        free.get(asset.pk, 0)
                        if asset is not None
                        else planned.get(serial)
                    )
                    if left is None and creates:
                        left = _whole(row.get("Quantity"), "Quantity", {}, 1) or 1
                    if not left:
                        errors["Serial No. Error"] = (
                            "No unit of this asset is free to give out."
                        )

            if errors:
                result.errors.append(self._error_entry(row, errors, employee))
                continue

            if creates:
                planned[serial] = _whole(row.get("Quantity"), "Quantity", {}, 1) or 1
                row["__create_asset"] = True
            if not row.get("Return Date"):
                if asset is not None:
                    free[asset.pk] -= 1
                else:
                    planned[serial] -= 1
            row["__op"] = "create"
            row["__changes"] = ["New allocation"] if mode == "both" else []
            row["__employee"] = employee.pk
            row["__assigner"] = assigner.pk
            row["__date"] = assigned
            row["__return"] = returned
            result.valid.append(row)

        result.errors.sort(key=lambda e: e["row"])
        result.will_create = self._will_create(result.valid)
        if progress:
            progress(100)
        return result

    def _update_row(
        self, row, alloc, asset, employees, categories, lots, item_ids, errors
    ):
        """({"assignment", "asset", ...}, ["Label: old -> new"]) for what the sheet changes."""
        apply = {
            "assignment": {},
            "asset": {},
            "return": False,
            "category": None,
            "lot": None,
        }
        changes = []
        today = timezone.now().date()

        def note(label, old, new):
            changes.append(
                f"{label}: {old if old not in (None, '') else '-'} \u2192 {new}"
            )

        def date(label):
            parsed = None
            date_errors = {}
            parsed = import_valid_date(row[label], label, date_errors, f"{label} Error")
            errors.update(date_errors)
            return parsed

        errors.update(self._too_long(row))

        # ---- the allocation
        assigned = alloc.assigned_date
        if row.get("Assigned Date"):
            when = date("Assigned Date")
            if when and when > today:
                errors["Assigned Date Error"] = "Assigned date cannot be in the future."
            elif when and when != alloc.assigned_date:
                apply["assignment"]["assigned_date"] = when
                note("Assigned Date", alloc.assigned_date, when)
                assigned = when
        returning = False
        returned = alloc.return_date
        if row.get("Return Date"):
            when = date("Return Date")
            if when and when != alloc.return_date:
                apply["assignment"]["return_date"] = when
                note("Return Date", alloc.return_date, when)
                returning = alloc.return_date is None
                returned = when
        if returned and assigned and returned < assigned:
            errors["Return Date Error"] = (
                "Return date cannot be before the assigned date."
            )
        status = row.get("Return Status")
        if status and status not in STATUSES.values():
            errors["Return Status Error"] = (
                "Use Minor damage, Major damage, Healthy or Lost."
            )
        if (status or row.get("Return Condition")) and not returned:
            errors["Return Date Error"] = (
                "A return status or condition needs a return date."
            )
        if returned:
            status = status or ("Healthy" if returning else None)
            if status and status != alloc.return_status:
                apply["assignment"]["return_status"] = status
                note("Return Status", alloc.return_status, status)
            condition = row.get("Return Condition")
            if condition and condition != (alloc.return_condition or ""):
                apply["assignment"]["return_condition"] = condition
                note("Return Condition", alloc.return_condition, condition)
        apply["return"] = returning
        if row.get("Assigned By"):
            giver = employees.get(str(row["Assigned By"]).strip().lower())
            if giver is None:
                errors["Assigned By Error"] = "No employee has this Badge ID."
            elif giver.pk != alloc.assigned_by_employee_id_id:
                apply["assignment"]["assigned_by_employee_id"] = giver.pk
                note(
                    "Assigned By", alloc.assigned_by_employee_id, giver.get_full_name()
                )

        self._asset_changes(
            row, asset, categories, lots, item_ids, errors, apply, note, date, today
        )
        return apply, changes

    @staticmethod
    def _asset_changes(
        row, asset, categories, lots, item_ids, errors, apply, note, date, today
    ):
        """Fill ``apply`` with what the sheet changes on an existing asset."""

        def asset_field(label, field, new, old=None):
            current = getattr(asset, field) if old is None else old
            if str(current if current is not None else "") != str(new):
                apply["asset"][field] = new
                note(label, current, new)

        if row.get("Asset Name"):
            asset_field("Asset Name", "asset_name", row["Asset Name"])
        if row.get("Asset Description"):
            asset_field(
                "Asset Description", "asset_description", row["Asset Description"]
            )
        if row.get("Purchase Date"):
            when = date("Purchase Date")
            if when and when > today:
                errors["Purchase Date Error"] = "Purchase date cannot be in the future."
            elif when:
                asset_field("Purchase Date", "asset_purchase_date", when)
        if row.get("Purchase Cost"):
            try:
                cost = Decimal(str(row["Purchase Cost"]).strip())
                if (
                    cost < 0
                    or cost >= Decimal("100000000")
                    or cost.as_tuple().exponent < -2
                ):
                    raise InvalidOperation
                if cost != asset.asset_purchase_cost:
                    apply["asset"]["asset_purchase_cost"] = cost
                    note("Purchase Cost", asset.asset_purchase_cost, cost)
            except InvalidOperation:
                errors["Purchase Cost Error"] = (
                    "Purchase Cost must be a positive amount with at most 2 decimals."
                )
        if row.get("Warranty Expiry Date"):
            when = date("Warranty Expiry Date")
            if when:
                asset_field("Warranty Expiry Date", "expiry_date", when)
        notify = _whole(
            row.get("Notify Before (Days)"), "Notify Before (Days)", errors, 0
        )
        if notify is not None:
            asset_field("Notify Before (Days)", "notify_before", notify)
        quantity = _whole(row.get("Quantity"), "Quantity", errors, 1)
        if quantity is not None and quantity != asset.quantity:
            if quantity < asset.quantity:
                errors["Quantity Error"] = (
                    f"Quantity can only be raised, from {asset.quantity}."
                )
            else:
                base = asset.asset_tracking_id
                clashes = [
                    f"{base}-{i}" for i in range(asset.quantity + 1, quantity + 1)
                ]
                if any(c in item_ids for c in clashes):
                    errors["Serial No. Error"] = (
                        f"The extra units of {base} would clash with another asset's Serial No."
                    )
                apply["asset"]["quantity"] = quantity
                note("Quantity", asset.quantity, quantity)
        if (
            row.get("Category")
            and row["Category"] != asset.asset_category_id.asset_category_name
        ):
            apply["category"] = row["Category"]
            note(
                "Category", asset.asset_category_id.asset_category_name, row["Category"]
            )
            if row["Category"] not in categories:
                row["__new_category"] = row["Category"]
        if row.get("Batch Number"):
            current = (
                asset.asset_lot_number_id.lot_number
                if asset.asset_lot_number_id_id
                else ""
            )
            if row["Batch Number"] != current:
                apply["lot"] = row["Batch Number"]
                note("Batch Number", current, row["Batch Number"])
                if row["Batch Number"] not in lots:
                    row["__new_lot"] = row["Batch Number"]

    @staticmethod
    def _employee(badge, employees, ctx, errors):
        if not badge:
            errors["Badge ID Error"] = "Badge ID is required."
            return None
        employee = employees.get(str(badge).strip().lower())
        if employee is None:
            errors["Badge ID Error"] = "No employee has this Badge ID."
            return None
        if ctx.company is not None:
            info = getattr(employee, "employee_work_info", None)
            if getattr(info, "company_id_id", None) != ctx.company.pk:
                errors["Badge ID Error"] = (
                    f"This employee is not in {ctx.company.company}."
                )
                return None
        return employee

    @staticmethod
    def _too_long(row):
        found = {}
        for key, (model, name) in LIMITS.items():
            limit = model._meta.get_field(name).max_length
            value = row.get(key)
            if limit and value is not None and len(str(value)) > limit:
                found[f"{key} Error"] = (
                    f"{key} is {len(str(value))} characters; the most allowed is {limit}."
                )
        return found

    @staticmethod
    def _new_asset_problems(row, serial, item_ids, errors):
        """Check what an asset needs to be created; True when it can be."""
        problems = {}
        for key in ("Asset Name", "Category", "Purchase Date", "Purchase Cost"):
            if not row.get(key):
                problems[f"{key} Error"] = (
                    f"{key} is needed to create asset {serial}, which does not exist yet."
                )
        if row.get("Purchase Date") and "Purchase Date Error" not in problems:
            date_errors = {}
            when = import_valid_date(
                row["Purchase Date"],
                "Purchase Date",
                date_errors,
                "Purchase Date Error",
            )
            problems.update(date_errors)
            if when and when > timezone.now().date():
                problems["Purchase Date Error"] = (
                    "Purchase date cannot be in the future."
                )
        if row.get("Purchase Cost") and "Purchase Cost Error" not in problems:
            try:
                cost = Decimal(str(row["Purchase Cost"]).strip())
                if (
                    cost < 0
                    or cost >= Decimal("100000000")
                    or cost.as_tuple().exponent < -2
                ):
                    raise InvalidOperation
            except InvalidOperation:
                problems["Purchase Cost Error"] = (
                    "Purchase Cost must be a positive amount with at most 2 decimals."
                )
        quantity = _whole(row.get("Quantity"), "Quantity", problems, 1) or 1
        _whole(row.get("Notify Before (Days)"), "Notify Before (Days)", problems, 0)
        if row.get("Warranty Expiry Date"):
            date_errors = {}
            import_valid_date(
                row["Warranty Expiry Date"],
                "Warranty Expiry Date",
                date_errors,
                "Warranty Expiry Date Error",
            )
            problems.update(date_errors)
        base = serial
        clashes = [base if i == 1 else f"{base}-{i}" for i in range(1, quantity + 1)]
        if any(c in item_ids for c in clashes):
            problems["Serial No. Error"] = (
                f"Serial No. {serial} is already used by another asset's unit."
            )
        errors.update(problems)
        return not problems

    @staticmethod
    def _error_entry(row, errors, employee):
        keys = {f.key for f in AssetAllocationDataset.fields}
        by_field = {
            k[: -len(" Error")]: v
            for k, v in errors.items()
            if k[: -len(" Error")] in keys
        }
        return {
            "row": int(row.get("__row") or 0),
            "name": employee.get_full_name() if employee is not None else "-",
            "badge": row.get("Badge ID") or "-",
            "messages": list(errors.values()),
            "by_field": by_field,
            "data": {k: v for k, v in row.items() if k in keys},
        }

    @staticmethod
    def _will_create(valid):
        makers = [r for r in valid if r.get("__create_asset")]
        categories = set(
            AssetCategory.objects.entire().values_list("asset_category_name", flat=True)
        )
        lots = set(AssetLot.objects.entire().values_list("lot_number", flat=True))
        return {
            "categories": sorted(
                (
                    {r["Category"] for r in makers}
                    | {r["__new_category"] for r in valid if r.get("__new_category")}
                )
                - categories
            ),
            "batches": sorted(
                (
                    {r["Batch Number"] for r in makers if r.get("Batch Number")}
                    | {r["__new_lot"] for r in valid if r.get("__new_lot")}
                )
                - lots
            ),
            "assets": sorted(f"{r['Serial No.']} - {r['Asset Name']}" for r in makers),
        }

    # ------------------------------------------------------------- commit
    def commit(self, rows, ctx: Context, mode="create", progress=None) -> dict:
        today = timezone.now().date()
        made_assets = made_changes = made_allocations = 0
        counts = {"categories": 0, "batches": 0}
        total = len(rows) or 1
        with transaction.atomic():
            categories = {
                c.asset_category_name: c for c in AssetCategory.objects.entire()
            }
            lots = {l.lot_number: l for l in AssetLot.objects.entire()}
            assets = {a.asset_tracking_id: a for a in Asset.objects.entire()}
            wanted = {r["__employee"] for r in rows if r.get("__op") != "update"} | {
                r["__assigner"] for r in rows if r.get("__op") != "update"
            }
            employees = {
                e.pk: e for e in Employee.objects.entire().filter(pk__in=wanted)
            }
            for position, row in enumerate(rows, start=1):
                serial = row["Serial No."]
                if row.get("__op") == "update":
                    self._apply_update(row, ctx, categories, lots, counts)
                    made_changes += 1
                    if progress and (position % 10 == 0 or position == total):
                        progress(5 + int(position / total * 90))
                    continue
                if row.get("__create_asset") and serial not in assets:
                    assets[serial] = self._make_asset(
                        row, ctx, categories, lots, counts
                    )
                    made_assets += 1
                asset = assets[serial]
                self._allocate(asset, row, employees, today)
                made_allocations += 1
                if progress and (position % 10 == 0 or position == total):
                    progress(5 + int(position / total * 90))
        if progress:
            progress(100)
        return {
            "assigned": made_allocations,
            "updated": made_changes,
            "assets": made_assets,
            "categories": counts["categories"],
            "batches": counts["batches"],
        }

    @staticmethod
    def _make_asset(row, ctx, categories, lots, counts):
        """Create an asset from a row, with its category and batch if they are new."""
        category = categories.get(row["Category"])
        if category is None:
            category = AssetCategory.objects.create(
                asset_category_name=row["Category"],
                asset_category_description=row.get("Category Description") or "",
            )
            categories[row["Category"]] = category
            counts["categories"] += 1
        if ctx.company is not None and not category.company_id.exists():
            category.company_id.add(ctx.company)
        lot = None
        if row.get("Batch Number"):
            lot = lots.get(row["Batch Number"])
            if lot is None:
                lot = AssetLot.objects.create(
                    lot_number=row["Batch Number"],
                    lot_description=row.get("Batch Description"),
                )
                lots[row["Batch Number"]] = lot
                counts["batches"] += 1
        extra = {}
        if row.get("Warranty Expiry Date"):
            extra["expiry_date"] = import_valid_date(
                row["Warranty Expiry Date"], "", {}, ""
            )
        notify = _whole(row.get("Notify Before (Days)"), "", {}, 0)
        if notify is not None:
            extra["notify_before"] = notify
        asset = Asset(
            asset_name=row["Asset Name"],
            asset_description=row.get("Asset Description"),
            asset_tracking_id=row["Serial No."],
            asset_purchase_date=import_valid_date(row["Purchase Date"], "", {}, ""),
            asset_purchase_cost=Decimal(str(row["Purchase Cost"]).strip()),
            asset_category_id=category,
            asset_lot_number_id=lot,
            quantity=_whole(row.get("Quantity"), "", {}, 1) or 1,
            **extra,
        )
        asset.save()  # makes its units and settles its status
        return asset

    @staticmethod
    def _apply_asset(asset, apply, row, ctx, categories, lots, counts):
        """Write the changes found for an asset, making its new category or batch first."""
        if apply["category"]:
            category = categories.get(apply["category"])
            if category is None:
                category = AssetCategory.objects.create(
                    asset_category_name=apply["category"],
                    asset_category_description=row.get("Category Description") or "",
                )
                categories[apply["category"]] = category
                counts["categories"] += 1
            if ctx.company is not None and not category.company_id.exists():
                category.company_id.add(ctx.company)
            apply["asset"]["asset_category_id"] = category
        if apply["lot"]:
            lot = lots.get(apply["lot"])
            if lot is None:
                lot = AssetLot.objects.create(
                    lot_number=apply["lot"],
                    lot_description=row.get("Batch Description"),
                )
                lots[apply["lot"]] = lot
                counts["batches"] += 1
            apply["asset"]["asset_lot_number_id"] = lot
        if apply["asset"]:
            for field, value in apply["asset"].items():
                setattr(asset, field, value)
            asset.save()  # a higher quantity makes the extra units

    @staticmethod
    def _apply_update(row, ctx, categories, lots, counts):
        """Write one allocation's changes and its asset's."""
        alloc = (
            AssetAssignment.objects.entire()
            .select_related("asset_id", "asset_item_id")
            .get(pk=row["__pk"])
        )
        apply = row["__apply"]
        AssetAllocationDataset._apply_asset(
            alloc.asset_id, apply, row, ctx, categories, lots, counts
        )
        if apply["assignment"]:
            AssetAssignment.objects.entire().filter(pk=alloc.pk).update(
                **apply["assignment"]
            )
        if apply["return"] and alloc.asset_item_id_id:
            item = alloc.asset_item_id
            final = apply["assignment"].get("return_status") or alloc.return_status
            item.status = "Lost" if final == "Lost" else "Available"
            item.save()

    @staticmethod
    def _allocate(asset, row, employees, today):
        returned = row.get("__return")
        items = list(asset.asset_items.all())
        if returned:
            # Already given back: it holds no unit, so any unit will do as the record's.
            item = next(
                (i for i in items if i.status == "Available"),
                items[0] if items else None,
            )
        else:
            item = next(i for i in items if i.status == "Available")
        assignment = AssetAssignment.objects.create(
            asset_id=asset,
            asset_item_id=item,
            assigned_to_employee_id=employees[row["__employee"]],
            assigned_by_employee_id=employees[row["__assigner"]],
            return_date=returned,
            return_status=(row.get("Return Status") or "Healthy") if returned else None,
            return_condition=row.get("Return Condition") if returned else None,
        )
        if row.get("__date"):
            AssetAssignment.objects.entire().filter(pk=assignment.pk).update(
                assigned_date=row["__date"]
            )
        if item is not None:
            if not returned:
                item.status = "In use"
                item.save()
            elif row.get("Return Status") == "Lost":
                item.status = "Lost"
                item.save()
