"""
Module for managing biometric devices and employee attendance.

Includes classes and functions for adding, editing, and deleting biometric devices,
as well as scheduling attendance capture. Also provides views for managing employees,
registered on biometric devices.
"""

import json
import logging
from datetime import datetime
from threading import Event, Thread
from urllib.parse import parse_qs, unquote

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from zk import ZK
from zk import exception as zk_exception

from attendance.methods.utils import Request
from attendance.views.clock_in_out import clock_in, clock_out
from base.methods import get_key_instances, get_pagination
from employee.models import Employee, EmployeeWorkInformation
from horilla.decorators import (
    hx_request_required,
    install_required,
    login_required,
    permission_required,
)
from horilla.filters import HorillaPaginator
from horilla.horilla_settings import BIO_DEVICE_THREADS

from .cosec import COSECBiometric
from .filters import BiometricDeviceFilter
from .forms import (
    BiometricDeviceForm,
    BiometricDeviceSchedulerForm,
    CosecUserAddForm,
    COSECUserForm,
    EmployeeBiometricAddForm,
)
from .models import BiometricDevices, BiometricEmployees, COSECAttendanceArguments

logger = logging.getLogger(__name__)


def str_time_seconds(time):
    """
    this method is used reconvert time in H:M formate string back to seconds and return it
    args:
        time : time in H:M format
    """

    ftr = [3600, 60, 1]
    return sum(a * b for a, b in zip(ftr, map(int, time.split(":"))))


def paginator_qry(qryset, page_number):
    """
    This method is used to paginate query set
    """
    paginator = HorillaPaginator(qryset, get_pagination())
    qryset = paginator.get_page(page_number)
    return qryset


def biometric_paginator_qry(data_list, page_number, per_page=25):
    """
    This function is used to paginate a list of dictionaries.
    """
    start_index = (page_number - 1) * per_page
    end_index = page_number * per_page
    paginated_data = {}
    paginated_data["users"] = data_list[start_index:end_index]

    total_items = len(data_list)
    total_pages = (total_items + per_page - 1) // per_page
    has_previous = page_number > 1
    has_next = page_number < total_pages

    paginated_data["paginator"] = {
        "number": page_number,
        "previous_page_number": page_number - 1 if has_previous else None,
        "next_page_number": page_number + 1 if has_next else None,
        "num_pages": total_pages,
        "has_previous": has_previous,
        "has_next": has_next,
    }
    return paginated_data


def biometric_set_time(conn):
    """
    Sets the time on the biometric device using the provided connection.

    Parameters:
    - conn: The connection to the biometric device.

    Returns:
    None
    """
    new_time = datetime.today()
    conn.set_time(new_time)


class ZKBioAttendance(Thread):
    """
    Represents a thread for capturing live attendance data from a ZKTeco biometric device.

    Attributes:
    - machine_ip: The IP address of the ZKTeco biometric device.
    - port_no: The port number for communication with the ZKTeco biometric device.
    - conn: The connection object to the ZKTeco biometric device.
    - _stop_event: Event flag to signal thread termination.

    Methods:
    - run(): Overrides the run method of the Thread class to capture live attendance data.
    - stop(): Sets the _stop_event to signal the thread to stop gracefully.
    """

    def __init__(self, machine_ip, port_no, password):
        super().__init__()
        self.machine_ip = machine_ip
        self.port_no = port_no
        self.password = int(password)
        self._stop_event = Event()  # Initialize stop event
        self.conn = None

    def run(self):
        try:
            zk_device = ZK(
                self.machine_ip,
                port=self.port_no,
                timeout=5,
                password=self.password,
                force_udp=False,
                ommit_ping=False,
            )
            conn = zk_device.connect()
            self.conn = conn
            if conn:
                device = BiometricDevices.objects.filter(
                    machine_ip=self.machine_ip, port=self.port_no
                ).first()
                if device and device.is_live:
                    while not self._stop_event.is_set():
                        attendances = conn.live_capture()
                        for attendance in attendances:
                            if attendance:
                                user_id = attendance.user_id
                                punch_code = attendance.punch
                                date_time = django_timezone.make_aware(
                                    attendance.timestamp
                                )
                                # date_time = attendance.timestamp
                                date = date_time.date()
                                time = date_time.time()
                                device.last_fetch_date = date
                                device.last_fetch_time = time
                                device.save()
                                bio_id = BiometricEmployees.objects.filter(
                                    user_id=user_id
                                ).first()
                                if bio_id:
                                    if punch_code in {0, 3, 4}:
                                        try:
                                            clock_in(
                                                Request(
                                                    user=bio_id.employee_id.employee_user_id,
                                                    date=date,
                                                    time=time,
                                                    datetime=date_time,
                                                )
                                            )
                                        except Exception as error:
                                            logger.error(
                                                "Got an error in clock_in %s", error
                                            )

                                            continue
                                    else:
                                        try:
                                            clock_out(
                                                Request(
                                                    user=bio_id.employee_id.employee_user_id,
                                                    date=date,
                                                    time=time,
                                                    datetime=date_time,
                                                )
                                            )
                                        except Exception as error:
                                            logger.error(
                                                "Got an error in clock_out", error
                                            )
                                            continue
                            else:
                                continue
        except ConnectionResetError as error:
            ZKBioAttendance(self.machine_ip, self.port_no, self.password).start()

    def stop(self):
        """To stop the ZK live capture mode"""
        self.conn.end_live_capture = True


class COSECBioAttendanceThread(Thread):
    """
    A thread class that handles the real-time retrieval and processing of
    biometric attendance data from a COSEC biometric device.

    Attributes:
        device_id (int): The ID of the biometric device to interact with.
        _stop_event (threading.Event): An event to signal when to stop the thread.

    Methods:
        run():
            Continuously fetches attendance data from the COSEC device, processes
            it, and updates the last fetched sequence and rollover count.

        stop():
            Signals the thread to stop by setting the _stop_event.
    """

    def __init__(self, device_id):
        super().__init__()
        self.device_id = device_id
        self._stop_event = Event()

    def run(self):
        try:
            device = BiometricDevices.objects.get(id=self.device_id)
            if not device.is_live:
                return

            device_args = COSECAttendanceArguments.objects.filter(
                device_id=device
            ).first()
            last_fetch_roll_ovr_count = (
                int(device_args.last_fetch_roll_ovr_count) if device_args else 0
            )
            last_fetch_seq_number = (
                int(device_args.last_fetch_seq_number) if device_args else 1
            )

            cosec = COSECBiometric(
                device.machine_ip,
                device.port,
                device.cosec_username,
                device.cosec_password,
                timeout=10,
            )
            while not self._stop_event.is_set():
                attendances = cosec.get_attendance_events(
                    last_fetch_roll_ovr_count, int(last_fetch_seq_number) + 1
                )
                if not isinstance(attendances, list):
                    self._stop_event.wait(5)
                    continue

                for attendance in attendances:
                    ref_user_id = attendance["detail-1"]
                    employee = BiometricEmployees.objects.filter(
                        ref_user_id=ref_user_id
                    ).first()
                    if not employee:
                        continue

                    date_str = attendance["date"]
                    time_str = attendance["time"]
                    attendance_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                    attendance_time = datetime.strptime(time_str, "%H:%M:%S").time()
                    attendance_datetime = datetime.combine(
                        attendance_date, attendance_time
                    )
                    punch_code = attendance["detail-2"]

                    request_data = Request(
                        user=employee.employee_id.employee_user_id,
                        date=attendance_date,
                        time=attendance_time,
                        datetime=django_timezone.make_aware(attendance_datetime),
                    )
                    try:
                        if punch_code in ["1", "3", "5", "7", "9", "0"]:
                            clock_in(request_data)
                        elif punch_code in ["2", "4", "6", "8", "10"]:
                            clock_out(request_data)
                    except Exception as error:
                        logger.error("Error processing attendance: ", error)

                if attendances:
                    last_attendance = attendances[-1]
                    last_fetch_seq_number = last_attendance["seq-No"]
                    last_fetch_roll_ovr_count = last_attendance["roll-over-count"]
                    COSECAttendanceArguments.objects.update_or_create(
                        device_id=device,
                        defaults={
                            "last_fetch_roll_ovr_count": last_fetch_roll_ovr_count,
                            "last_fetch_seq_number": last_fetch_seq_number,
                        },
                    )
                # Sleep to prevent overwhelming the device with requests
                self._stop_event.wait(2)

        except Exception as error:
            device = BiometricDevices.objects.get(id=self.device_id)
            device.is_live = False
            device.save()
            logger.error("Error in COSECBioAttendanceThread: ", error)

    def stop(self):
        """Set the stop event to signal the thread to stop gracefully."""
        self._stop_event.set()


