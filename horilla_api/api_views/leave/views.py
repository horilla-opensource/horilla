import contextlib

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import AnonymousUser
from django.db.models import Count
from django.http import Http404, QueryDict
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from base.methods import filtersubordinates
from horilla_api.api_serializers.leave.serializers import *
from leave.filters import *
from leave.methods import filter_conditional_leave_request
from leave.models import LeaveRequest
from notifications.signals import notify

from ...api_decorators.base.decorators import manager_permission_required
from ...api_methods.base.methods import groupby_queryset


class EmployeeAvailableLeaveGetAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = request.user.employee_get
        available_leave = employee.available_leave.all()
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(available_leave, request)
        serializer = GetAvailableLeaveTypeSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class EmployeeLeaveRequestGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserLeaveRequestFilter

    def get(self, request):
        employee = request.user.employee_get
        leave_request = employee.leaverequest_set.all().order_by("-id")
        filterset = self.filterset_class(request.GET, queryset=leave_request)
        paginator = PageNumberPagination()
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = userLeaveRequestGetAllSerilaizer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        employee_id = request.user.employee_get.id
        data = request.data
        if isinstance(data, QueryDict):
            data = data.dict()
        data["employee_id"] = employee_id
        data["end_date"] = (
            data.get("start_date") if not data.get("end_date") else data.get("end_date")
        )
        serializer = LeaveRequestCreateUpdateSerializer(data=data)
        if serializer.is_valid():
            leave_request = serializer.save()
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                    verb="You have a new leave request to validate.",
                    verb_ar="لديك طلب إجازة جديد يجب التحقق منه.",
                    verb_de="Sie haben eine neue Urlaubsanfrage zur Validierung.",
                    verb_es="Tiene una nueva solicitud de permiso que debe validar.",
                    verb_fr="Vous avez une nouvelle demande de congé à valider.",
                    icon="people-circle",
                    redirect=f"/leave/request-view?id={leave_request.id}",
                    api_redirect=f"/api/leave/request/{leave_request.id}/",
                )
            return Response(
                userLeaveRequestGetAllSerilaizer(leave_request).data, status=201
            )
        return Response(serializer.errors, status=400)


class EmployeeLeaveRequestUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_request(self, request, pk):
        try:
            return LeaveRequest.objects.get(
                pk=pk, employee_id=request.user.employee_get
            )
        except LeaveRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def get(self, request, pk):
        leave_request = self.get_leave_request(request, pk)
        serializer = UserLeaveRequestGetSerilaizer(leave_request)
        return Response(serializer.data, status=200)

    def put(self, request, pk):
        leave_request = self.get_leave_request(request, pk)
        employee_id = request.user.employee_get
        if (
            leave_request.status == "requested"
            and leave_request.employee_id == employee_id
        ):
            data = request.data
            if isinstance(data, QueryDict):
                data = data.dict()
            data["employee_id"] = employee_id.id
            data["end_date"] = (
                data.get("start_date")
                if not data.get("end_date")
                else data.get("end_date")
            )
            serializer = LeaveRequestCreateUpdateSerializer(leave_request, data=data)
            if serializer.is_valid():
                leave_request = serializer.save()
                return Response(
                    UserLeaveRequestGetSerilaizer(leave_request).data, status=201
                )
            return Response(serializer.errors, status=400)
        raise serializers.ValidationError({"error": "Access Denied.."})

    def delete(self, request, pk):
        leave_request = self.get_leave_request(request, pk)
        employee_id = request.user.employee_get
        if (
            leave_request.status == "requested"
            and leave_request.employee_id == employee_id
        ):
            leave_request.delete()
            return Response(
                {"message": "Leave request deleted successfully.."}, status=200
            )
        raise serializers.ValidationError({"error": "Access Denied.."})


class LeaveTypeGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LeaveTypeFilter

    # @method_decorator(permission_required('leave.view_leavetype', raise_exception=True), name='dispatch')
    def get(self, request):
        leave_type = LeaveType.objects.all()
        filterset = self.filterset_class(request.GET, queryset=leave_type)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = LeaveTypeAllGetSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @method_decorator(
        permission_required("leave.add_leavetype", raise_exception=True),
        name="dispatch",
    )
    def post(self, request):
        serializer = LeaveTypeGetCreateSerilaizer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class LeaveTypeGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_type(self, pk):
        try:
            return LeaveType.objects.get(pk=pk)
        except LeaveType.DoesNotExist as e:
            raise serializers.ValidationError(e)

    @method_decorator(
        permission_required("leave.view_leavetype", raise_exception=True),
        name="dispatch",
    )
    def get(self, request, pk):
        leave_type = self.get_leave_type(pk)
        serializer = LeaveTypeGetCreateSerilaizer(leave_type)
        return Response(serializer.data, status=200)

    @method_decorator(
        permission_required("leave.change_leavetype", raise_exception=True),
        name="dispatch",
    )
    def put(self, request, pk):
        leave_type = self.get_leave_type(pk)
        serializer = LeaveTypeGetCreateSerilaizer(leave_type, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @method_decorator(
        permission_required("leave.delete_leavetype", raise_exception=True),
        name="dispatch",
    )
    def delete(self, request, pk):
        leave_type = self.get_leave_type(pk)
        leave_type.delete()
        return Response(status=201)


class LeaveAllocationRequestGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LeaveAllocationRequestFilter

    def get_user(self, request):
        user = request.user
        if isinstance(user, AnonymousUser):
            raise Http404("AnonymousUser")
        return user

    @manager_permission_required("leave.view_leaveallocationrequest")
    def get(self, request):
        allocation_requests = LeaveAllocationRequest.objects.all().order_by("-id")
        queryset = filtersubordinates(
            request, allocation_requests, "leave.view_leaveallocationrequest"
        )
        filterset = self.filterset_class(request.GET, queryset=queryset)
        paginator = PageNumberPagination()
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = LeaveAllocationRequestGetSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        data = request.data
        employee_id = self.get_user(request).employee_get.id
        if isinstance(data, QueryDict):
            data = data.dict()
        data["created_by"] = employee_id
        serializer = LeaveAllocationRequestCreateSerializer(data=data)
        if serializer.is_valid():
            allocation_request = serializer.save()
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=allocation_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                    verb=f"New leave allocation request created for {allocation_request.employee_id}.",
                    verb_ar=f"تم إنشاء طلب تخصيص إجازة جديد لـ {allocation_request.employee_id}.",
                    verb_de=f"Neue Anfrage zur Urlaubszuweisung erstellt für {allocation_request.employee_id}.",
                    verb_es=f"Nueva solicitud de asignación de permisos creada para {allocation_request.employee_id}.",
                    verb_fr=f"Nouvelle demande d'allocation de congé créée pour {allocation_request.employee_id}.",
                    icon="people-cicle",
                    redirect=f"/leave/leave-allocation-request-view?id={allocation_request.id}",
                    api_redirect=f"/api/leave/allocation-request/{allocation_request.id}/",
                )
            return Response(
                LeaveAllocationRequestGetSerializer(allocation_request).data, status=201
            )
        return Response(serializer.errors, status=400)


class LeaveAllocationRequestGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_allocation_request(self, pk):
        try:
            return LeaveAllocationRequest.objects.get(pk=pk)
        except LeaveAllocationRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    @manager_permission_required("leave.view_leaveallocationrequest")
    def get(self, request, pk):
        allocation_request = self.get_leave_allocation_request(pk)
        serializer = LeaveAllocationRequestGetSerializer(allocation_request)
        return Response(serializer.data, status=200)

    @manager_permission_required("leave.change_leaveallocationrequest")
    def put(self, request, pk):
        allocation_request = self.get_leave_allocation_request(pk)
        if allocation_request.status == "requested":
            serializer = LeaveAllocationRequestSerilaizer(
                allocation_request, data=request.data
            )
            if serializer.is_valid():
                allocation_request = serializer.save()
                return Response(
                    LeaveAllocationRequestGetSerializer(allocation_request).data,
                    status=201,
                )
            return Response(serializer.errors, status=400)
        raise serializers.ValidationError({"error": "Access Denied.."})

    @manager_permission_required("leave.delete_leaveallocationrequest")
    def delete(self, request, pk):
        allocation_request = self.get_leave_allocation_request(pk)
        if allocation_request.status == "requested":
            allocation_request.delete()
            return Response(status=200)
        raise serializers.ValidationError({"error": "Access Denied.."})


