from typing import Optional, Type
from collections import defaultdict
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response

from base.backends import ConfiguredEmailBackend
from base.methods import eval_validate
from payroll.filters import AllowanceFilter, ContractFilter, DeductionFilter, PayslipFilter
from payroll.models.models import (
    Allowance, Contract, Deduction, LoanAccount, 
    Payslip, Reimbursement
)
from payroll.models.tax_models import TaxBracket
from payroll.threadings.mail import MailSendThread
from payroll.views.views import payslip_pdf
from ...api_methods.base.methods import groupby_queryset
from ...api_serializers.payroll.serializers import (
    AllowanceSerializer, ContractSerializer, DeductionSerializer,
    LoanAccountSerializer, PayslipSerializer, ReimbursementSerializer,
    TaxBracketSerializer
)

class BasePayrollViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet providing common functionality for all payroll-related views.
    Includes permission handling, pagination, and standard CRUD operations.
    """
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    pagination_class = PageNumberPagination

    def get_object_or_404(self, pk: int):
        try:
            return self.queryset.get(pk=pk)
        except self.queryset.model.DoesNotExist as e:
            raise ValidationError(str(e))

    def handle_groupby(self, request, queryset):
        field_name = request.GET.get("groupby_field")
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, queryset)
        return None

class PayslipViewSet(BasePayrollViewSet):
    """
    ViewSet for managing payslips with specialized handling for employee access
    and email functionality.
    """
    serializer_class = PayslipSerializer
    filterset_class = PayslipFilter

    def get_queryset(self):
        if self.request.user.has_perm("payroll.view_payslip"):
            return Payslip.objects.all()
        return Payslip.objects.filter(employee_id=self.request.user.employee_get)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Handle groupby if requested
        groupby_response = self.handle_groupby(request, queryset)
        if groupby_response:
            return groupby_response

        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        payslip = self.get_object()
        if not (request.user.has_perm("payroll.view_payslip") or 
                payslip.employee_id == request.user.employee_get):
            raise PermissionDenied("You don't have permission to access this payslip")
        return payslip_pdf(request, pk)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    @method_decorator(permission_required("payroll.add_payslip"))
    def send_mail(self, request):
        email_backend = ConfiguredEmailBackend()
        if not getattr(email_backend, "dynamic_username_with_display_name", None):
            raise ValidationError("Email server is not configured")

        payslip_ids = request.data.get("id", [])
        payslips = self.get_queryset().filter(id__in=payslip_ids)
        
        # Group payslips by employee for efficient processing
        result_dict = defaultdict(lambda: {"employee_id": None, "instances": [], "count": 0})
        for payslip in payslips:
            emp_dict = result_dict[payslip.employee_id]
            emp_dict["employee_id"] = payslip.employee_id
            emp_dict["instances"].append(payslip)
            emp_dict["count"] += 1

        # Start email thread
        MailSendThread(request, result_dict=result_dict, ids=payslip_ids).start()
        return Response({"status": "Email sending initiated"}, status=status.HTTP_200_OK)

class ReimbursementViewSet(BasePayrollViewSet):
    """
    ViewSet for handling reimbursement requests with approval/rejection functionality.
    """
    serializer_class = ReimbursementSerializer

    def get_queryset(self):
        if self.request.user.has_perm("payroll.view_reimbursement"):
            return Reimbursement.objects.all()
        return Reimbursement.objects.filter(employee_id=self.request.user.employee_get)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def process_request(self, request, pk=None):
        """Handle approval/rejection of reimbursement requests"""
        reimbursement = self.get_object()
        status_value = request.data.get("status")
        amount = eval_validate(request.data.get("amount", "0"))
        
        if amount is not None:
            amount = max(0, float(amount))
            reimbursement.amount = amount
        
        reimbursement.status = status_value
        reimbursement.save()
        
        return Response(
            {"status": reimbursement.status},
            status=status.HTTP_200_OK
        )

class ContractViewSet(BasePayrollViewSet):
    """ViewSet for managing employment contracts."""
    serializer_class = ContractSerializer
    queryset = Contract.objects.all()
    filterset_class = ContractFilter

    def get_queryset(self):
        if self.request.user.has_perm("payroll.view_contract"):
            return Contract.objects.all()
        return Contract.objects.filter(employee_id=self.request.user.employee_get)

class AllowanceViewSet(BasePayrollViewSet):
    """ViewSet for managing employee allowances."""
    serializer_class = AllowanceSerializer
    queryset = Allowance.objects.all()
    filterset_class = AllowanceFilter

class DeductionViewSet(BasePayrollViewSet):
   
    serializer_class = DeductionSerializer
    queryset = Deduction.objects.all()
    filterset_class = DeductionFilter

class LoanAccountViewSet(BasePayrollViewSet):
    """ViewSet for managing employee loan accounts."""
    serializer_class = LoanAccountSerializer
    queryset = LoanAccount.objects.all()

class TaxBracketViewSet(BasePayrollViewSet):
    """ViewSet for managing tax brackets."""
    serializer_class = TaxBracketSerializer
    queryset = TaxBracket.objects.all()