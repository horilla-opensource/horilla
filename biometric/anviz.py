"""
CrossChexCloudAPI module for Anviz Biometric Integration

This module provides a wrapper for interacting with the CrossChex Cloud API to manage
authentication, attendance data retrieval, and token handling. It allows for secure
communication with the API, including fetching and validating tokens, and retrieving
attendance records .
"""

from datetime import datetime

import requests


class CrossChexCloudAPI:
    """
    CrossChexCloudAPI: A class to interact with the CrossChex Cloud API for attendance data
    and token management.
    """

    def __init__(self, api_url, api_key, api_secret, anviz_request_id):
        """
        Initializes the CrossChexCloudAPI object with necessary parameters, such as API URL,
        credentials (API key and secret), and request ID for the connection.
        """
        self.api_url = api_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.anviz_request_id = anviz_request_id
        self.token = None
        self.expires = None
        self.auth_error = {
            "header": {"nameSpace": "System", "name": "Exception"},
            "payload": {"type": "AUTH_ERROR", "message": "AUTH_ERROR"},
        }
        self.expires_error = {
            "header": {"nameSpace": "System", "name": "Exception"},
            "payload": {"type": "TOKEN_EXPIRES", "message": "TOKEN_EXPIRES"},
        }

    def _get_timestamp(self):
        """
        Generates a UTC timestamp in ISO 8601 format.
        """
        return datetime.utcnow().isoformat() + "Z"

    def _post(self, data):
        """
        Sends a POST request with the given data to the API and handles the response, including
        automatic token renewal in case of expiration or authentication error.
        """
        response = requests.post(self.api_url, json=data, timeout=5)
        response_data = response.json()

        if "payload" in response_data:
            if response_data["payload"] == self.expires_error:
                self.get_token()
                response = requests.post(self.api_url, json=data, timeout=5)
                response_data = response.json()
            elif response_data["payload"] == self.auth_error:
                raise Exception("Authentication error: API key or secret is incorrect.")

        response.raise_for_status()
        return response_data

    def _is_token_expired(self):
        """Check if the token is expired."""
        if self.expires:
            expires_datetime = datetime.fromisoformat(self.expires)
            # Remove timezone info to make it offset-naive
            expires_datetime = expires_datetime.replace(tzinfo=None)
            return datetime.utcnow() > expires_datetime
        return True

    def get_token(self):
        """Fetch a new token if expired or not present, and store it in the database."""
        if self.token is None or self._is_token_expired():
            data = {
                "header": {
                    "nameSpace": "authorize.token",
                    "nameAction": "token",
                    "version": "1.0",
                    "requestId": self.anviz_request_id,
                    "timestamp": self._get_timestamp(),
                },
                "payload": {"api_key": self.api_key, "api_secret": self.api_secret},
            }
            response = self._post(data)
            self.token = response.get("payload").get("token")
            self.expires = response.get("payload").get("expires")

        return self.token, self.expires

    def test_connection(self):
        """Test connection and fetch the token and expiry."""
        token, expires = self.get_token()
        return {"token": token, "expires": expires}

    def get_attendance_payload(
        self, begin_time, end_time, order, page, per_page, token
    ):
        """Constructs the payload for retrieving attendance records."""
        current_utc_time = datetime.utcnow()
        begin_time = begin_time or current_utc_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_time = end_time or current_utc_time
        begin_time_str = begin_time.isoformat() + "+00:00"
        end_time_str = end_time.isoformat() + "+00:00"
        return {
            "header": {
                "nameSpace": "attendance.record",
                "nameAction": "getrecord",
                "version": "1.0",
                "requestId": self.anviz_request_id,
                "timestamp": self._get_timestamp(),
            },
            "authorize": {
                "type": "token",
                "token": token,
            },
            "payload": {
                "begin_time": begin_time_str,
                "end_time": end_time_str,
                "order": order,
                "page": page,
                "per_page": per_page,
            },
        }

    def get_attendance_records(
        self,
        begin_time=None,
        end_time=None,
        order="asc",
        page=1,
        per_page=100,
        token=None,
    ):
        """Get attendance records, optimizing token usage and handling pagination."""
        all_records = []
        token = token or self.get_token()[0]

        while True:
            payload_data = self.get_attendance_payload(
                begin_time=begin_time,
                end_time=end_time,
                order=order,
                page=str(page),
                per_page=str(per_page),
                token=token,
            )
            response = self._post(payload_data)

            records = response["payload"]["list"]
            all_records.extend(records)

            page_count = response["payload"]["pageCount"]
            if page >= page_count:
                break

            page += 1

        return {
            "token": self.token,
            "expires": self.expires,
            "list": all_records,
            "count": len(all_records),
        }
