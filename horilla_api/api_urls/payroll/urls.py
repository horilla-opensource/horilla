from django.urls import path, include
from rest_framework.routers import DefaultRouter

from ...api_views.payroll.views import (
    PayslipViewSet,
    ContractViewSet,
    LoanAccountViewSet,
    ReimbursementViewSet,
    TaxBracketViewSet,
    AllowanceViewSet,
    DeductionViewSet,
)

# Create a router for ViewSet-based URLs
router = DefaultRouter()
router.register(r'api/contract', ContractViewSet, basename='contract')
router.register(r'api/payslip', PayslipViewSet, basename='payslip')
router.register(r'api/loan-account', LoanAccountViewSet, basename='loan-account')
router.register(r'api/reimbursement', ReimbursementViewSet, basename='reimbursement')
router.register(r'api/tax-bracket', TaxBracketViewSet, basename='tax-bracket')
router.register(r'api/allowance', AllowanceViewSet, basename='allowance')
router.register(r'api/deduction', DeductionViewSet, basename='deduction')

# Define URL patterns, maintaining backward compatibility
urlpatterns = [
    # Include router-generated URLs
    path('', include(router.urls)),

    # Legacy URL patterns for backward compatibility
    path(
        "contract/",
        ContractViewSet.as_view({'get': 'list', 'post': 'create'}),
        name="legacy-contract-list"
    ),
    path(
        "contract/<int:id>",
        ContractViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'delete': 'destroy'
        }),
        name="legacy-contract-detail"
    ),
    path(
        "payslip/",
        PayslipViewSet.as_view({'get': 'list', 'post': 'create'}),
        name="legacy-payslip-list"
    ),
    path(
        "payslip/<int:id>",
        PayslipViewSet.as_view({'get': 'retrieve'}),
        name="legacy-payslip-detail"
    ),
    path(
        "payslip-download/<int:id>",
        PayslipViewSet.as_view({'get': 'download'}),
        name="legacy-payslip-download"
    ),
    path(
        "payslip-send-mail/",
        PayslipViewSet.as_view({'post': 'send_mail'}),
        name="legacy-payslip-send-mail"
    ),
    path(
        "reimbursement/",
        ReimbursementViewSet.as_view({'get': 'list', 'post': 'create'}),
        name="legacy-reimbursement-list"
    ),
    path(
        "reimbursement/<int:pk>",
        ReimbursementViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'delete': 'destroy'
        }),
        name="legacy-reimbursement-detail"
    ),
    path(
        "reimbursement-approve-reject/<int:pk>",
        ReimbursementViewSet.as_view({'post': 'process_request'}),
        name="legacy-reimbursement-approve-reject"
    ),
]