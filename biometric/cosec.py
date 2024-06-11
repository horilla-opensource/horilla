"""
This module provides a Python interface to interact with a COSEC biometric device.
It allows users to perform various operations such as configuring device settings,
managing users, retrieving attendance events, etc.
"""

import xml.etree.ElementTree as ET
from base64 import b64encode

import requests

cosec_api_response_codes = {
    "0": "Successful",
    "1": "Failed - Invalid Login Credentials",
    "2": "Date and time manual set failed",
    "3": "Invalid Date/Time",
    "4": "Maximum users are already configured.",
    "5": "Image size is too big.",
    "6": "Image format not supported",
    "7": "Card 1 and card 2 are identical",
    "8": "Card ID exists",
    "9": "Finger print template/ Palm template/ Face template\
        already exists/ Face Image already exists",
    "10": "No Record Found",
    "11": "Template size/ format mismatch",
    "12": "FP Memory full",
    "13": "User id not found",
    "14": "Credential limit reached",
    "15": "Reader mismatch/ Reader not configured",
    "16": "Device Busy",
    "17": "Internal process error ",
    "18": "PIN already exists",
    "19": "Credential not found",
    "20": "Memory Card Not Found",
    "21": "Reference User ID exists",
    "22": "Wrong Selection",
    "23": "Palm template mode mismatch",
    "24": "Feature not enabled in the configuration",
    "25": "Message already exists for same user for same date",
    "26": "Invalid smart card format/Parameters not applicable as per card type defined.",
    "27": "Time Out",
    "28": "Read/Write failed",
    "29": "Wrong Card Type",
    "30": "key mismatch",
    "31": "invalid card",
    "32": "Scan failed",
    "33": "Invalid value",
    "34": "Credential does not match",
    "35": "Failure",
    "36": "Face Not Detected",
    "37": "User Conflict",
    "38": "Enroll Conflict",
    "39": "Face Mask Detected",
    "40": "Full Face Not Visible",
    "41": "Face Not Straight",
}

true_false_arguments = [
    "enroll-on-device",
    "week-day0",
    "week-day1",
    "week-day2",
    "week-day3",
    "week-day4",
    "week-day5",
    "week-day6",
    "alarm",
    "tamper-alarm",
    "auto-alarm-ack",
    "thresh-temp-exceeded",
    "allow-exit-when-locked",
    "auto-relock",
    "asc-active",
    "door-sense-active",
    "exit-switch",
    "aux-output-enable",
    "greeting-msg-enable",
    "buzzer-mute",
    "enable",
    "enable-signal-wait",
    "read-csn",
]


