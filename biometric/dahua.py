"""
DahuaAPI module for interacting with Dahua biometric and access control devices.

This module provides a set of methods for managing and configuring Dahua devices,
including retrieving system information, managing users, setting up network configurations,
and interacting with attendance logs. It communicates with Dahua devices via HTTP requests
and supports basic operations such as system reboot, setting time, and language configuration.
"""

import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict

import requests
from requests.auth import HTTPDigestAuth

key_map = {
    "AttendanceState": "attendance_state",
    "CardID": "card_id",
    "CardName": "card_name",
    "CardNo": "card_no",
    "CardType": "card_type",
    "CreateTime": "create_time",
    "CreateTimeRealUTC": "create_time_real_utc",
    "Door": "door",
    "ErrorCode": "error_code",
    "FaceIndex": "face_index",
    "FacilityCode": "facility_code",
    "HatColor": "hat_color",
    "HatType": "hat_type",
    "Mask": "mask",
    "Method": "method",
    "Notes": "notes",
    "Password": "password",
    "ReaderID": "reader_id",
    "RecNo": "rec_no",
    "RemainingTimes": "remaining_times",
    "ReservedInt": "reserved_int",
    "ReservedString": "reserved_string",
    "RoomNumber": "room_number",
    "Status": "status",
    "Type": "type",
    "URL": "url",
    "UserID": "user_id",
    "UserType": "user_type",
    "VTONumber": "vto_number",
}


def convert_logs_to_list(logs):
    """
    Converts a dictionary of logs into a list of records.

    This function processes a dictionary containing log data, identifies records by
    the keys starting with "records[", and converts the corresponding values into
    a list of dictionaries with more readable keys. It also handles timestamp fields
    by converting them to `datetime` objects.

    Args:
        logs (dict): The dictionary containing the log data to be converted.

    Returns:
        list: A list of dictionaries representing individual log records, with
              formatted keys and values. Each record is a dictionary with keys
              mapped according to the `key_map` and timestamps converted to `datetime`.
    """
    records_list = []
    record_dict = defaultdict(dict)
    previous_key = None

    for key, value in logs.items():
        if key.startswith("records["):
            parts = key.split(".")
            current_key = parts[0]

            if previous_key and previous_key != current_key:
                records_list.append(dict(record_dict))
                record_dict.clear()
            time_keys = ["CreateTime", "CreateTimeRealUTC"]
            if parts[-1] in time_keys:
                value = datetime.fromtimestamp(int(value))

            record_dict[key_map.get(parts[-1])] = value
            previous_key = current_key
    if record_dict:
        records_list.append(dict(record_dict))

    return records_list


