# Generated migration for Royal Falcon Security Leave Policy - Phase 1 Foundation

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("leave", "0007_alter_historicalleaverequest_reject_reason_and_more"),
        ("employee", "0001_initial"),  # Adjust based on actual employee migrations
        ("base", "0001_initial"),  # Adjust based on actual base migrations
    ]

    operations = [
        # Add fields to AvailableLeave for accrual tracking
        migrations.AddField(
            model_name="availableleave",
            name="last_accrual_date",
            field=models.DateField(
                blank=True,
                null=True,
                editable=False,
                verbose_name="Last Accrual Date",
                help_text="Track last date 2.5 days were credited to prevent duplicate accrual",
            ),
        ),
        migrations.AddField(
            model_name="availableleave",
            name="accrual_paused_until",
            field=models.DateField(
                blank=True,
                null=True,
                editable=False,
                verbose_name="Accrual Paused Until",
                help_text="If set, accrual is paused until this date (e.g., during unpaid leave)",
            ),
        ),
        # Create EmployeeCategory model
        migrations.CreateModel(
            name="EmployeeCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        null=True,
                        verbose_name="Created At",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        null=True,
                        verbose_name="Updated At",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="e.g., Management, Normal Employee",
                        max_length=100,
                        verbose_name="Category Name",
                    ),
                ),
                (
                    "badge_id_prefix",
                    models.CharField(
                        help_text="e.g., A-, S-, SD-, D-, P-",
                        max_length=10,
                        unique=True,
                        verbose_name="Badge ID Prefix",
                    ),
                ),
                (
                    "max_carryforward_days",
                    models.IntegerField(
                        default=30,
                        help_text="Maximum leave days allowed to carryforward after December 31 reset",
                        verbose_name="Max Carryforward Days",
                    ),
                ),
                (
                    "company_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="base.company",
                        verbose_name="Company",
                    ),
                ),
            ],
            options={
                "verbose_name": "Employee Category",
                "verbose_name_plural": "Employee Categories",
                "unique_together": {("badge_id_prefix", "company_id")},
            },
        ),
        # Create LeaveAccrualConfiguration model
        migrations.CreateModel(
            name="LeaveAccrualConfiguration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        null=True,
                        verbose_name="Created At",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        null=True,
                        verbose_name="Updated At",
                    ),
                ),
                (
                    "monthly_accrual_days",
                    models.DecimalField(
                        decimal_places=2,
                        default=2.5,
                        help_text="Days of leave credited each month to employees",
                        max_digits=5,
                        verbose_name="Monthly Accrual Days",
                    ),
                ),
                (
                    "annual_reset_month",
                    models.IntegerField(
                        default=12,
                        help_text="Month when carryforward limits are reset (1-12)",
                        verbose_name="Annual Reset Month",
                    ),
                ),
                (
                    "annual_reset_day",
                    models.IntegerField(
                        default=31,
                        help_text="Day of month when carryforward limits are reset",
                        verbose_name="Annual Reset Day",
                    ),
                ),
                (
                    "active",
                    models.BooleanField(
                        default=True,
                        help_text="Enable/disable accrual for this company",
                        verbose_name="Active",
                    ),
                ),
                (
                    "company_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="base.company",
                        verbose_name="Company",
                    ),
                ),
            ],
            options={
                "verbose_name": "Leave Accrual Configuration",
                "verbose_name_plural": "Leave Accrual Configurations",
                "unique_together": {("company_id",)},
            },
        ),
        # Create UnpaidLeave model
        migrations.CreateModel(
            name="UnpaidLeave",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        null=True,
                        verbose_name="Created At",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        null=True,
                        verbose_name="Updated At",
                    ),
                ),
                ("start_date", models.DateField(verbose_name="Start Date")),
                ("end_date", models.DateField(verbose_name="End Date")),
                (
                    "reason",
                    models.TextField(
                        help_text="Reason for unpaid leave",
                        verbose_name="Reason",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("returned", "Returned"),
                            ("rejected", "Rejected"),
                        ],
                        default="active",
                        help_text="Current status of unpaid leave",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        help_text="HR or SuperAdmin who created this record",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="unpaid_leave_created",
                        to="employee.employee",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "employee_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="employee.employee",
                        verbose_name="Employee",
                    ),
                ),
            ],
            options={
                "verbose_name": "Unpaid Leave",
                "verbose_name_plural": "Unpaid Leaves",
                "ordering": ["-start_date"],
            },
        ),
        # Create UnauthorizedExtension model
        migrations.CreateModel(
            name="UnauthorizedExtension",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        null=True,
                        verbose_name="Created At",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        null=True,
                        verbose_name="Updated At",
                    ),
                ),
                (
                    "approved_return_date",
                    models.DateField(
                        help_text="When employee was supposed to return",
                        verbose_name="Approved Return Date",
                    ),
                ),
                (
                    "actual_return_date",
                    models.DateField(
                        blank=True,
                        help_text="When employee actually returned",
                        null=True,
                        verbose_name="Actual Return Date",
                    ),
                ),
                (
                    "unauthorized_days",
                    models.FloatField(
                        default=0,
                        editable=False,
                        help_text="Auto-calculated: actual_return_date - approved_return_date",
                        verbose_name="Unauthorized Days",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending_review", "Pending Review"),
                            ("approved", "Approved"),
                            ("converted_to_paid", "Converted to Paid"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending_review",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "remarks",
                    models.TextField(
                        blank=True,
                        help_text="HR notes and decision details",
                        verbose_name="Remarks",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="unauthorized_ext_created",
                        to="employee.employee",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "employee_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="employee.employee",
                        verbose_name="Employee",
                    ),
                ),
                (
                    "leave_request_id",
                    models.ForeignKey(
                        blank=True,
                        help_text="The approved paid leave request that was extended",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="leave.leaverequest",
                        verbose_name="Related Leave Request",
                    ),
                ),
            ],
            options={
                "verbose_name": "Unauthorized Extension",
                "verbose_name_plural": "Unauthorized Extensions",
                "ordering": ["-created_at"],
            },
        ),
        # Create LeaveAccrualAuditLog model
        migrations.CreateModel(
            name="LeaveAccrualAuditLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "accrual_type",
                    models.CharField(
                        choices=[
                            ("monthly_accrual", "Monthly Accrual"),
                            ("annual_reset", "Annual Reset"),
                            ("accrual_pause_start", "Accrual Pause Start"),
                            ("accrual_pause_end", "Accrual Pause End"),
                            ("manual_adjustment", "Manual Adjustment"),
                        ],
                        max_length=50,
                        verbose_name="Accrual Type",
                    ),
                ),
                (
                    "old_balance",
                    models.FloatField(
                        help_text="Leave balance before change",
                        verbose_name="Old Balance",
                    ),
                ),
                (
                    "new_balance",
                    models.FloatField(
                        help_text="Leave balance after change",
                        verbose_name="New Balance",
                    ),
                ),
                (
                    "accrual_days",
                    models.FloatField(
                        help_text="Days added (positive) or removed (negative)",
                        verbose_name="Accrual Days",
                    ),
                ),
                (
                    "reason",
                    models.TextField(
                        help_text="Why this accrual change was made",
                        verbose_name="Reason",
                    ),
                ),
                (
                    "effective_date",
                    models.DateField(
                        help_text="Date when this accrual took effect",
                        verbose_name="Effective Date",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Created At",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="Who triggered this accrual (system or HR)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="accrual_log_created",
                        to="employee.employee",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "employee_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="employee.employee",
                        verbose_name="Employee",
                    ),
                ),
                (
                    "related_leave_type_id",
                    models.ForeignKey(
                        blank=True,
                        help_text="Leave type affected by this accrual",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="leave.leavetype",
                        verbose_name="Leave Type",
                    ),
                ),
            ],
            options={
                "verbose_name": "Leave Accrual Audit Log",
                "verbose_name_plural": "Leave Accrual Audit Logs",
                "ordering": ["-effective_date", "-created_at"],
                "indexes": [
                    models.Index(
                        fields=["employee_id", "-effective_date"],
                        name="leave_leaveaccrualaudit_employee_effective_idx",
                    ),
                    models.Index(
                        fields=["accrual_type", "-effective_date"],
                        name="leave_leaveaccrualaudit_accrual_type_effective_idx",
                    ),
                ],
            },
        ),
        # Create EmployeeServiceAdjustment model
        migrations.CreateModel(
            name="EmployeeServiceAdjustment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "adjustment_type",
                    models.CharField(
                        choices=[
                            ("unpaid_leave_pause", "Unpaid Leave Pause"),
                            ("unauthorized_extension", "Unauthorized Extension"),
                        ],
                        max_length=50,
                        verbose_name="Adjustment Type",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(
                        help_text="When service pause started",
                        verbose_name="Start Date",
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        help_text="When service pause ended",
                        verbose_name="End Date",
                    ),
                ),
                (
                    "days_excluded",
                    models.FloatField(
                        default=0,
                        editable=False,
                        help_text="Auto-calculated number of days excluded from service",
                        verbose_name="Days Excluded",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Additional context for this service adjustment",
                        verbose_name="Notes",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Created At",
                    ),
                ),
                (
                    "employee_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="employee.employee",
                        verbose_name="Employee",
                    ),
                ),
                (
                    "related_unpaid_leave_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="service_adjustments",
                        to="leave.unpaidleave",
                        verbose_name="Related Unpaid Leave",
                    ),
                ),
                (
                    "related_unauthorized_extension_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="service_adjustments",
                        to="leave.unauthorizedextension",
                        verbose_name="Related Unauthorized Extension",
                    ),
                ),
            ],
            options={
                "verbose_name": "Employee Service Adjustment",
                "verbose_name_plural": "Employee Service Adjustments",
                "ordering": ["-start_date"],
            },
        ),
    ]