class AnvizBiometricDeviceManager:
    """Manages communication with Anviz biometric devices for attendance records."""

    def __init__(self, device_id):
        """
        Initializes the AnvizBiometricDeviceManager.

        :param device_id: The Object ID of the biometric device.
        """
        self.device = BiometricDevices.objects.get(id=device_id)
        self.begin_time = None
        self.end_time = None

    def get_attendance_payload(self):
        """
        Constructs the payload for retrieving attendance records.

        :return: A dictionary containing the payload.
        """
        current_utc_time = datetime.utcnow()
        self.begin_time = (
            datetime.combine(self.device.last_fetch_date, self.device.last_fetch_time)
            if self.device.last_fetch_date and self.device.last_fetch_time
            else current_utc_time.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        self.end_time = current_utc_time
        begin_time_str = self.begin_time.isoformat() + "+00:00"
        end_time_str = self.end_time.isoformat() + "+00:00"
        return {
            "header": {
                "nameSpace": "attendance.record",
                "nameAction": "getrecord",
                "version": "1.0",
                "requestId": self.device.anviz_request_id,
                "timestamp": "2022-10-21T07:39:07+00:00",
            },
            "authorize": {
                "type": "token",
                "token": self.device.api_token,
            },
            "payload": {
                "begin_time": begin_time_str,
                "end_time": end_time_str,
                "order": "asc",
                "page": "1",
                "per_page": "100",
            },
        }

    def refresh_api_token(self):
        """
        Refreshes the API token for the device.

        This method sends a request to the API to refresh the token.
        """
        token_payload = {
            "header": {
                "nameSpace": "authorize.token",
                "nameAction": "token",
                "version": "1.0",
                "requestId": self.device.anviz_request_id,
                "timestamp": "2022-10-21T07:39:07+00:00",
            },
            "payload": {
                "api_key": self.device.api_key,
                "api_secret": self.device.api_secret,
            },
        }
        response = requests.post(self.device.api_url, json=token_payload, timeout=30)
        api_response = response.json()
        token = api_response["payload"]["token"]
        expires = api_response["payload"]["expires"]
        self.device.api_token = token
        self.device.api_expires = expires
        self.device.save()

    def get_attendance_records(self):
        """
        Retrieves attendance records from the biometric device.

        :return: A dictionary containing the attendance records.
        """
        token_expire = {
            "header": {"nameSpace": "System", "name": "Exception"},
            "payload": {"type": "TOKEN_EXPIRES", "message": "TOKEN_EXPIRES"},
        }
        attendance_payload = self.get_attendance_payload()
        response = requests.post(
            self.device.api_url, json=attendance_payload, timeout=30
        )
        api_response = response.json()
        if api_response == token_expire:
            self.refresh_api_token()
            attendance_payload = self.get_attendance_payload()
            response = requests.post(
                self.device.api_url, json=attendance_payload, timeout=30
            )
            api_response = response.json()
        page_count = response.json()["payload"]["pageCount"]
        if page_count > 1:
            page = attendance_payload["payload"]["page"]
            for page in range(2, page_count + 1):
                attendance_payload["payload"]["page"] = str(page)
                response = requests.post(
                    self.device.api_url, json=attendance_payload, timeout=30
                )
                if response.json() == token_expire:
                    self.refresh_api_token()
                    attendance_payload = self.get_attendance_payload()
                    response = requests.post(
                        self.device.api_url, json=attendance_payload, timeout=30
                    )
                page_records = response.json().get("payload", {}).get("list", [])
                api_response["payload"]["list"].extend(page_records)
        self.device.last_fetch_date, self.device.last_fetch_time = (
            self.end_time.date(),
            self.end_time.time(),
        )
        self.device.save()
        return api_response


@login_required
@install_required
@permission_required("biometric.view_biometricdevices")
def biometric_devices_view(request):
    """
    Renders a page displaying a list of active biometric devices.

    Parameters:
    - request: The HTTP request object.

    Returns:
    - HttpResponse: The rendered HTML page displaying the list of biometric devices.

    Template:
    - "biometric/view_biometric_devices.html"

    Context:
    - biometric_form (BiometricDeviceForm): Form for adding new biometric devices.
    - devices (QuerySet): Queryset of active biometric devices, ordered by creation date.
    - f (BiometricDeviceFilter): Form for filtering biometric devices.

    """
    biometric_form = BiometricDeviceForm()
    filter_form = BiometricDeviceFilter()
    biometric_devices = BiometricDevices.objects.filter(is_active=True).order_by(
        "-created_at"
    )
    biometric_devices = paginator_qry(biometric_devices, request.GET.get("page"))
    template = "biometric/view_biometric_devices.html"
    context = {
        "biometric_form": biometric_form,
        "devices": biometric_devices,
        "f": filter_form,
    }
    return render(request, template, context)


@login_required
@install_required
@permission_required("biometric.change_biometricdevices")
def biometric_device_schedule(request, device_id):
    """
    Handles scheduling of attendance capture from a biometric device.

    Parameters:
    - request (HttpRequest): The HTTP request object.
    - device_id (uuid): The ID of the biometric device for which scheduling is being done.

    Returns:
    - HttpResponse: HTML response indicating success or failure of the scheduling operation.
    """
    device = BiometricDevices.objects.get(id=device_id)
    initial_data = {"scheduler_duration": device.scheduler_duration}
    scheduler_form = BiometricDeviceSchedulerForm(initial=initial_data)
    context = {
        "scheduler_form": scheduler_form,
        "device_id": device_id,
    }
    if request.method == "POST":
        scheduler_form = BiometricDeviceSchedulerForm(request.POST)
        if scheduler_form.is_valid():
            if device.machine_type == "zk":
                try:
                    port_no = device.port
                    machine_ip = device.machine_ip
                    password = device.zk_password
                    conn = None
                    zk_device = ZK(
                        machine_ip,
                        port=port_no,
                        timeout=5,
                        password=int(password),
                        force_udp=False,
                        ommit_ping=False,
                    )
                    conn = zk_device.connect()
                    conn.test_voice(index=0)
                    duration = request.POST.get("scheduler_duration")
                    device = BiometricDevices.objects.get(id=device_id)
                    device.scheduler_duration = duration
                    device.is_scheduler = True
                    device.is_live = False
                    device.save()
                    scheduler = BackgroundScheduler()
                    scheduler.add_job(
                        lambda: zk_biometric_device_attendance(device.id),
                        "interval",
                        seconds=str_time_seconds(device.scheduler_duration),
                    )
                    scheduler.start()
                    return HttpResponse("<script>window.location.reload()</script>")
                except Exception as error:
                    logger.error("An error comes in biometric_device_schedule ", error)
                    script = """
                    <script>
                        Swal.fire({
                          title : "Schedule Attendance unsuccessful",
                          text: "Please double-check the accuracy of the provided IP Address and Port Number for correctness",
                          icon: "warning",
                          showConfirmButton: false,
                          timer: 3500,
                          timerProgressBar: true,
                          didClose: () => {
                            location.reload();
                            },
                        });
                    </script>
                    """
                    return HttpResponse(script)
            elif device.machine_type == "anviz":
                duration = request.POST.get("scheduler_duration")
                device.is_scheduler = True
                device.scheduler_duration = duration
                device.save()
                scheduler = BackgroundScheduler()
                scheduler.add_job(
                    lambda: anviz_biometric_device_attendance(device.id),
                    "interval",
                    seconds=str_time_seconds(device.scheduler_duration),
                )
                scheduler.start()
                return HttpResponse("<script>window.location.reload()</script>")
            else:
                duration = request.POST.get("scheduler_duration")
                device.is_scheduler = True
                device.is_live = False
                device.scheduler_duration = duration
                device.save()
                scheduler = BackgroundScheduler()
                existing_thread = BIO_DEVICE_THREADS.get(device.id)
                if existing_thread:
                    existing_thread.stop()
                    del BIO_DEVICE_THREADS[device.id]
                scheduler.add_job(
                    lambda: cosec_biometric_device_attendance(device.id),
                    "interval",
                    seconds=str_time_seconds(device.scheduler_duration),
                )
                scheduler.start()
                return HttpResponse("<script>window.location.reload()</script>")

        context["scheduler_form"] = scheduler_form
        response = render(request, "biometric/scheduler_device_form.html", context)
        return HttpResponse(
            response.content.decode("utf-8")
            + "<script>$('#BiometricDeviceTestModal').removeClass('oh-modal--show');\
            $('#BiometricDeviceModal').toggleClass('oh-modal--show');</script>"
        )
    return render(request, "biometric/scheduler_device_form.html", context)


@login_required
@install_required
@hx_request_required
@permission_required("biometric.change_biometricdevices")
def biometric_device_unschedule(request, device_id):
    """
    Handles unschedule of attendance capture for a biometric device.

    Parameters:
    - request (HttpRequest): The HTTP request object.
    - device_id (uuid): The ID of the biometric device for which unscheduling is being done.

    Returns:
    - HttpResponseRedirect: Redirects to the biometric devices view after unscheduling.
    """
    previous_data = request.GET.urlencode()
    device = BiometricDevices.objects.get(id=device_id)
    device.is_scheduler = False
    device.save()
    messages.success(request, _("Biometric device unscheduled successfully"))
    return redirect(f"/biometric/search-devices?{previous_data}")


@login_required
@install_required
@hx_request_required
@permission_required("biometric.add_biometricdevices")
def biometric_device_add(request):
    """
    Handles the addition of a new biometric device.

    Parameters:
    - request (HttpRequest): The HTTP request object containing data about the request.

    Returns:
    - HttpResponse: Renders the 'add_biometric_device.html' template with the biometric device form.
    """
    previous_data = unquote(request.GET.urlencode())[len("pd=") :]
    biometric_form = BiometricDeviceForm()
    if request.method == "POST":
        biometric_form = BiometricDeviceForm(request.POST)
        if biometric_form.is_valid():
            biometric_form.save()
            messages.success(request, _("Biometric device added successfully."))
            biometric_form = BiometricDeviceForm()
    context = {"biometric_form": biometric_form, "pd": previous_data}
    return render(request, "biometric/add_biometric_device.html", context)


@login_required
@install_required
@hx_request_required
@permission_required("biometric.change_biometricdevices")
def biometric_device_edit(request, device_id):
    """
    Handles the editing of an existing biometric device.

    Parameters:
    - request (HttpRequest): The HTTP request object containing data about the request.
    - device_id (uuid): The ID of the biometric device to be edited.

    Returns:
    - HttpResponse: Renders the 'edit_biometric_device.html' template with the biometric
                    device form pre-filled with existing data.
    """
    device = BiometricDevices.objects.get(id=device_id)
    biometric_form = BiometricDeviceForm(instance=device)
    if request.method == "POST":
        biometric_form = BiometricDeviceForm(request.POST, instance=device)
        if biometric_form.is_valid():
            biometric_form.save()
            messages.success(request, _("Biometric device updated successfully."))
    context = {
        "biometric_form": biometric_form,
        "device_id": device_id,
    }
    return render(request, "biometric/edit_biometric_device.html", context)


@login_required
@install_required
@hx_request_required
@permission_required("biometric.change_biometricdevices")
def biometric_device_archive(request, device_id):
    """
    This method is used to archive or un-archive devices
    """
    previous_data = request.GET.urlencode()
    device_obj = BiometricDevices.objects.get(id=device_id)
    device_obj.is_active = not device_obj.is_active
    device_obj.save()
    message = _("archived") if not device_obj.is_active else _("un-archived")
    messages.success(request, _("Device is %(message)s") % {"message": message})
    return redirect(f"/biometric/search-devices?{previous_data}")


@login_required
@install_required
@hx_request_required
@permission_required("biometric.delete_biometricdevices")
def biometric_device_delete(request, device_id):
    """
    Handles the deletion of a biometric device.

    Parameters:
    - request (HttpRequest): The HTTP request object containing data about the request.
    - device_id (uuid): The ID of the biometric device to be deleted.

    Returns:
    - HttpResponseRedirect: Redirects to the 'search-devices' page after deleting the
                            biometric device.

    """
    device = BiometricDevices.objects.get(id=device_id)
    device.delete()
    previous_data = request.GET.urlencode()
    messages.success(request, _("Biometric device deleted successfully."))
    return redirect(f"/biometric/search-devices?{previous_data}")


@login_required
@install_required
@hx_request_required
@permission_required("biometric.view_biometricdevices")
def search_devices(request):
    """
    This method is used to search biometric device model and return matching objects
    """
    previous_data = request.GET.urlencode()
    search = request.GET.get("search")
    is_active = request.GET.get("is_active")
    if search is None:
        search = ""
    devices = BiometricDeviceFilter(request.GET).qs.order_by("-created_at")
    if not is_active or is_active == "unknown":
        devices = devices.filter(is_active=True)
    data_dict = []
    data_dict = parse_qs(previous_data)
    get_key_instances(BiometricDevices, data_dict)
    template = "biometric/card_biometric_devices.html"
    if request.GET.get("view") == "list":
        template = "biometric/list_biometric_devices.html"

    devices = paginator_qry(devices, request.GET.get("page"))
    return render(
        request,
        template,
        {
            "devices": devices,
            "pd": previous_data,
            "filter_dict": data_dict,
        },
    )


@login_required
@install_required
@hx_request_required
@permission_required("biometric.add_biometricdevices")
def biometric_device_test(_request, device_id):
    """
    Test the connection with the specified biometric device.

    Parameters:
    - request (HttpRequest): Django HttpRequest object.
    - device_id (uuid): ID of the biometric device to test.

    Returns:
    - HttpResponse: HTML response containing JavaScript code to display
                    a notification about the connection test result.
    """
    device = BiometricDevices.objects.get(id=device_id)
    if device.machine_type == "zk":
        port_no = device.port
        machine_ip = device.machine_ip
        password = device.zk_password
        conn = None
        # create ZK instance
        zk_device = ZK(
            machine_ip,
            port=port_no,
            timeout=5,
            password=int(password),
            force_udp=False,
            ommit_ping=False,
        )
        try:
            conn = zk_device.connect()
            conn.test_voice(index=0)
            find_employees_in_zk(device_id)
            script = """<script>
                    Swal.fire({
                      text: "Test connection successful.",
                      icon: "success",
                      showConfirmButton: false,
                      timer: 1500,
                      timerProgressBar: true,
                      didClose: () => {
                        location.reload();
                        },
                    });
                    </script>
                """
        except zk_exception.ZKErrorResponse as error:
            script = """
           <script>
                Swal.fire({
                  title : "Failed to connect: Authentication error.",
                  text: "Please double-check the accuracy of the provided IP Address, Port Number and Password for correctness",
                  icon: "warning",
                  showConfirmButton: false,
                  timer: 3500,
                  timerProgressBar: true,
                  didClose: () => {
                    location.reload();
                    },
                });
            </script>
            """

        except Exception as error:
            logger.error("An error comes in biometric_device_test ", error)
            script = """
           <script>
                Swal.fire({
                  title : "Connection unsuccessful",
                  text: "Please double-check the accuracy of the provided IP Address, Port Number and Password for correctness",
                  icon: "warning",
                  showConfirmButton: false,
                  timer: 3500,
                  timerProgressBar: true,
                  didClose: () => {
                    location.reload();
                    },
                });
            </script>
            """
        finally:
            if conn:
                conn.disconnect()
    elif device.machine_type == "anviz":
        payload = {
            "header": {
                "nameSpace": "authorize.token",
                "nameAction": "token",
                "version": "1.0",
                "requestId": device.anviz_request_id,
                "timestamp": "2022-10-21T07:39:07+00:00",
            },
            "payload": {"api_key": device.api_key, "api_secret": device.api_secret},
        }
        error = {
            "header": {"nameSpace": "System", "name": "Exception"},
            "payload": {"type": "AUTH_ERROR", "message": "AUTH_ERROR"},
        }
        script = """
           <script>
                Swal.fire({
                  title : "Connection unsuccessful",
                  text: "Please double-check the accuracy of the provided API Url , API Key and API Secret for correctness",
                  icon: "warning",
                  showConfirmButton: false,
                  timer: 3500,
                  timerProgressBar: true,
                  didClose: () => {
                    location.reload();
                    },
                });
            </script>
            """
        try:
            response = requests.post(device.api_url, json=payload, timeout=5)
            if response.status_code != 200:
                pass
            api_response = response.json()
            if api_response == error:
                pass
            else:
                payload = api_response["payload"]
                api_token = payload["token"]
                api_expires = payload["expires"]
                device.api_token = api_token
                device.api_expires = api_expires
                device.save()
                anviz_device = AnvizBiometricDeviceManager(device_id)
                attendance_records = anviz_device.get_attendance_records()
                script = """<script>
                    Swal.fire({
                      text: "Test connection successful.",
                      icon: "success",
                      showConfirmButton: false,
                      timer: 1500,
                      timerProgressBar: true,
                      didClose: () => {
                        location.reload();
                        },
                    });
                    </script>
                """
        except Exception as error:
            logger.error(
                "Got an error in test connection of Anviz Biometric Device", error
            )
            pass
    elif device.machine_type == "cosec":
        cosec = COSECBiometric(
            device.machine_ip,
            device.port,
            device.cosec_username,
            device.cosec_password,
            timeout=10,
        )
        response = cosec.basic_config()
        if response.get("app"):
            find_employees_in_cosec(device_id)
            script = """<script>
                    Swal.fire({
                      text: "Test connection successful.",
                      icon: "success",
                      showConfirmButton: false,
                      timer: 1500,
                      timerProgressBar: true,
                      didClose: () => {
                        location.reload();
                        },
                    });
                    </script>
                """
        else:
            script = """
           <script>
                Swal.fire({
                  title : "Connection unsuccessful",
                  text: "Please double-check the accuracy of the provided Machine IP , Username and Password for correctness",
                  icon: "warning",
                  showConfirmButton: false,
                  timer: 3500,
                  timerProgressBar: true,
                  didClose: () => {
                    location.reload();
                    },
                });
            </script>
            """
    else:
        script = """
           <script>
                Swal.fire({
                  title : "Connection unsuccessful",
                  text: "Please select a valid biometric device",
                  icon: "warning",
                  showConfirmButton: false,
                  timer: 3500,
                  timerProgressBar: true,
                  didClose: () => {
                    location.reload();
                    },
                });
            </script>
            """

    return HttpResponse(script)


def zk_employees_fetch(device):
    """
    Fetch employee data from the specified ZK biometric device.

    Parameters:
    - device: Biometric device object containing machine IP, port, etc.

    Returns:
    - list: A list of dictionaries, where each dictionary represents an employee
            with associated data including user ID, employee ID, work email,
            phone number, job position, badge ID, and fingerprint data.
    """
    zk_device = ZK(
        device.machine_ip,
        port=device.port,
        timeout=1,
        password=int(device.zk_password),
        force_udp=False,
        ommit_ping=False,
    )
    conn = zk_device.connect()
    conn.enable_device()
    users = conn.get_users()
    fingers = conn.get_templates()
    employees = []
    for user in users:
        user_id = user.user_id
        uid = user.uid
        bio_id = BiometricEmployees.objects.filter(user_id=user_id).first()
        if bio_id:
            employee = bio_id.employee_id
            employee_work_info = EmployeeWorkInformation.objects.filter(
                employee_id=employee
            ).first()
            if employee_work_info:
                work_email = (
                    employee_work_info.email if employee_work_info.email else None
                )
                phone = employee_work_info.mobile if employee_work_info.mobile else None
                job_position = (
                    employee_work_info.job_position_id
                    if employee_work_info.job_position_id
                    else None
                )
                user.__dict__["work_email"] = work_email
                user.__dict__["phone"] = phone
                user.__dict__["job_position"] = job_position
            else:
                user.__dict__["work_email"] = None
                user.__dict__["phone"] = None
                user.__dict__["job_position"] = None
            user.__dict__["employee"] = employee
            user.__dict__["badge_id"] = employee.badge_id
            finger_print = []
            for finger in fingers:
                if finger.uid == uid:
                    finger_print.append(finger.fid)
            if not finger_print:
                finger_print = []
            user.__dict__["finger"] = finger_print
            employees.append(user)
    return employees


def cosec_employee_fetch(device_id):
    """
    Fetch employee data from the COSEC biometric device associated with the specified device ID.

    Parameters:
    - device_id: ID of the biometric device.

    Returns:
    - list: A list of dictionaries, where each dictionary represents an employee with associated
            data including user ID, employee ID, finger count, and card count.
    """
    users = []
    device = BiometricDevices.objects.get(id=device_id)
    employees = BiometricEmployees.objects.filter(device_id=device)
    cosec = COSECBiometric(
        device.machine_ip, device.port, device.cosec_username, device.cosec_password
    )
    for employee in employees:
        user = cosec.get_cosec_user(user_id=employee.user_id)
        if user.get("user-id"):
            user["employee_id"] = employee.employee_id
            user_credential = cosec.get_user_credential_count(user_id=employee.user_id)
            user["finger-count"] = user_credential.get("finger-count")
            user["face-count"] = user_credential.get("face-count")
            user["card-count"] = user_credential.get("card-count")
            new_dict = {}
            for key, value in user.items():
                new_key = key.replace("-", "_")
                new_dict[new_key] = value
            users.append(new_dict)
        else:
            BiometricEmployees.objects.get(id=employee.id).delete()
    return users


def find_employees_in_cosec(device_id):
    """
    Synchronize active employees with a COSEC biometric device.

    This function retrieves a list of active employees from the database,
    checks their presence on a specified COSEC biometric device, and updates
    the database with employees who are registered on the COSEC device.

    Args:
        device_id (uuid): The ID of the biometric device to synchronize with.
    """
    device = BiometricDevices.objects.get(id=device_id)
    employees = Employee.objects.filter(is_active=True).values_list("id", "badge_id")
    cosec = COSECBiometric(
        device.machine_ip, device.port, device.cosec_username, device.cosec_password
    )
    existing_user_ids = BiometricEmployees.objects.filter(device_id=device).values_list(
        "user_id", flat=True
    )
    biometric_employees_to_create = []
    for employee_id, badge_id in employees:
        if badge_id and badge_id.isalnum() and len(badge_id) <= 15:
            user = cosec.get_cosec_user(user_id=badge_id)
            if user.get("user-id") and user.get("user-id") not in existing_user_ids:
                biometric_employees_to_create.append(
                    BiometricEmployees(
                        ref_user_id=user.get("ref-user-id"),
                        user_id=user.get("user-id"),
                        employee_id_id=employee_id,
                        device_id_id=device_id,
                    )
                )
    BiometricEmployees.objects.bulk_create(biometric_employees_to_create)


def find_employees_in_zk(device_id):
    """
    Synchronize active employees with a COSEC biometric device.

    This function retrieves a list of active employees from the database,
    checks their presence on a specified COSEC biometric device, and updates
    the database with employees who are registered on the COSEC device.

    Args:
        device_id (uuid): The ID of the biometric device to synchronize with.
    """
    device = BiometricDevices.objects.get(id=device_id)
    employees = Employee.objects.filter(is_active=True).values_list("id", "badge_id")
    existing_user_ids = set(
        BiometricEmployees.objects.filter(device_id=device_id).values_list(
            "user_id", flat=True
        )
    )
    zk_device = ZK(
        device.machine_ip, port=device.port, password=int(device.zk_password), timeout=5
    )
    conn = zk_device.connect()
    zk_users = {user.user_id: user.uid for user in conn.get_users()}
    biometric_employees_to_create = [
        BiometricEmployees(
            uid=zk_users[badge_id],
            user_id=badge_id,
            employee_id_id=employee_id,
            device_id_id=device_id,
        )
        for employee_id, badge_id in employees
        if badge_id
        and badge_id.isalnum()
        and len(badge_id) <= 9
        and badge_id in zk_users
        and badge_id not in existing_user_ids
    ]
    BiometricEmployees.objects.bulk_create(biometric_employees_to_create)
    conn.disconnect()


@login_required
@install_required
@permission_required("biometric.view_biometricemployees")
def biometric_device_employees(request, device_id, **kwargs):
    """
    View function to display employees associated with a biometric device.

    Depending on the machine type of the biometric device (either "zk" or "cosec"),
    this function fetches the relevant employees and renders the appropriate template.

    Args:
        request (HttpRequest): The HTTP request object.
        device_id (uuid): The ID of the biometric device.
        **kwargs: Additional keyword arguments.

    Returns:
        HttpResponse: The rendered template response or a redirect to `biometric_devices_view`
                      in case of an error.
    """
    previous_data = request.GET.urlencode()
    device = BiometricDevices.find(device_id)
    if device:
        try:
            if device.machine_type == "zk":
                employee_add_form = EmployeeBiometricAddForm()
                employees = zk_employees_fetch(device)
                employees = paginator_qry(employees, request.GET.get("page"))
                context = {
                    "employees": employees,
                    "device_id": device_id,
                    "form": employee_add_form,
                    "pd": previous_data,
                }
                return render(
                    request, "biometric/view_employees_biometric.html", context
                )
            if device.machine_type == "cosec":
                employee_add_form = CosecUserAddForm()
                employees = cosec_employee_fetch(device_id)
                employees = biometric_paginator_qry(
                    employees, int(request.GET.get("page", 1))
                )
                context = {
                    "employees": employees,
                    "device_id": device.id,
                    "form": employee_add_form,
                    "pd": previous_data,
                }
                return render(request, "biometric/view_cosec_employees.html", context)
        except Exception as error:
            logger.error("An error occurred: ", error)
            messages.info(
                request,
                _(
                    "Failed to establish a connection. Please verify the accuracy of the IP\
                    Address , Port No. and Password of the device."
                ),
            )
    else:
        messages.error(request, _("Biometric device not found"))
    return redirect(biometric_devices_view)


@login_required
@install_required
@hx_request_required
@permission_required("biometric.view_biometricemployees")
def search_employee_device(request):
    """
    View function to search for employees associated with a specific biometric device.

    This function handles searching employees based on their first name and the type of
    biometric device (either "zk" or "cosec"). It then renders the appropriate template
    with the filtered employee list.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered template response with the context.
    """
    previous_data = request.GET.urlencode()
    device_id = request.GET.get("device")
    device = BiometricDevices.objects.get(id=device_id)
    search = request.GET.get("search")
    if device.machine_type == "zk":
        employees = zk_employees_fetch(device)
        if search:
            search_employees = BiometricEmployees.objects.filter(
                employee_id__employee_first_name__icontains=search
            )
            search_uids = search_employees.values_list("uid", flat=True)
            employees = [
                employee for employee in employees if employee.uid in search_uids
            ]
        employees = paginator_qry(employees, request.GET.get("page"))
        template = "biometric/list_employees_biometric.html"
        context = {
            "employees": employees,
            "device_id": device_id,
            "pd": previous_data,
        }
    else:
        employees = cosec_employee_fetch(device_id)
        if search:
            search_employees = BiometricEmployees.objects.filter(
                employee_id__employee_first_name__icontains=search, device_id=device
            )
        else:
            search_employees = BiometricEmployees.objects.filter(device_id=device)
        queryset_user_ids = [employee.user_id for employee in search_employees]
        filtered_employees = [
            employee
            for employee in employees
            if employee["user_id"] in queryset_user_ids
        ]
        filtered_employees = biometric_paginator_qry(
            filtered_employees, int(request.GET.get("page", 1))
        )
        template = "biometric/list_employees_cosec_biometric.html"
        context = {
            "employees": filtered_employees,
            "device_id": device_id,
            "pd": previous_data,
        }
    return render(request, template, context)


@login_required
@install_required
@permission_required("biometric.delete_biometricemployees")
def delete_biometric_user(request, uid, device_id):
    """
    This function connects to the specified biometric device, deletes the user
    identified by the given UID, and removes the corresponding entry from the
    BiometricEmployees table in the local database

    Args:
        request (HttpRequest): The HTTP request object.
        uid (str): The UID of the user to be deleted from the biometric device.
        device_id (uuid): The ID of the biometric device.

    Returns:
        HttpResponse: A redirect response to the list of employees for the specified
                      biometric device.
    """
    device = BiometricDevices.objects.get(id=device_id)
    zk_device = ZK(
        device.machine_ip,
        port=device.port,
        timeout=5,
        password=int(device.zk_password),
        force_udp=False,
        ommit_ping=False,
    )
    conn = zk_device.connect()
    conn.delete_user(uid=uid)
    employee_bio = BiometricEmployees.objects.filter(uid=uid).first()
    employee_bio.delete()
    messages.success(
        request,
        _("{} successfully removed from the biometric device.").format(
            employee_bio.employee_id
        ),
    )
    redirect_url = f"/biometric/biometric-device-employees/{device_id}/"
    return redirect(redirect_url)


@login_required
@install_required
@permission_required("biometric.change_biometricemployees")
def enable_cosec_face_recognition(request, user_id, device_id):
    """
    View function to enable face recognition for a user on a COSEC biometric device

    Args:
        request (HttpRequest): The HTTP request object.
        user_id (str): The ID of the user for whom face recognition is to be enabled.
        device_id (uuid): The ID of the COSEC biometric device.

    Returns:
        HttpResponse: A redirect response to the list of employees for the specified
                      biometric device.
    """
    device = BiometricDevices.find(device_id)
    if device:
        cosec = COSECBiometric(
            device.machine_ip,
            device.port,
            device.cosec_username,
            device.cosec_password,
        )
        enable_fr = cosec.enable_user_face_recognition(user_id=user_id, enable_fr=True)
        response_code = enable_fr.get("Response-Code")
        if response_code == "0":
            messages.success(request, _("Face recognition enabled successfully"))
        else:
            messages.error(request, _("Something went wrong when enabling face"))
    else:
        messages.error(request, _("Device not found"))
    return redirect(f"/biometric/biometric-device-employees/{device_id}/")


@login_required
@install_required
@hx_request_required
@permission_required("biometric.change_biometricemployees")
def edit_cosec_user(request, user_id, device_id):
    """
    View function to edit the details of a COSEC biometric user.

    Args:
        request (HttpRequest): The HTTP request object.
        user_id (str): The ID of the user to be edited.
        device_id (uuid): The ID of the COSEC biometric device.

    Returns:
        HttpResponse: The rendered form template for GET requests, and a response with
                      a success message for valid POST requests. Reloads the page after
                      successful update.

    """
    device = BiometricDevices.objects.get(id=device_id)
    cosec = COSECBiometric(
        device.machine_ip,
        device.port,
        device.cosec_username,
        device.cosec_password,
    )
    user = cosec.get_cosec_user(user_id)
    if user.get("name"):
        year = int(user["validity-date-yyyy"])
        month = int(user["validity-date-mm"])
        day = int(user["validity-date-dd"])
        date_object = datetime(year, month, day)
        formatted_date = date_object.strftime("%Y-%m-%d")
        initial_data = {
            "name": user["name"],
            "user_active": bool(int(user["user-active"])),
            "vip": bool(int(user["vip"])),
            "validity_enable": bool(int(user["validity-enable"])),
            "validity_end_date": formatted_date,
        }

        if "by-pass-finger" in user:
            initial_data["by_pass_finger"] = bool(int(user["by-pass-finger"]))

        form = COSECUserForm(initial=initial_data)

        if request.method == "POST":
            form = COSECUserForm(request.POST)
            if form.is_valid():
                name = form.cleaned_data["name"]
                user_active = form.cleaned_data["user_active"]
                vip = form.cleaned_data["vip"]
                validity_enable = form.cleaned_data["validity_enable"]
                validity_end_date_str = str(form.cleaned_data["validity_end_date"])
                validity_end_date = datetime.strptime(
                    validity_end_date_str, "%Y-%m-%d"
                ).date()
                validity_year = validity_end_date.year
                validity_month = validity_end_date.month
                validity_day = validity_end_date.day
                by_pass_finger = form.cleaned_data["by_pass_finger"]
                update_user = cosec.set_cosec_user(
                    user_id=user["user-id"],
                    ref_user_id=user["ref-user-id"],
                    name=name,
                    user_active=int(user_active),
                    vip=int(vip),
                    by_pass_finger=int(by_pass_finger),
                    validity_enable=int(validity_enable),
                    validity_date_dd=validity_day,
                    validity_date_mm=validity_month,
                    validity_date_yyyy=validity_year,
                )
                if (
                    update_user.get("Response-Code")
                    and update_user.get("Response-Code") == "0"
                ):
                    messages.success(
                        request, _("Biometric user data updated successfully")
                    )
                    return HttpResponse("<script>window.location.reload()</script>")
                if update_user.get("error"):
                    error = update_user.get("error")
                    if "validity-date-yyyy" in error:
                        form.add_error(
                            None,
                            _(
                                "This date cannot be used as the Validity End Date for\
                                the COSEC Biometric."
                            ),
                        )
        return render(
            request,
            "biometric/edit_cosec_user.html",
            context={"form": form, "user_id": user_id, "device_id": device_id},
        )


@login_required
@install_required
@permission_required("biometric.delete_biometricemployees")
def delete_horilla_cosec_user(request, user_id, device_id):
    """
    View function to delete a user from a COSEC biometric device and database.

    Args:
        request (HttpRequest): The HTTP request object.
        user_id (str): The ID of the user to be deleted from the COSEC biometric device.
        device_id (uuid): The ID of the COSEC biometric device.

    Returns:
        HttpResponse: A redirect response to the list of employees for the specified
                      biometric device.
    """
    device = BiometricDevices.find(device_id)
    if device:
        employee_bio = BiometricEmployees.objects.filter(
            user_id=user_id, device_id=device
        ).first()
        cosec = COSECBiometric(
            device.machine_ip,
            device.port,
            device.cosec_username,
            device.cosec_password,
        )
        response = cosec.delete_cosec_user(user_id)
        if response.get("Response-Code") and response.get("Response-Code") == "0":
            employee_bio.delete()
            messages.success(
                request,
                _("{} successfully removed from the biometric device.").format(
                    employee_bio.employee_id
                ),
            )
        else:
            messages.error(request, _("Biometric user not found"))
    else:
        messages.error(request, _("Biometric device not found"))
    redirect_url = (
        f"/biometric/biometric-device-employees/{device_id}/"
        if device
        else "/biometric/view-biometric-devices/"
    )
    return redirect(redirect_url)


@login_required
@install_required
@permission_required("biometric.delete_biometricemployees")
def bio_users_bulk_delete(request):
    """
    View function to delete multiple users from a ZK biometric device and the local database.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: A JSON response indicating the success of the bulk delete operation.

    """
    conn = None
    json_ids = request.POST["ids"]
    device_id = request.POST["deviceId"]
    ids = json.loads(json_ids)
    device = BiometricDevices.objects.get(id=device_id)
    try:
        zk_device = ZK(
            device.machine_ip,
            port=device.port,
            timeout=5,
            password=int(device.zk_password),
            force_udp=False,
            ommit_ping=False,
        )
        conn = zk_device.connect()
        for user_id in ids:
            user_id = int(user_id)
            conn.delete_user(user_id=user_id)
            employee_bio = BiometricEmployees.objects.filter(user_id=user_id).first()
            employee_bio.delete()
            conn.refresh_data()
            messages.success(
                request,
                _("{} successfully removed from the biometric device.").format(
                    employee_bio.employee_id
                ),
            )
    except Exception as error:
        logger.error("An error occurred: ", error)
    return JsonResponse({"messages": "Success"})


@login_required
@install_required
@permission_required("biometric.delete_biometricemployees")
def cosec_users_bulk_delete(request):
    """
    View function to delete multiple users from a COSEC biometric device and database.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: A JSON response indicating the success of the bulk delete operation.
    """
    json_ids = request.POST["ids"]
    device_id = request.POST["deviceId"]
    ids = json.loads(json_ids)
    device = BiometricDevices.objects.get(id=device_id)
    try:
        cosec = COSECBiometric(
            device.machine_ip,
            device.port,
            device.cosec_username,
            device.cosec_password,
        )
        for user_id in ids:
            cosec.delete_cosec_user(user_id=user_id)
            employee_bio = BiometricEmployees.objects.filter(
                user_id=user_id, device_id=device
            ).first()
            if employee_bio:
                employee_bio.delete()
            messages.success(
                request,
                f"{employee_bio.employee_id} "
                + _("successfully removed from the biometric device."),
            )

    except Exception as error:
        logger.error("An error occurred: ", error)
    return JsonResponse({"messages": "Success"})


@login_required
@install_required
@hx_request_required
@permission_required("biometric.add_biometricemployees")
def add_biometric_user(request, device_id):
    """
    View function to add a new user to a biometric device.

    This function adds a new user to the specified biometric device and stores their
    information in the database.

    Args:
        request (HttpRequest): The HTTP request object.
        device_id (uuid): The ID of the biometric device.

    Returns:
        HttpResponse: A JavaScript script to reload the current page after adding the user.

    """
    device = BiometricDevices.objects.get(id=device_id)
    employee_add_form = (
        EmployeeBiometricAddForm()
        if device.machine_type == "zk"
        else CosecUserAddForm()
    )
    if request.method == "POST":
        device = BiometricDevices.objects.get(id=device_id)
        try:
            if device.machine_type == "zk":
                zk_device = ZK(
                    device.machine_ip,
                    port=device.port,
                    timeout=5,
                    password=int(device.zk_password),
                    force_udp=False,
                    ommit_ping=False,
                )
                conn = zk_device.connect()
                conn.enable_device()
                existing_uids = [user.uid for user in conn.get_users()]
                existing_user_ids = [user.user_id for user in conn.get_users()]
                uid = 1
                user_id = 1000
                employee_ids = request.POST.getlist("employee_ids")
                for obj_id in employee_ids:
                    employee = Employee.objects.get(id=obj_id)
                    existing_biometric_employee = BiometricEmployees.objects.filter(
                        employee_id=employee, device_id=device
                    ).first()
                    if existing_biometric_employee is None:
                        while uid in existing_uids or user_id in existing_user_ids:
                            user_id = int(user_id)
                            uid += 1
                            user_id += 1
                        existing_uids.append(uid)
                        existing_user_ids.append(user_id)
                        employee_name = employee.get_full_name()
                        conn.set_user(
                            uid=uid,
                            name=employee_name,
                            password="",
                            group_id="",
                            user_id=str(user_id),
                            card=0,
                        )
                        # The ZK Biometric user ID must be a character value
                        # that can be converted to an integer.
                        BiometricEmployees.objects.create(
                            uid=uid,
                            user_id=str(user_id),
                            employee_id=employee,
                            device_id=device,
                        )
                        messages.success(
                            request,
                            _("{} added to biometric device successfully").format(
                                employee
                            ),
                        )
                    else:
                        messages.info(
                            request,
                            _("{} already added to biometric device").format(employee),
                        )
            else:
                cosec = COSECBiometric(
                    device.machine_ip,
                    device.port,
                    device.cosec_username,
                    device.cosec_password,
                )
                basic = cosec.basic_config()
                if basic.get("app"):
                    employee_ids = request.POST.getlist("employee_ids")
                    cosec_users = BiometricEmployees.objects.filter(device_id=device_id)
                    existing_ref_user_ids = list(
                        cosec_users.values_list("ref_user_id", flat=True)
                    )
                    for obj_id in employee_ids:
                        employee = Employee.objects.get(id=obj_id)
                        employee_name = employee.get_full_name()
                        user_id = employee.badge_id
                        ref_user_id = 100
                        while ref_user_id in existing_ref_user_ids:
                            ref_user_id += 1
                        existing_ref_user_ids.append(ref_user_id)
                        user = cosec.set_cosec_user(
                            user_id=user_id,
                            ref_user_id=ref_user_id,
                            name=employee_name,
                            user_active=True,
                            validity_enable=True,
                            validity_date_dd=1,
                            validity_date_mm=1,
                            validity_date_yyyy=2035,
                        )
                        response = user.get("Response-Code")
                        if response and response == "0":
                            BiometricEmployees.objects.create(
                                ref_user_id=ref_user_id,
                                user_id=user_id,
                                employee_id=employee,
                                device_id=device,
                            )
        except Exception as error:
            if device.machine_type == "zk":
                conn.disable_device()
                logger.error("An error occurred: ", str(error))
        return HttpResponse("<script>window.location.reload()</script>")
    return render(
        request,
        "biometric/add_biometric_user.html",
        context={"form": employee_add_form, "device_id": device_id},
    )


@login_required
@install_required
@hx_request_required
@permission_required("biometric.change_biometricdevices")
def biometric_device_live(request):
    """
    Activate or deactivate live capture mode for a biometric device based on the request parameters.

    :param request: The Django request object.
    :return: A JsonResponse containing a script to be executed on the client side.
    """
    is_live = request.GET.get("is_live")
    device_id = request.GET.get("deviceId")
    device = BiometricDevices.objects.get(id=device_id)
    is_live = is_live == "on"
    if is_live:
        port_no = device.port
        machine_ip = device.machine_ip
        password = int(device.zk_password)
        conn = None
        # create ZK instance
        try:
            if device.machine_type == "zk":
                zk_device = ZK(
                    machine_ip,
                    port=port_no,
                    timeout=5,
                    password=int(password),
                    force_udp=False,
                    ommit_ping=False,
                )
                conn = zk_device.connect()
                instance = ZKBioAttendance(machine_ip, port_no, password)
                conn.test_voice(index=14)
                if conn:
                    device.is_live = True
                    device.is_scheduler = False
                    device.save()
                    instance.start()
            elif device.machine_type == "cosec":
                cosec = COSECBiometric(
                    device.machine_ip,
                    device.port,
                    device.cosec_username,
                    device.cosec_password,
                    timeout=10,
                )
                response = cosec.basic_config()
                if response.get("app"):
                    device.is_live = True
                    device.is_scheduler = False
                    device.save()
                    thread = COSECBioAttendanceThread(device.id)
                    thread.start()
                    BIO_DEVICE_THREADS[device.id] = thread
                else:
                    raise TimeoutError
            else:
                pass

            script = """<script>
                    Swal.fire({
                      text: "The live capture mode has been activated successfully.",
                      icon: "success",
                      showConfirmButton: false,
                      timer: 1500,
                      timerProgressBar: true, // Show a progress bar as the timer counts down
                      didClose: () => {
                        location.reload(); // Reload the page after the SweetAlert is closed
                        },
                    });
                    </script>
                """
        except TimeoutError as error:
            device.is_live = False
            device.save()
            logger.error("An error comes in biometric_device_live", error)
            script = """
           <script>
                Swal.fire({
                  title : "Connection unsuccessful",
                  text: "Please double-check the accuracy of the provided IP Address and Port Number for correctness",
                  icon: "warning",
                  showConfirmButton: false,
                  timer: 3000,
                  timerProgressBar: true,
                  didClose: () => {
                    location.reload();
                    },
                });
            </script>
            """
        finally:
            if conn:
                conn.disconnect()
    else:
        device.is_live = False
        device.save()
        if device.machine_type == "cosec":
            existing_thread = BIO_DEVICE_THREADS.get(device.id)
            if existing_thread:
                existing_thread.stop()
                del BIO_DEVICE_THREADS[device.id]

        script = """
           <script>
                Swal.fire({
                  text: "The live capture mode has been deactivated successfully.",
                  icon: "warning",
                  showConfirmButton: false,
                  timer: 3000,
                  timerProgressBar: true,
                  didClose: () => {
                    location.reload();
                    },
                });
            </script>
            """
    return HttpResponse(script)


def zk_biometric_device_attendance(device_id):
    """
    Retrieve attendance records from a ZK biometric device and update the clock-in/clock-out status.

    :param device_id: The ID of the ZK biometric device.
    """
    device = BiometricDevices.objects.get(id=device_id)
    if device.is_scheduler:
        port_no = device.port
        machine_ip = device.machine_ip
        conn = None
        zk_device = ZK(
            machine_ip,
            port=port_no,
            timeout=5,
            password=int(device.zk_password),
            force_udp=False,
            ommit_ping=False,
        )
        try:
            conn = zk_device.connect()
            conn.enable_device()
            attendances = conn.get_attendance()
            last_attendance_datetime = attendances[-1].timestamp
            if device.last_fetch_date and device.last_fetch_time:
                filtered_attendances = [
                    attendance
                    for attendance in attendances
                    if attendance.timestamp.date() >= device.last_fetch_date
                    and attendance.timestamp.time() > device.last_fetch_time
                ]
            else:
                filtered_attendances = attendances
            device.last_fetch_date = last_attendance_datetime.date()
            device.last_fetch_time = last_attendance_datetime.time()
            device.save()
            for attendance in filtered_attendances:
                user_id = attendance.user_id
                punch_code = attendance.punch
                date_time = django_timezone.make_aware(attendance.timestamp)
                date = date_time.date()
                time = date_time.time()
                bio_id = BiometricEmployees.objects.filter(user_id=user_id).first()
                if bio_id:
                    request_data = Request(
                        user=bio_id.employee_id.employee_user_id,
                        date=date,
                        time=time,
                        datetime=date_time,
                    )
                    if punch_code in {0, 3, 4}:
                        try:
                            clock_in(request_data)
                        except Exception as error:
                            logger.error("Got an error : ", error)
                    else:
                        try:
                            clock_out(request_data)
                        except Exception as error:
                            logger.error("Got an error : ", error)
        except Exception as error:
            logger.error("Process terminate : ", error)
        finally:
            if conn:
                conn.disconnect()


def anviz_biometric_device_attendance(device_id):
    """
    Retrieves attendance records from an Anviz biometric device and processes them.

    :param device_id: The Object Id of the Anviz biometric device.
    """
    device = BiometricDevices.objects.get(id=device_id)
    if device.is_scheduler:
        anviz_device = AnvizBiometricDeviceManager(device_id)
        attendance_records = anviz_device.get_attendance_records()
        for attendance in attendance_records["payload"]["list"]:
            badge_id = attendance["employee"]["workno"]
            punch_code = attendance["checktype"]
            date_time_utc = datetime.strptime(
                attendance["checktime"], "%Y-%m-%dT%H:%M:%S%z"
            )
            date_time_obj = date_time_utc.astimezone(
                django_timezone.get_current_timezone()
            )
            employee = Employee.objects.filter(badge_id=badge_id).first()
            if employee:
                request_data = Request(
                    user=employee.employee_user_id,
                    date=date_time_obj.date(),
                    time=date_time_obj.time(),
                    datetime=date_time_obj,
                )
                if punch_code in {0, 128}:
                    try:
                        clock_in(request_data)
                    except Exception as error:
                        logger.error("Error in clock in ", error)
                else:
                    try:
                        # // 1 , 129 check type check out and door close
                        clock_out(request_data)
                    except Exception as error:
                        logger.error("Error in clock out ", error)


def cosec_biometric_device_attendance(device_id):
    """
    Retrieve and process attendance events from a COSEC biometric device.

    This function fetches attendance events from the specified COSEC biometric device
    and processes them to record clock-in and clock-out events for employees.

    Args:
        device_id (uuid): The ID of the COSEC biometric device.
    """
    device = BiometricDevices.objects.get(id=device_id)
    if not device.is_scheduler:
        return

    device_args = COSECAttendanceArguments.objects.filter(device_id=device).first()
    last_fetch_roll_ovr_count = (
        int(device_args.last_fetch_roll_ovr_count) if device_args else 0
    )
    last_fetch_seq_number = int(device_args.last_fetch_seq_number) if device_args else 1

    cosec = COSECBiometric(
        device.machine_ip,
        device.port,
        device.cosec_username,
        device.cosec_password,
        timeout=10,
    )
    attendances = cosec.get_attendance_events(
        last_fetch_roll_ovr_count, int(last_fetch_seq_number) + 1
    )

    if not isinstance(attendances, list):
        return

    for attendance in attendances:
        ref_user_id = attendance["detail-1"]
        employee = BiometricEmployees.objects.filter(ref_user_id=ref_user_id).first()
        if not employee:
            continue

        date_str = attendance["date"]
        time_str = attendance["time"]
        attendance_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        attendance_time = datetime.strptime(time_str, "%H:%M:%S").time()
        attendance_datetime = datetime.combine(attendance_date, attendance_time)
        punch_code = attendance["detail-2"]

        request_data = Request(
            user=employee.employee_id.employee_user_id,
            date=attendance_date,
            time=attendance_time,
            datetime=django_timezone.make_aware(attendance_datetime),
        )

        try:
            if punch_code in ["1", "3", "5", "7", "9", "0"]:
                clock_in(request_data)
            elif punch_code in ["2", "4", "6", "8", "10"]:
                clock_out(request_data)
            else:
                pass
        except Exception as error:
            logger.error("Error processing attendance: ", error)

    if attendances:
        last_attendance = attendances[-1]
        COSECAttendanceArguments.objects.update_or_create(
            device_id=device,
            defaults={
                "last_fetch_roll_ovr_count": last_attendance["roll-over-count"],
                "last_fetch_seq_number": last_attendance["seq-No"],
            },
        )


try:
    devices = BiometricDevices.objects.all().update(is_live=False)
    for device in BiometricDevices.objects.filter(is_scheduler=True):
        if device:
            if str_time_seconds(device.scheduler_duration) > 0:
                if device.machine_type == "anviz":
                    scheduler = BackgroundScheduler()
                    scheduler.add_job(
                        lambda: anviz_biometric_device_attendance(device.id),
                        "interval",
                        seconds=str_time_seconds(device.scheduler_duration),
                    )
                    scheduler.start()
                elif device.machine_type == "zk":
                    scheduler = BackgroundScheduler()
                    scheduler.add_job(
                        lambda: zk_biometric_device_attendance(device.id),
                        "interval",
                        seconds=str_time_seconds(device.scheduler_duration),
                    )
                    scheduler.start()
                elif device.machine_type == "cosec":
                    scheduler = BackgroundScheduler()
                    scheduler.add_job(
                        lambda: cosec_biometric_device_attendance(device.id),
                        "interval",
                        seconds=str_time_seconds(device.scheduler_duration),
                    )
                    scheduler.start()
                else:
                    pass
except:
    pass