class DahuaAPI:
    """
    A class for interacting with Dahua biometric and access control devices.

    This class provides methods to interact with Dahua devices, including retrieving
    system information, configuring device settings (network, language, general, etc.),
    managing users, and processing logs related to attendance and access control.
    The class communicates with the Dahua device via HTTP requests and supports
    actions like enrolling users, rebooting the device, and fetching various device logs.
    """

    def __init__(self, ip: str, username: str, password: str):
        # self.base_url = f"http://{ip}/cgi-bin/"
        self.base_url = f"{ip}/cgi-bin/"
        self.auth = HTTPDigestAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth

    def parse_response(self, response):
        """
        Parses the response from the Dahua API request.

        This method processes the HTTP response from the Dahua device API. It decodes
        the content of the response, checks the status code, and returns a structured
        result. If the response is successful (status code 200), it attempts to parse
        the content as a dictionary of key-value pairs. If the response is an error,
        it returns a relevant error message
        """
        content = response.content.decode("utf-8").strip()
        status_code = response.status_code

        if status_code == 200:
            if "\r\n" not in content and "=" not in content:
                return {"result": content, "status_code": status_code}

            try:
                content_dict = dict(
                    line.split("=", 1) for line in content.split("\r\n") if "=" in line
                )
                content_dict["status_code"] = status_code
                return content_dict
            except Exception:
                return {
                    "result": f"Invalid parameter {content}",
                    "status_code": status_code,
                }

        if status_code == 400:
            return {
                "result": "Error: Bad Request. Check the parameters.",
                "status_code": status_code,
            }

        return {"result": content, "status_code": status_code}

    def _get(self, endpoint: str, params: Dict[str, Any] = None):
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, params=params)
        return self.parse_response(response)

    def _post(self, endpoint: str, data: Dict[str, Any]):
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, data=data)
        return self.parse_response(response)

    def get_system_info(self):
        """Get system information."""
        endpoint = "magicBox.cgi?action=getSystemInfo"
        return self._get(endpoint)

    def get_serial_number(self):
        """Get the device serial number."""
        endpoint = "magicBox.cgi?action=getSerialNo"
        return self._get(endpoint)

    def get_hardware_version(self):
        """Get the hardware version."""
        endpoint = "magicBox.cgi?action=getHardwareVersion"
        return self._get(endpoint)

    def get_device_type(self):
        """Get the device type."""
        endpoint = "magicBox.cgi?action=getDeviceType"
        return self._get(endpoint)

    def get_basic_config(self):
        """i"""
        endpoint = "configManager.cgi?action=getConfig&name=Network"
        return self._get(endpoint)

    def set_basic_config(self, params: Dict[str, Any]):
        """Set basic network configuration."""
        endpoint = "configManager.cgi?action=setConfig"
        return self._post(endpoint, data=params)

    def get_general_config(self):
        """Get general system configuration."""
        endpoint = "configManager.cgi?action=getConfig&name=General"
        return self._get(endpoint)

    def set_general_config(self, params: Dict[str, Any]):
        """Set general system configuration."""
        endpoint = "configManager.cgi?action=setConfig"
        return self._get(endpoint, params=params)

    def get_system_time(self):
        """Get the current system time."""
        endpoint = "global.cgi?action=getCurrentTime"
        return self._get(endpoint)

    def set_system_time(self, date: str, time: str):
        """
        Set the system time.
        Date format : YYYY-MM-DD
        Time format : HH-MM-SS
        Combines date and time with %20 between them.
        %20 character used for add space
        """
        # Validate the date format (YYYY-MM-DD)
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(date_pattern, date):
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

        # Validate the time format (HH:MM:SS)
        time_pattern = r"^\d{2}:\d{2}:\d{2}$"
        if not re.match(time_pattern, time):
            raise ValueError("Invalid time format. Expected HH:MM:SS.")

        device_datetime = f"{date}%20{time}"
        endpoint = f"global.cgi?action=setCurrentTime&time={device_datetime}"

        return self._get(endpoint)

    def reboot_device(self):
        """Reboot the device."""
        endpoint = "configManager.cgi?action=reboot"
        return self._post(endpoint, data={})

    def shutdown_device(self):
        """Shut down the device."""
        endpoint = "configManager.cgi?action=shutdown"
        return self._post(endpoint, data={})

    def get_language_caps(self):
        """Get supported language capabilities."""
        endpoint = "magicBox.cgi?action=getLanguageCaps"
        return self._get(endpoint)

    def get_language_config(self):
        """Get current language configuration."""
        endpoint = "magicBox.cgi?action=getLanguageConfig"
        return self._get(endpoint)

    def set_language_config(self, language: str):
        """Set the device language."""
        endpoint = "magicBox.cgi?action=setLanguageConfig"
        data = {"Language": language}
        return self._post(endpoint, data=data)

    def get_locales_config(self):
        """Get current locales configuration."""
        endpoint = "magicBox.cgi?action=getLocalesConfig"
        return self._get(endpoint)

    def set_locales_config(self, params: Dict[str, Any]):
        """Set locales configuration."""
        endpoint = "magicBox.cgi?action=setLocalesConfig"
        return self._post(endpoint, data=params)

    def get_group_info(self, name):
        """
        Retrieves information about a specific user group.
        """
        if not name:
            raise ValueError("The 'name' parameter is required and cannot be empty.")
        endpoint = f"userManager.cgi?action=getGroupInfoAll&name={name}"
        return self._get(endpoint)

    def get_group_info_all(self):
        """
        Retrieves information about all user groups.
        """
        endpoint = "userManager.cgi?action=getGroupInfoAll"
        return self._get(endpoint)

    def enroll_new_user(
        self,
        card_name: str,
        card_no: str,
        user_id: str,
        card_status: int = 0,
        card_type: int = 0,
        password: str = "",
        doors: list[int] = None,
        time_sections: list[int] = None,
        vto_position: str = "",
        valid_date_start: str = "",
        valid_date_end: str = "",
        is_valid: bool = True,
    ):
        """
        Enroll a new user with access control card details.

        Args:
            card_name (str): Card name, up to 32 characters.
            card_no (str): Card number,Must be unique.
            user_id (str): User ID,Must be unique..
            card_status (int): Card status, default is 0 (Normal).
            card_type (int): Card type, default is 0 (Ordinary card).
            password (str): Card password (default is an empty string).
            doors (list[int]): Door permissions (default is None).
            time_sections (list[int]): Time sections corresponding to
                                        door permissions (default is None).
            vto_position (str): Door number linked with indoor monitor (default is an empty string).
            valid_date_start (str): Start time of the validity period,
                                    format "yyyyMMdd hhmmss" (default is an empty string).
            valid_date_end (str): End time of the validity period,
                                    format "yyyyMMdd hhmmss" (default is an empty string).
            is_valid (bool): Validity of the card, default is True.

        Returns:
            Response from the server.
        """
        endpoint = "recordUpdater.cgi?action=insert&name=AccessControlCard"
        endpoint += f"&CardName={card_name}"
        endpoint += f"&CardNo={card_no}"
        endpoint += f"&UserID={user_id}"
        endpoint += f"&CardStatus={card_status}"
        endpoint += f"&CardType={card_type}"

        if password:
            endpoint += f"&Password={password}"
        if doors:
            for index, door in enumerate(doors):
                endpoint += f"&Doors[{index}]={door}"
        if time_sections:
            for index, section in enumerate(time_sections):
                endpoint += f"&TimeSections[{index}]={section}"
        if vto_position:
            endpoint += f"&VTOPosition={vto_position}"
        if valid_date_start:
            endpoint += f"&ValidDateStart={valid_date_start}"
        if valid_date_end:
            endpoint += f"&ValidDateEnd={valid_date_end}"
        endpoint += f"&IsValid={'true' if is_valid else 'false'}"

        return self._get(endpoint)

    def get_user_info_all(self):
        """
        Retrieves information about all users.
        """
        endpoint = "userManager.cgi?action=getUserInfoAll"
        return self._get(endpoint)

    def get_user_info(self, username: str):
        """
        Retrieves information about a specific user.
        """
        if not username:
            raise ValueError("The 'name' parameter is required and cannot be empty.")
        endpoint = f"userManager.cgi?action=getUserInfo&name={username}"
        return self._get(endpoint)

    def add_user(
        self,
        username: str,
        password: str,
        group: str,
        sharable: bool,
        reserved: bool,
        memo: str = "",
    ):
        """
        Add a new user.

        Args:
            username (str): The username of the new user.
            password (str): The password for the new user.
            group (str): The group of the new user, either "admin" or "user".
            sharable (bool): Whether the user can have multi-point login.
            reserved (bool): Whether the user is reserved and cannot be deleted.
            memo (str): An optional memo for the user.

        Returns:
            Response from the server.
        """
        all_groups_info = self.get_group_info_all()
        name_list = [
            value for key, value in all_groups_info.items() if key.endswith(".Name")
        ]
        if group not in name_list:
            raise ValueError(f"Invalid group. It must be comes in {name_list}.")

        endpoint = (
            f"userManager.cgi?action=addUser&"
            f"user.Name={username}&"
            f"user.Password={password}&"
            f"user.Group={group}&"
            f"user.Sharable={'true' if sharable else 'false'}&"
            f"user.Reserved={'true' if reserved else 'false'}&"
            f"user.Memo={memo}"
        )

        return self._get(endpoint)

    def delete_user(self, username: str):
        """Delete an existing user."""
        endpoint = f"userManager.cgi?action=deleteUser&name={username}"
        return self._get(endpoint)

    def fetch_attendance_logs(self):
        """Fetch attendance logs using the API."""
        endpoint = "log.cgi?action=doFind"
        params = {
            "name": "AttendanceLog",
            "SessionID": "session-id",
            "count": 100,
            "offset": 0,
        }
        return self._get(endpoint, params=params)

    def get_logs(self, log_type: str = "SystemLog"):
        """Fetch logs from the device."""
        endpoint = "log.cgi?action=doFind"
        params = {
            "name": log_type,
            "SessionID": "session-id",
            "count": 100,
            "offset": 0,
        }
        return self._get(endpoint, params=params)

    def get_record_config(self):
        """Get record configuration."""
        endpoint = "configManager.cgi?action=getConfig&name=Record"
        return self._get(endpoint)

    def set_record_config(self, params: Dict[str, Any]):
        """Set record configuration."""
        endpoint = "configManager.cgi?action=setConfig"
        return self._post(endpoint, data=params)

    def get_record_mode_config(self):
        """Get record mode configuration."""
        endpoint = "configManager.cgi?action=getConfig&name=RecordMode"
        return self._get(endpoint)

    def set_record_mode_config(self, params: Dict[str, Any]):
        """Set record mode configuration."""
        endpoint = "configManager.cgi?action=setConfig"
        return self._post(endpoint, data=params)

    def get_snapshot_config(self):
        """Get snapshot configuration."""
        endpoint = "configManager.cgi?action=getConfig&name=Snap"
        return self._get(endpoint)

    def set_snapshot_config(self, params: Dict[str, Any]):
        """Set snapshot configuration."""
        endpoint = "configManager.cgi?action=setConfig"
        return self._post(endpoint, data=params)

    def get_control_card_rec(
        self,
        card_no: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
    ):
        """
        Get offline records from device.
        start_time and end_time must be Python datetime objects, used to convert to Unix timestamp.
        """
        endpoint = "recordFinder.cgi?action=find&name=AccessControlCardRec"

        if start_time:
            if isinstance(start_time, datetime):
                start_time = int(start_time.timestamp())
            else:
                raise ValueError("start_time must be a Python datetime object")

        if end_time:
            if isinstance(end_time, datetime):
                end_time = int(end_time.timestamp())
            else:
                raise ValueError("end_time must be a Python datetime object")

        if card_no:
            endpoint += f"&condition.CardNo={card_no}"
        if start_time:
            endpoint += f"&StartTime={start_time}"
        if end_time:
            endpoint += f"&EndTime={end_time}"

        card_records = self._get(endpoint)

        records = convert_logs_to_list(card_records)
        logs = {
            "records": records,
            "found": card_records.get("found"),
            "status_code": card_records.get("status_code"),
        }

        return logs


# Example usage
# dahua = DahuaAPI(ip="192.168.100.195", username="admin", password="User@123")
# result = dahua.get_system_time()
# result1 = dahua.get_control_card_rec(start_time="1736418923")
# result1 = dahua.get_snapshot_config()
# result1 = dahua.delete_user(username="TestUser")
# result2 = dahua.get_user_info_all()
# result = dahua.get_user_info(name="TestUser")
# result1 = dahua.add_user(
#     username="TestUser",
#     password="Test@!12",
#     group="admin",
#     sharable=True,
#     reserved=False,
#     memo="TestUser Group",
# )
# response = dahua.enroll_new_user(
#     card_name="Nikhil Ravi",  # Card name
#     card_no="987564",  # Card number
#     user_id="CTS437",  # User ID
#     card_status=0,  # Card status (Normal)
#     card_type=0,  # Card type (Ordinary card)
#     password="Nikh@!12",  # Password for card + password
# )