class AssignLeaveGetCreateAPIView(APIView):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AssignedLeaveFilter

    @method_decorator(
        permission_required("leave.view_availableleave", raise_exception=True),
        name="dispatch",
    )
    def get(self, request):
        available_leave = AvailableLeave.objects.all().order_by("-id")
        queryset = filtersubordinates(
            request, available_leave, "leave.view_availableleave"
        )
        filterset = self.filterset_class(request.GET, queryset=queryset)
        paginator = PageNumberPagination()
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = AssignLeaveGetSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @method_decorator(
        permission_required("leave.add_availableleave", raise_exception=True),
        name="dispatch",
    )
    def post(self, request):
        serializer = AssignLeaveCreateSerializer(data=request.data)
        if serializer.is_valid():
            employee_ids = serializer.validated_data.get("employee_ids")
            leave_type_ids = serializer.validated_data.get("leave_type_ids")
            for employee_id in employee_ids:
                for leave_type_id in leave_type_ids:
                    if not AvailableLeave.objects.filter(
                        employee_id=employee_id, leave_type_id=leave_type_id
                    ).exists():
                        AvailableLeave.objects.create(
                            employee_id=employee_id,
                            leave_type_id=leave_type_id,
                            available_days=leave_type_id.total_days,
                        )
                        with contextlib.suppress(Exception):
                            notify.send(
                                request.user.employee_get,
                                recipient=employee_id.employee_user_id,
                                verb="New leave type is assigned to you",
                                verb_ar="تم تعيين نوع إجازة جديد لك",
                                verb_de="Dir wurde ein neuer Urlaubstyp zugewiesen",
                                verb_es="Se te ha asignado un nuevo tipo de permiso",
                                verb_fr="Un nouveau type de congé vous a été attribué",
                                icon="people-circle",
                                redirect="/leave/user-request-view",
                                api_redirect="/api/leave/user-request/",
                            )
            return Response(status=201)
        return Response(serializer.errors, status=400)


class AssignLeaveGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_available_leave(self, pk):
        try:
            return AvailableLeave.objects.get(pk=pk)
        except AvailableLeave.DoesNotExist as e:
            raise serializers.ValidationError(e)

    @method_decorator(
        permission_required("leave.view_availableleave", raise_exception=True),
        name="dispatch",
    )
    def get(self, request, pk):
        available_leave = self.get_available_leave(pk)
        serializer = AssignLeaveGetSerializer(available_leave)
        return Response(serializer.data, status=200)

    @method_decorator(
        permission_required("leave.change_availableleave", raise_exception=True),
        name="dispatch",
    )
    def put(self, request, pk):
        available_leave = self.get_available_leave(pk)
        serializer = AvailableLeaveUpdateSerializer(available_leave, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(status=201)
        return Response(serializer.errors, status=400)

    @method_decorator(
        permission_required("leave.delete_availableleave", raise_exception=True),
        name="dispatch",
    )
    def delete(self, request, pk):
        available_leave = self.get_available_leave(pk)
        available_leave.delete()
        return Response(status=200)


class LeaveRequestGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LeaveRequestFilter

    @manager_permission_required("leave.view_leaverequest")
    def get(self, request):
        leave_request = LeaveRequest.objects.all().order_by("-id")
        multiple_approvals = filter_conditional_leave_request(request)
        queryset = (
            filtersubordinates(request, leave_request, "leave.view_leaverequest")
            | multiple_approvals
        )
        filterset = self.filterset_class(request.GET, queryset=queryset)
        paginator = PageNumberPagination()
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = LeaveRequestGetAllSerilaizer(
            page, context={"request": request}, many=True
        )
        return paginator.get_paginated_response(serializer.data)

    @manager_permission_required("leave.add_leaverequest")
    def post(self, request):
        data = request.data
        if isinstance(data, QueryDict):
            data = data.dict()
        data["end_date"] = (
            data.get("start_date") if not data.get("end_date") else data.get("end_date")
        )
        serializer = LeaveRequestCreateUpdateSerializer(data=data)
        if serializer.is_valid():
            leave_request = serializer.save()
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                    verb=f"New leave request created for {leave_request.employee_id}.",
                    verb_ar=f"تم إنشاء طلب إجازة جديد لـ {leave_request.employee_id}.",
                    verb_de=f"Neuer Urlaubsantrag erstellt für {leave_request.employee_id}.",
                    verb_es=f"Nueva solicitud de permiso creada para {leave_request.employee_id}.",
                    verb_fr=f"Nouvelle demande de congé créée pour {leave_request.employee_id}.",
                    icon="people-circle",
                    redirect=f"/leave/request-view?id={leave_request.id}",
                    api_redirect=f"/api/leave/request/{leave_request.id}/",
                )
            return Response(
                LeaveRequestGetSerilaizer(
                    leave_request, context={"request": request}
                ).data,
                status=201,
            )
        return Response(serializer.errors, status=400)


class LeaveRequestGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_request(self, pk):
        try:
            return LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    @manager_permission_required("leave.view_leaverequest")
    def get(self, request, pk):
        leave_request = self.get_leave_request(pk)
        serializer = LeaveRequestGetSerilaizer(
            leave_request, context={"request": request}
        )
        return Response(serializer.data, status=200)

    @manager_permission_required("leave.change_leaverequest")
    def put(self, request, pk):
        leave_request = self.get_leave_request(pk)
        if leave_request.status == "requested":
            data = request.data
            if isinstance(data, QueryDict):
                data = data.dict()
            data["end_date"] = (
                data.get("start_date")
                if not data.get("end_date")
                else data.get("end_date")
            )
            serializer = LeaveRequestCreateUpdateSerializer(leave_request, data=data)
            if serializer.is_valid():
                leave_request = serializer.save()
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        verb=f"Leave request updated for {leave_request.employee_id}.",
                        verb_ar=f"تم تحديث طلب الإجازة لـ {leave_request.employee_id}.",
                        verb_de=f"Urlaubsantrag aktualisiert für {leave_request.employee_id}.",
                        verb_es=f"Solicitud de permiso actualizada para {leave_request.employee_id}.",
                        verb_fr=f"Demande de congé mise à jour pour {leave_request.employee_id}.",
                        icon="people-circle",
                        redirect=f"/leave/request-view?id={leave_request.id}",
                        api_redirect=f"/api/leave/request/{leave_request.id}/",
                    )
                return Response(
                    UserLeaveRequestGetSerilaizer(
                        leave_request, context={"request": request}
                    ).data,
                    status=201,
                )
            return Response(serializer.errors, status=400)
        raise serializers.ValidationError({"error": "Access Denied.."})

    @manager_permission_required("leave.delete_leaverequest")
    def delete(self, request, pk):
        leave_request = self.get_leave_request(pk)
        if leave_request.status == "requested":
            leave_request.delete()
            return Response(status=200)
        raise serializers.ValidationError({"error": "Access Denied.."})


class CompanyLeaveGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(
        permission_required("leave.view_companyleave", raise_exception=True),
        name="dispatch",
    )
    def get(self, request):
        company_leave = CompanyLeave.objects.all().order_by("-id")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(company_leave, request)
        serializer = CompanyLeaveSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @method_decorator(
        permission_required("leave.add_companyleave", raise_exception=True),
        name="dispatch",
    )
    def post(self, request):
        serializer = CompanyLeaveSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class CompanyLeaveGetUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_company_leave(self, pk):
        try:
            return CompanyLeave.objects.get(pk=pk)
        except CompanyLeave.DoesNotExist as e:
            raise serializers.ValidationError(e)

    @method_decorator(
        permission_required("leave.view_companyleave", raise_exception=True),
        name="dispatch",
    )
    def get(self, request, pk):
        company_leave = self.get_company_leave(pk)
        serializer = CompanyLeaveSerializer(company_leave)
        return Response(serializer.data, status=200)

    @method_decorator(
        permission_required("leave.change_companyleave", raise_exception=True),
        name="dispatch",
    )
    def put(self, request, pk):
        company_leave = self.get_company_leave(pk)
        serializer = CompanyLeaveSerializer(company_leave, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @method_decorator(
        permission_required("leave.delete_companyleave", raise_exception=True),
        name="dispatch",
    )
    def delete(self, request, pk):
        company_leave = self.get_company_leave(pk)
        company_leave.delete()
        return Response(status=200)


class HolidayGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(
        permission_required("leave.view_holiday", raise_exception=True), name="dispatch"
    )
    def get(self, request):
        holiday = Holiday.objects.all().order_by("-id")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(holiday, request)
        serializer = HoildaySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @method_decorator(
        permission_required("leave.add_holiday", raise_exception=True), name="dispatch"
    )
    def post(self, request):
        serializer = HoildaySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class HolidayGetUpdateDeleteAPIView(APIView):

    def get_holiday(self, pk):
        try:
            return Holiday.objects.get(pk=pk)
        except Holiday.DoesNotExist as e:
            raise serializers.ValidationError(e)

    @method_decorator(
        permission_required("leave.view_holiday", raise_exception=True), name="dispatch"
    )
    def get(self, request, pk):
        holiday = self.get_holiday(pk)
        serializer = HoildaySerializer(holiday)
        return Response(serializer.data, status=200)

    @method_decorator(
        permission_required("leave.change_holiday", raise_exception=True),
        name="dispatch",
    )
    def put(self, request, pk):
        holiday = self.get_holiday(pk)
        serializer = HoildaySerializer(holiday, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @method_decorator(
        permission_required("leave.delete_holiday", raise_exception=True),
        name="dispatch",
    )
    def delete(self, request, pk):
        holiday = self.get_holiday(pk)
        holiday.delete()
        return Response(status=200)


class LeaveRequestApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_request(self, pk):
        try:
            return LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def leave_approve_calculation(self, leave_request, available_leave):
        if leave_request.requested_days > available_leave.available_days:
            leave = leave_request.requested_days - available_leave.available_days
            leave_request.approved_available_days = available_leave.available_days
            available_leave.available_days = 0
            available_leave.carryforward_days = (
                available_leave.carryforward_days - leave
            )

            leave_request.approved_carryforward_days = leave
        else:
            temp = available_leave.available_days
            available_leave.available_days = temp - leave_request.requested_days
            leave_request.approved_available_days = leave_request.requested_days
        available_leave.save()

    def leave_multiple_approve(self, request, leave_request, available_leave):
        if request.user.is_superuser:
            LeaveRequestConditionApproval.objects.filter(
                leave_request_id=leave_request
            ).update(is_approved=True)
            self.leave_approve_calculation(leave_request, available_leave)
            leave_request.status = "approved"
            leave_request.save()
        else:
            conditional_requests = leave_request.multiple_approvals()
            approver = [
                manager
                for manager in conditional_requests["managers"]
                if manager.employee_user_id == request.user
            ]
            condition_approval = LeaveRequestConditionApproval.objects.filter(
                manager_id=approver[0], leave_request_id=leave_request
            ).first()
            condition_approval.is_approved = True
            condition_approval.save()
            if approver[0] == conditional_requests["managers"][-1]:
                self.leave_approve_calculation(leave_request, available_leave)
                leave_request.status = "approved"
                leave_request.save()

    @manager_permission_required("leave.change_leaverequest")
    def put(self, request, pk):
        leave_request = self.get_leave_request(pk)
        serializer = LeaveRequestApproveSerializer(leave_request, data=request.data)
        if serializer.is_valid():
            available_leave = serializer.validated_data.get("available_leave")
            if not leave_request.multiple_approvals():
                self.leave_approve_calculation(leave_request, available_leave)
                leave_request.status = "approved"
                leave_request.save()
            else:
                self.leave_multiple_approve(request, leave_request, available_leave)
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=leave_request.employee_id.employee_user_id,
                    verb="Your Leave request has been approved",
                    verb_ar="تمت الموافقة على طلب الإجازة الخاص بك",
                    verb_de="Ihr Urlaubsantrag wurde genehmigt",
                    verb_es="Se ha aprobado su solicitud de permiso",
                    verb_fr="Votre demande de congé a été approuvée",
                    icon="people-circle",
                    redirect=f"/leave/user-request-view?id={leave_request.id}",
                    api_redirect=f"/api/leave/user-request/{leave_request.id}",
                )
            return Response(status=200)
        return Response(serializer.errors, status=400)


class LeaveRequestRejectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_request(self, pk):
        try:
            return LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def leave_calculation(self, leave_request, employee_id):
        leave_type_id = leave_request.leave_type_id
        available_leave = AvailableLeave.objects.get(
            leave_type_id=leave_type_id, employee_id=employee_id
        )
        available_leave.available_days += leave_request.approved_available_days
        available_leave.carryforward_days += leave_request.approved_carryforward_days
        available_leave.save()
        leave_request.approved_available_days = 0
        leave_request.approved_carryforward_days = 0
        leave_request.status = "rejected"
        leave_request.save()

    @manager_permission_required("leave.change_leaverequest")
    def put(self, request, pk):
        leave_request = self.get_leave_request(pk)
        employee_id = request.user.employee_get
        if leave_request.status != "rejected":
            self.leave_calculation(leave_request, employee_id)
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=leave_request.employee_id.employee_user_id,
                    verb="Your Leave request has been rejected",
                    verb_ar="تم رفض طلب الإجازة الخاص بك",
                    verb_de="Ihr Urlaubsantrag wurde abgelehnt",
                    verb_es="Tu solicitud de permiso ha sido rechazada",
                    verb_fr="Votre demande de congé a été rejetée",
                    icon="people-circle",
                    redirect=f"/leave/user-request-view?id={leave_request.id}",
                    api_redirect=f"/api/leave/user-request/{leave_request.id}/",
                )
            return Response(status=200)
        raise serializers.ValidationError("Nothing to reject.")


class LeaveRequestCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_request(self, pk):
        try:
            return LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def put(self, request, pk):
        leave_request = self.get_leave_request(pk)
        if (
            leave_request.employee_id == request.user.employee_get
            and leave_request.status == "approved"
        ):
            start_date = leave_request.start_date
            curr_date = datetime.now().date()
            if start_date >= curr_date:
                leave_request.status = "cancelled"
                leave_request.save()
                return Response(status=200)
            raise serializers.ValidationError("Nothing to cancel.")
        raise serializers.ValidationError("Access Denied.")


class LeaveAllocationApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_allocation_request(self, pk):
        try:
            return LeaveAllocationRequest.objects.get(pk=pk)
        except LeaveAllocationRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def approve_calculations(self, leave_allocation_request):
        available_leave = AvailableLeave.objects.get_or_create(
            employee_id=leave_allocation_request.employee_id,
            leave_type_id=leave_allocation_request.leave_type_id,
        )[0]
        available_leave.available_days += leave_allocation_request.requested_days
        available_leave.save()

    @manager_permission_required("leave.change_leaveallocationrequest")
    def put(self, request, pk):
        leave_allocation_request = self.get_leave_allocation_request(pk)
        if leave_allocation_request.status == "requested":
            self.approve_calculations(leave_allocation_request)
            leave_allocation_request.status = "approved"
            leave_allocation_request.save()
            return Response(status=200)
        raise serializers.ValidationError("Access Denied.")


class LeaveAllocationRequestRejectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_allocation_request(self, pk):
        try:
            return LeaveAllocationRequest.objects.get(pk=pk)
        except LeaveAllocationRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def reject_calculation(self, leave_allocation_request):
        if leave_allocation_request.status == "approved":
            leave_type = leave_allocation_request.leave_type_id
            requested_days = leave_allocation_request.requested_days
            available_leave = AvailableLeave.objects.filter(
                leave_type_id=leave_type,
                employee_id=leave_allocation_request.employee_id,
            ).first()
            available_leave.available_days = max(
                0, available_leave.available_days - requested_days
            )
            available_leave.save()

    @manager_permission_required("leave.change_leaveallocationrequest")
    def put(self, request, pk):
        leave_allocation_request = self.get_leave_allocation_request(pk)
        if leave_allocation_request.status != "rejected":
            self.reject_calculation(leave_allocation_request)
            leave_allocation_request.status = "rejected"
            leave_allocation_request.save()
            return Response(status=200)
        raise serializers.ValidationError("Access Denied.")


class LeaveRequestBulkApproveDeleteAPIview(APIView):
    permission_classes = [IsAuthenticated]

    def get_leave_requests(self, request):
        try:
            leave_request_ids = request.data.getlist("leave_request_id")
        except Exception as e:
            raise serializers.ValidationError(
                {"leave_request_id": ["This field is required"]}
            )
        leave_requests = LeaveRequest.objects.filter(id__in=leave_request_ids).exclude(
            status__in=["reject", "cancelled", "approved"]
        )
        if leave_requests:
            return leave_requests
        raise serializers.ValidationError("Nothing to approve")

    def leave_approve_calculation(self, leave_request, available_leave):
        if leave_request.requested_days > available_leave.available_days:
            leave = leave_request.requested_days - available_leave.available_days
            leave_request.approved_available_days = available_leave.available_days
            available_leave.available_days = 0
            available_leave.carryforward_days = (
                available_leave.carryforward_days - leave
            )
            leave_request.approved_carryforward_days = leave
        else:
            temp = available_leave.available_days
            available_leave.available_days = temp - leave_request.requested_days
            leave_request.approved_available_days = leave_request.requested_days
        available_leave.save()

    @manager_permission_required("leave.change_leaverequest")
    def put(self, request):
        leave_requests = self.get_leave_requests(request)
        for leave_request in leave_requests:
            employee_id = leave_request.employee_id
            leave_type_id = leave_request.leave_type_id
            available_leave = AvailableLeave.objects.get(
                leave_type_id=leave_type_id, employee_id=employee_id
            )
            total_available_leave = (
                available_leave.available_days + available_leave.carryforward_days
            )
            if total_available_leave >= leave_request.requested_days:
                self.leave_approve_calculation(leave_request, available_leave)
                leave_request.status = "approved"
                leave_request.save()
        return Response(status=200)

    @manager_permission_required("leave.delete_leaverequest")
    def delete(self, request):
        leave_requests = self.get_leave_requests(request)
        leave_requests.delete()
        return Response(status=200)


class EmployeeLeaveAllocationGetCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LeaveAllocationRequestFilter

    def get_user(self, request):
        user = request.user
        if isinstance(user, AnonymousUser):
            raise Http404("AnonymousUser")
        return user

    def get(self, request):
        employee = self.get_user(request).employee_get
        allocation_requests = employee.leaveallocationrequest_set.all().order_by("-id")
        filterset = self.filterset_class(request.GET, queryset=allocation_requests)
        paginator = PageNumberPagination()
        field_name = request.GET.get("groupby_field", None)
        if field_name:
            url = request.build_absolute_uri()
            return groupby_queryset(request, url, field_name, filterset.qs)
        page = paginator.paginate_queryset(filterset.qs, request)
        serializer = LeaveAllocationRequestGetSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        data = request.data
        employee_id = self.get_user(request).employee_get.id
        if isinstance(data, QueryDict):
            data = data.dict()
        data["employee_id"] = employee_id
        data["created_by"] = employee_id
        serializer = LeaveAllocationRequestCreateSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(status=200)
        return Response(serializer.errors, status=400)


class EmployeeLeaveAllocationUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_allocation_request(self, request, pk):
        user = request.user
        if isinstance(user, AnonymousUser):
            raise Http404("AnonymousUser")
        try:
            allocation_request = LeaveAllocationRequest.objects.get(id=pk)
            if allocation_request.employee_id == user.employee_get:
                return allocation_request
        except LeaveAllocationRequest.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def put(self, request, pk):
        allocation_request = self.get_allocation_request(request, pk)
        if allocation_request.status == "requested":
            data = request.data
            employee_id = request.user.employee_get.id
            if isinstance(data, QueryDict):
                data = data.dict()
            data["employee_id"] = employee_id
            data["created_by"] = employee_id
            serializer = LeaveAllocationRequestSerilaizer(allocation_request, data=data)
            if serializer.is_valid():
                allocation_request = serializer.save()
                return Response(
                    LeaveAllocationRequestGetSerializer(allocation_request).data,
                    status=201,
                )
            return Response(serializer.errors, status=400)
        raise serializers.ValidationError({"error": "Access Denied.."})
        return Response(status=200)

    def delete(self, request, pk):
        allocation_request = self.get_allocation_request(request, pk)
        if allocation_request.status == "requested":
            allocation_request.delete()
            return Response(status=200)
        raise serializers.ValidationError({"error": "Access Denied.."})


class LeaveRequestedApprovedCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @manager_permission_required("leave.view_leaverequest")
    def get(self, request):
        leave_requests = LeaveRequest.objects.all()
        multiple_approvals = filter_conditional_leave_request(request)
        queryset = (
            filtersubordinates(request, leave_requests, "leave.view_leaverequest")
            | multiple_approvals
        )
        requested = queryset.filter(status="requested").count()
        approved = queryset.filter(status="approved").count()
        data = {"requested": requested, "approved": approved}
        return Response(data, status=200)


class EmployeeAvailableLeaveTypeGetAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_employee(self, pk):
        try:
            return Employee.objects.get(pk=pk)
        except Employee.DoesNotExist as e:
            raise serializers.ValidationError(e)

    def get(self, request, pk):
        employee = self.get_employee(pk)
        available_leave = employee.available_leave.all()
        leave_type_ids = available_leave.values_list("leave_type_id", flat=True)
        leave_types = LeaveType.objects.filter(id__in=leave_type_ids)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(leave_types, request)
        serializer = LeaveTypeAllGetSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class LeaveTypeGetPermissionCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(
        permission_required("leave.add_leavetype", raise_exception=True),
        name="dispatch",
    )
    def get(self, request):
        return Response(status=200)


class LeaveAllocationGetPermissionCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @manager_permission_required("leave.view_leaveallocationrequest")
    def get(self, request):
        return Response(status=200)


class LeaveRequestGetPermissionCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @manager_permission_required("leave.view_leaverequest")
    def get(self, request):
        return Response(status=200)


class LeaveAssignGetPermissionCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(
        permission_required("leave.view_availableleave", raise_exception=True),
        name="dispatch",
    )
    def get(self, request):
        return Response(status=200)


class LeavePermissionCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leave_type = LeaveTypeGetPermissionCheckAPIView()
        leave_allocation = LeaveAllocationGetPermissionCheckAPIView()
        leave_request = LeaveRequestGetPermissionCheckAPIView()
        leave_assign = LeaveAssignGetPermissionCheckAPIView()
        perm_list = []
        try:
            if leave_type.get(request).status_code == 200:
                perm_list.append("leave_type")
        except:
            pass
        try:
            if leave_allocation.get(request).status_code == 200:
                perm_list.append("leave_allocation")
        except:
            pass
        try:
            if leave_request.get(request).status_code == 200:
                perm_list.append("leave_request")
                perm_list.append("leave_overview")
        except:
            pass
        try:
            if leave_assign.get(request).status_code == 200:
                perm_list.append("leave_assign")
        except:
            pass
        return Response({"perm_list": perm_list}, status=200)