class COSECBiometric:
    """
    A Python interface to interact with a COSEC biometric device.

    This class provides methods for configuring device settings, managing users,
    retrieving attendance events, and other operations.

    Usage:
        1. Instantiate the COSECBiometric class with the required parameters:
            IP address, port, username, and password.
        2. Use the provided methods to perform specific actions on the biometric device.
    """

    def __init__(self, machine_ip, port, username, password, timeout=60):
        """
        Initialize the COSECBiometric object with the specified parameters.

        Args:
            machine_ip (str): The IP address of the COSEC biometric device.
            port (int): The port number of the COSEC biometric device.
            username (str): The username for accessing the biometric device.
            password (str): The password for accessing the biometric device.
            timeout (int, optional): The timeout for HTTP requests (default is 60 seconds).
        """
        self.__ip = machine_ip
        self.__port = port
        self.__timeout = timeout
        self.__username = username
        self.__password = password
        self.__header = {"Authorization": self.__generate_auth_header()}
        self.__base_url = f"http://{self.__ip}/device.cgi"
        self.__user_fields = []

    def __generate_auth_header(self):
        """
        Generate the Authorization header for making authenticated requests to the COSEC
        biometric device.

        This method creates an Authorization header using the provided username and
        password, encoded in Base64 format as per the Basic authentication scheme.

        Returns:
            str: The Authorization header value in the format 'Basic <base64_encoded_credentials>'.
        """
        credentials = f"{self.__username}:{self.__password}".encode()
        return "Basic " + b64encode(credentials).decode()

    def __send_request(self, url):
        """
        This method sends an HTTP GET request to the specified URL with the
        appropriate headers, and then parses the response to handle different scenarios
        such as timeouts, access errors, unsupported content types, and valid responses.
        """
        try:
            response = requests.get(
                url + "&format=xml", headers=self.__header, timeout=self.__timeout
            )
            return self.__parse_response(response)
        except requests.Timeout:
            return {"Timeout": "Request Timeout"}

    def __parse_response(self, response):
        """
        Parse the response received from the COSEC biometric device.

        This method parses the HTTP response received from the COSEC biometric device,
        handles different scenarios such as HTTP status codes, content types,
        and response formats, and extracts relevant data from the response.

        Args:
            response (requests.Response): The HTTP response object received from
            the device.

        Returns:
            dict: A dictionary representing the parsed response. If the response status
            code is 200 (OK), and the content type is XML, the dictionary may contain
            response data. If there is an error or unsupported content, the dictionary
            will contain an appropriate error message.
        """
        if response.status_code != 200:
            return {"Error": "Access Error"}
        if response.headers.get("Content-Type") != "text/xml":
            return {"Error": "Unsupported content"}

        response_data = response.content.decode("utf-8")
        root = ET.fromstring(response_data)
        text_content = root.text.strip()
        if not text_content:
            events = root.findall("Events")
            if events:
                parsed_response = []
                for event in root.findall("Events"):
                    event_dict = {}
                    for elem in event:
                        event_dict[elem.tag] = elem.text
                    if event_dict.get("event-id") == "101":
                        parsed_response.append(event_dict)
            else:
                parsed_response = {elem.tag: elem.text for elem in root}
                if parsed_response.get("Response-Code"):
                    message = cosec_api_response_codes.get(
                        parsed_response["Response-Code"]
                    )
                    parsed_response["message"] = message
        else:
            parsed_response = {}
            parsed_response["error"] = text_content
        return parsed_response

    def __authenticate_arguments(self, url, kwargs):
        """
        Authenticate and validate the arguments before sending a request to the COSEC
        biometric device.

        This method verifies that the provided arguments are supported by the
        specified URL endpoint and raises a ValueError if any unsupported arguments
        are found.

        Args:
            url (str): The URL endpoint for the request.
            kwargs (dict): A dictionary containing the arguments to be authenticated.

        Raises:
            ValueError: If any of the provided arguments are not supported by the specified
                        URL endpoint.
        """
        if url == "special-function":
            url = f"{self.__base_url}/{url}?action=get&sp-fn-index=1"
        elif url == "smart-card-format":
            url = f"{self.__base_url}/{url}?action=get&card-type=1&index=1"
        else:
            url = f"{self.__base_url}/{url}?action=get"
        response = self.__send_request(url)
        supported_args = response.keys()
        unsupported_args = [arg for arg in kwargs.keys() if arg not in supported_args]

        if unsupported_args:
            unsupported_args_str = ", ".join(unsupported_args)
            raise ValueError(
                f"The following argument(s) are not supported\
                    : {unsupported_args_str}. Supported arguments are: {', '.join(supported_args)}"
            )

    def basic_config(self, action="get", **kwargs):
        """
        Configure or retrieve basic settings of the COSEC biometric device.

        This method allows the user to configure or retrieve basic settings of
        the COSEC biometric device, such as device name, IP settings, time settings,
        etc.
        """
        url = f"{self.__base_url}/device-basic-config?action={action}"

        if action == "set":
            self.__authenticate_arguments("device-basic-config", kwargs)
            url += "&" + "&".join([f"{key}={value}" for key, value in kwargs.items()])

        return self.__send_request(url)

    def finger_reader_parameter_configuration(self, action="get", **kwargs):
        """
        Configure or retrieve parameters related to the finger reader of the COSEC
        biometric device.

        This method allows the user to configure or retrieve parameters related to
        the finger reader of the COSEC biometric device, such as sensitivity, timeout,
        template format, etc.
        """
        url = f"{self.__base_url}/finger-parameter?action={action}"

        if action == "set":
            self.__authenticate_arguments("finger-parameter", kwargs)
            url += "&" + "&".join([f"{key}={value}" for key, value in kwargs.items()])

        return self.__send_request(url)

    def enrollment_configuration(self, action="get", **kwargs):
        """
        Configure or retrieve enrollment options of the COSEC biometric device.

        This method allows the user to configure or retrieve enrollment options
        of the COSEC biometric device, such as enabling or disabling self-enrollment,
        setting enrollment timeout, template format, etc.
        """
        url = f"{self.__base_url}/enroll-options?action={action}"

        if action == "set":
            self.__authenticate_arguments("enroll-options", kwargs)
            url += "&" + "&".join(
                [
                    f"{key}={int(value) if key in true_false_arguments else value}"
                    for key, value in kwargs.items()
                ]
            )

        return self.__send_request(url)

    def access_settings_configuration(self, action="get", **kwargs):
        """
        Configure or retrieve access settings of the COSEC biometric device.

        This method allows the user to configure or retrieve access settings of the
        COSEC biometric device, such as door access control, alarm settings,
        exit switches, etc
        """
        url = f"{self.__base_url}/access-setting?action={action}"

        if action == "set":
            self.__authenticate_arguments("access-setting", kwargs)
            url += "&" + "&".join(
                [
                    f"{key}={int(value) if key in true_false_arguments else value}"
                    for key, value in kwargs.items()
                ]
            )

        return self.__send_request(url)

    def alarm_configuration(self, action="get", **kwargs):
        """
        Configure or retrieve alarm settings of the COSEC biometric device.

        This method allows the user to configure or retrieve alarm settings of
        the COSEC biometric device, such as enabling or disabling alarms, setting
        alarm thresholds, configuring alarm acknowledgements, etc.
        """

        url = f"{self.__base_url}/alarm?action={action}"
        if action == "set":
            self.__authenticate_arguments("alarm", kwargs)
            url += "&" + "&".join(
                [
                    f"{key}={int(value) if key in true_false_arguments else value}"
                    for key, value in kwargs.items()
                ]
            )
        return self.__send_request(url)

    def date_and_time_configuration(self, action="get", **kwargs):
        """
        Configure or retrieve date and time settings of the COSEC biometric device.

        This method allows the user to configure or retrieve date and time settings
        of the COSEC biometric device, such as setting the current date and time,
        configuring time zones, enabling daylight saving time, etc.
        """
        url = f"{self.__base_url}/date-time?action={action}"
        if action == "set":
            self.__authenticate_arguments("date-time", kwargs)
            url += "&" + "&".join(
                [
                    f"{key}={int(value) if key in true_false_arguments else value}"
                    for key, value in kwargs.items()
                ]
            )
        return self.__send_request(url)

    def door_features_configuration(self, action="get", **kwargs):
        """
        Configure or retrieve door features settings of the COSEC biometric device.

        This method allows the user to configure or retrieve door features settings
        of the COSEC biometric device, such as enabling or disabling door senses,
        setting door open durations, configuring auxiliary outputs, etc.
        """
        url = f"{self.__base_url}/door-feature?action={action}"
        if action == "set":
            self.__authenticate_arguments("door-feature", kwargs)
            url += "&" + "&".join(
                [
                    f"{key}={int(value) if key in true_false_arguments else value}"
                    for key, value in kwargs.items()
                ]
            )
        return self.__send_request(url)

    def system_timer_configuration(self, action="get", **kwargs):
        """
        Configure or retrieve system timer settings of the COSEC biometric device.

        This method allows the user to configure or retrieve system timer settings
        of the COSEC biometric device, such as setting the system idle timeout,
        configuring system heartbeat intervals, etc.
        """
        url = f"{self.__base_url}/system-timer?action={action}"
        if action == "set":
            self.__authenticate_arguments("system-timer", kwargs)
            url += "&" + "&".join(
                [
                    f"{key}={int(value) if key in true_false_arguments else value}"
                    for key, value in kwargs.items()
                ]
            )
        return self.__send_request(url)

    def special_function_configuration(self, action="get", sp_fn_index="1", **kwargs):
        """
        Configure special functions on the COSEC biometric device.

        This method allows configuring special functions on the COSEC biometric device,
        such as enabling or disabling
        specific functionalities
        """
        url = f"{self.__base_url}/special-function?action={action}&sp-fn-index={sp_fn_index}"
        if action == "set":
            self.__authenticate_arguments("special-function", kwargs)
            url += "&" + "&".join(
                [
                    f"{key}={int(value) if key in true_false_arguments else value}"
                    for key, value in kwargs.items()
                ]
            )
        return self.__send_request(url)

    def wiegand_interface(self, action="get", **kwargs):
        """
        Configure or retrieve Wiegand interface settings of the COSEC biometric device.

        This method allows the user to configure or retrieve Wiegand interface settings
        of the COSEC biometric device,such as setting up Wiegand card readers, configuring
        Wiegand data formats, etc.
        """
        url = f"{self.__base_url}/wiegand-interface?action={action}"
        if action == "set":
            self.__authenticate_arguments("wiegand-interface", kwargs)
            url += "&" + "&".join(
                [
                    f"{key}={int(value) if key in true_false_arguments else value}"
                    for key, value in kwargs.items()
                ]
            )
        return self.__send_request(url)

    def smart_card_format(self, action="get", card_type="1", index="1", **kwargs):
        """
        Configure or retrieve smart card format settings of the COSEC biometric device.

        This method allows the user to configure or retrieve smart card format settings
        of the COSEC biometric device,
        such as setting up card types and their corresponding formats.
        """
        url = (
            f"{self.__base_url}/smart-card-format?action={action}"
            f"&card-type={card_type}&index={index}"
        )

        if action == "set":
            self.__authenticate_arguments("smart-card-format", kwargs)
            url += "&" + "&".join(
                [
                    f"{key}={int(value) if key in true_false_arguments else value}"
                    for key, value in kwargs.items()
                ]
            )
        return self.__send_request(url)

    def get_cosec_user(self, user_id):
        """
        Retrieve user information from the COSEC biometric device.

        This method retrieves user information, such as user details,
        credentials, and access rights, from the COSEC biometric device based
        on the provided user ID.
        """
        url = f"{self.__base_url}/users?action=get&user-id={user_id}"
        return self.__send_request(url)

    def check_user_url_arguments(self, user_id, url_arguments):
        """
        Check if the provided URL arguments are supported for the COSEC
        biometric device's user configuration.

        This method verifies if the provided URL arguments are supported
        for configuring or retrieving user settings on the COSEC biometric
        device. It compares the provided arguments with the supported fields
        retrieved from the device for user configuration.
        """
        user = self.get_cosec_user(user_id)
        if not user.get("Response-Code"):
            self.__user_fields = list(user.keys())

        else:
            ref_user_id = 1
            code = "13"
            while code != "0":
                url = (
                    f"{self.__base_url}/users?action=set&user-id={user_id}"
                    f"&ref-user-id={ref_user_id}&format=xml"
                )

                response = requests.get(
                    url, headers=self.__header, timeout=self.__timeout
                )
                if response.status_code == 200:
                    response_data = response.content.decode("utf-8")
                    root = ET.fromstring(response_data)
                    code = root.find("Response-Code").text
                    if code == "0":
                        user = self.get_cosec_user(user_id)
                        self.__user_fields = list(user.keys())
                        self.delete_cosec_user(user_id)
                        break
                    ref_user_id += 1
        fields = ""
        for arg in url_arguments:
            if arg.split("=")[0] not in self.__user_fields:
                fields += arg.split("=")[0] + " , "
        if fields:
            raise ValueError(
                f"{fields} argument is not support on this biometric device API"
            )

    def set_cosec_user(
        self,
        user_id,
        ref_user_id,
        name=None,
        user_active=None,
        vip=None,
        validity_enable=None,
        validity_time_hh=None,
        validity_time_mm=None,
        validity_date_dd=None,
        validity_date_mm=None,
        validity_date_yyyy=None,
        user_pin=None,
        card1=None,
        card2=None,
        by_pass_finger=None,
        dob_enable=None,
        dob_dd=None,
        dob_mm=None,
        dob_yyyy=None,
        by_pass_palm=None,
        user_group=None,
        self_enrollment_enable=None,
        enable_fr=None,
    ):
        """
        Set or update user information on the COSEC biometric device.

        This method allows setting or updating user information on the COSEC
        biometric device, including user details, access rights, credentials,
        validity periods, etc.
        """
        if not user_id or not ref_user_id:
            raise ValueError(
                "Both user_id and ref_id are mandatory for create & edit a user"
            )
        # user_id : Mandatory To set or retrieve the alphanumeric user ID for the selected user.
        # Note: If a set request is sent against an existing user ID, then configuration for this
        # user will be updated with the new values.
        # ref_user_id : Mandatory for the set action.Maximum 8 digits.To select the numeric user
        # ID on which the specified operation is to be done.
        url_arguments = []
        url = f"{self.__base_url}/users?action=set"
        url_arguments.append(f"user-id={user_id}")
        url_arguments.append(f"ref-user-id={ref_user_id}")

        if name:
            # Truncate name if it exceeds 15 characters
            truncated_name = name[:15] if len(name) > 15 else name
            url_arguments.append(f"name={truncated_name}")

        if user_active is not None:
            # To activate or deactivate a user.
            if user_active not in [True, False]:
                raise ValueError("user_active must be either True, False, or None")
            url_arguments.append(f"user-active={int(user_active)}")

        if vip is not None:
            # To define a user as VIP.
            # Note: A VIP user is a user with the special privilege to access a particular door.
            if vip not in [True, False]:
                raise ValueError("vip must be either True, False, or None")
            url_arguments.append(f"vip={int(vip)}")

        if validity_enable is not None:
            # To enable/disable the user validity.
            if validity_enable not in [True, False]:
                raise ValueError("validity_enable must be either True, False, or None")
            url_arguments.append(f"validity-enable={int(validity_enable)}")

        if validity_date_dd and validity_date_mm and validity_date_yyyy:
            # To define the end date for user validity.Valid Values : validity_date_dd = 1-31 &
            # validity_date_mm = 1-12 validity_date_yyyy = based on device model
            url_arguments.append(f"validity-date-dd={validity_date_dd}")
            url_arguments.append(f"validity-date-mm={validity_date_mm}")
            url_arguments.append(f"validity-date-yyyy={validity_date_yyyy}")

        if validity_time_hh and validity_time_mm:
            # To define the end time for user validity.Valid Values : validity_time_hh = 00-23
            # & validity_time_mm = 00-59
            url_arguments.append(f"validity-time-hh={validity_time_hh}")
            url_arguments.append(f"validity-time-mm={validity_time_mm}")

        if user_pin:
            # 1 to 6 Digits . To set the user PIN or get the event from user PIN.
            # Note: The user-pin can be set to a blank value.
            url_arguments.append(f"user-pin={user_pin}")

        if by_pass_finger is not None:
            # To enable/disable the bypass finger option.
            url_arguments.append(f"by-pass-finger={by_pass_finger}")

        if by_pass_palm is not None:
            # To enable/disable the bypass palm option.
            if by_pass_palm not in [True, False]:
                raise ValueError("by_pass_palm must be either True, False, or None")
            url_arguments.append(f"by-pass-palm={int(by_pass_palm)}")

        if card1:
            # Values : 64 Bits (8 bytes) (max value - 18446744073709551615).
            # Defines the value of access card 1 and 2.
            url_arguments.append(f"card1={card1}")
        if card2:
            url_arguments.append(f"card2={card2}")

        if dob_enable is not None:
            # To enable/disable the display of a birthday message.
            if dob_enable not in [True, False]:
                raise ValueError("dob_enable must be either True, False, or None")
            url_arguments.append(f"dob-enable={int(dob_enable)}")

        if dob_dd and dob_mm and dob_yyyy:
            # To set or delete the date of birth for a user Valid Values :
            # dob_dd = 1-31 & dob_mm = 1-12 dob_yyyy = 1990-2037
            url_arguments.append(f"dob-dd={dob_dd}")
            url_arguments.append(f"dob-mm={dob_mm}")
            url_arguments.append(f"dob-yyyy={dob_yyyy}")

        if user_group:
            # To set the user group number.
            # Note: A user can be assigned to any user group ranging from 1 to 999.
            #       User group number can be set/update via “Set” action.
            #       To remove a user from an assigned user group, user group should be set to 0.
            url_arguments.append(f"user-group={user_group}")

        if self_enrollment_enable is not None:
            # To enable/disable self-enrollment for user
            if self_enrollment_enable not in [True, False]:
                raise ValueError(
                    "self_enrollment_enable must be either True, False, or None"
                )
            url_arguments.append(
                f"self-enrollment-enable={int(self_enrollment_enable)}"
            )

        if enable_fr is not None:
            # To enable/disable face recognition for a user
            if enable_fr not in [True, False]:
                raise ValueError("enable_fr must be either True, False, or None")
            url_arguments.append(f"enable-fr={int(enable_fr)}")
        self.check_user_url_arguments(user_id, url_arguments)
        url += "&" + "&".join(url_arguments)
        return self.__send_request(url)

    def delete_cosec_user(self, user_id):
        """
        Delete a user from the COSEC biometric device.

        This method deletes a user with the specified user ID from the COSEC
        biometric device.
        """
        url = f"{self.__base_url}/users?action=delete&user-id={user_id}"
        return self.__send_request(url)

    def enable_user_face_recognition(self, user_id, enable_fr=True):
        """
        Enable or disable face recognition for a user in cosec biometric device.
        """
        url = (
            f"{self.__base_url}/users?action=set&user-id={user_id}"
            f"&enable-fr={int(enable_fr)}&format=xml"
        )
        return self.__send_request(url)

    def get_user_credential(self, user_id, credential_type=1, finger_index=1):
        """
        Retrieve the credential of a user from the COSEC biometric device.

        This method retrieves the credential of a user, such as fingerprint,
        card, palm template, face template, or face image, from the COSEC biometric
        device based on the provided user ID
        and credential type.
        """
        # type values: 1 = Finger , 2 = Card , 3 = Palm , 4 = Palm template with
        # guide mode , 5 = Face Template , 6 = Face Image
        if not isinstance(credential_type, int) or not isinstance(finger_index, int):
            raise ValueError("type and finger_index arguments value must be integers")

        if credential_type < 1 or credential_type > 6:
            raise ValueError("Type must be between 1 and 6")

        if finger_index < 1 or finger_index > 10:
            raise ValueError("Finger index must be between 1 and 10")

        url = (
            f"{self.__base_url}/credential?action=get&type={credential_type}"
            f"&user-id={user_id}&finger-index={finger_index}"
        )
        return self.__send_request(url)

    def get_user_credential_count(self, user_id):
        """
        Retrieve the credential of a user from the COSEC biometric device.

        This method retrieves the count of credentials of a user, such as fingerprint,
        card, palm template, face template, or face image, from the COSEC biometric
        device based on the provided user ID
        and credential type.
        """
        url = f"{self.__base_url}/command?action=getcount&user-id={user_id}"
        return self.__send_request(url)

    def delete_cosec_user_credential(self, user_id, credential_type):
        """
        Delete a specific type of credential associated
        with a user from the COSEC biometric device.

        This method deletes a specific type of credential
        associated with a user, such as fingerprint,
        card, palm template, face template, or face image,
        from the COSEC biometric device.
        """
        # type values: 0 = All , 1 = Finger , 2 = Card , 3 = Palm , 4 = Palm template
        # with guide mode , 5 = Face Template , 6 = Face Image
        # type= 5 and 6 are applicable only for ARGO FACE.
        if type < 0 or type > 6:
            raise ValueError("Type must be between 0 and 6")
        url = f"{self.__base_url}/credential?action=delete&user-id={user_id}&type={credential_type}"
        return self.__send_request(url)

    def get_user_count(self):
        """
        Retrieve the total number of users configured on the COSEC biometric device.

        This method retrieves the total number of users configured on the COSEC biometric device.
        """
        url = f"{self.__base_url}/command?action=getusercount"
        return self.__send_request(url)

    def get_attendance_events(self, roll_over_count=0, seq_num=1, no_of_events=100):
        """
        Retrieve attendance events from the COSEC biometric device.

        This method retrieves attendance events, such as punch-in and punch-out records,
        from the COSEC biometric device.
        """
        url = (
            f"{self.__base_url}/events?action=getevent&roll-over-count={roll_over_count}"
            f"&seq-number={seq_num}&no-of-events={no_of_events}"
        )
        return self.__send_request(url)
