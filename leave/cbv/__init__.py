# Import all CBV views for easier access
from leave.cbv.unpaid_leave import (
    UnpaidLeaveListView,
    UnpaidLeaveDetailView,
    UnpaidLeaveCreateView,
    UnpaidLeaveUpdateView,
    UnpaidLeaveDeleteView,
)
from leave.cbv.unauthorized_extension import (
    UnauthorizedExtensionListView,
    UnauthorizedExtensionDetailView,
    UnauthorizedExtensionCreateView,
    UnauthorizedExtensionUpdateView,
    UnauthorizedExtensionDeleteView,
)
from leave.cbv.employee_category import (
    EmployeeCategoryListView,
    EmployeeCategoryDetailView,
    EmployeeCategoryCreateView,
    EmployeeCategoryUpdateView,
    EmployeeCategoryDeleteView,
)
from leave.cbv.accrual_audit_logs import (
    LeaveAccrualAuditLogListView,
    LeaveAccrualAuditLogDetailView,
    LeaveAccrualAuditLogHRView,
)

__all__ = [
    # Unpaid Leave views
    "UnpaidLeaveListView",
    "UnpaidLeaveDetailView",
    "UnpaidLeaveCreateView",
    "UnpaidLeaveUpdateView",
    "UnpaidLeaveDeleteView",
    # Unauthorized Extension views
    "UnauthorizedExtensionListView",
    "UnauthorizedExtensionDetailView",
    "UnauthorizedExtensionCreateView",
    "UnauthorizedExtensionUpdateView",
    "UnauthorizedExtensionDeleteView",
    # Employee Category views
    "EmployeeCategoryListView",
    "EmployeeCategoryDetailView",
    "EmployeeCategoryCreateView",
    "EmployeeCategoryUpdateView",
    "EmployeeCategoryDeleteView",
    # Audit Log views
    "LeaveAccrualAuditLogListView",
    "LeaveAccrualAuditLogDetailView",
    "LeaveAccrualAuditLogHRView",
]