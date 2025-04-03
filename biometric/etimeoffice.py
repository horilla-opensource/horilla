from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth


class ETimeOfficeAPI:
    def __init__(self, username, password, base_url="https://api.etimeoffice.com/api/"):
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip("/") + "/"

    def _is_valid_date(self, date_str, with_time=True):
        try:
            if with_time:
                datetime.strptime(date_str, "%d/%m/%Y_%H:%M")
            else:
                datetime.strptime(date_str, "%d/%m/%Y")
            return True
        except ValueError:
            return False

    def _convert_punch_dates(self, response_data):
        if not response_data.get("Error", True):
            if "PunchData" in response_data:
                for punch in response_data["PunchData"]:
                    try:
                        punch["PunchDate"] = datetime.strptime(
                            punch["PunchDate"], "%d/%m/%Y %H:%M:%S"
                        )
                    except ValueError:
                        pass
            if "InOutPunchData" in response_data:
                for punch in response_data["InOutPunchData"]:
                    try:
                        punch["DateString"] = datetime.strptime(
                            punch["DateString"], "%d/%m/%Y"
                        ).date()
                    except ValueError:
                        pass
                    try:
                        punch["INTime"] = datetime.strptime(
                            punch["INTime"], "%H:%M"
                        ).time()
                    except:
                        pass
                    try:
                        punch["OUTTime"] = datetime.strptime(
                            punch["OUTTime"], "%H:%M"
                        ).time()
                    except:
                        pass
        return response_data

    def _fetch_data(self, endpoint, emp_code, from_date, to_date, with_time=True):
        if not (
            self._is_valid_date(from_date, with_time)
            and self._is_valid_date(to_date, with_time)
        ):
            return {
                "Error": True,
                "Msg": "Error: Invalid date format. Expected format: "
                + ("DD/MM/YYYY_HH:MM" if with_time else "DD/MM/YYYY"),
            }

        url = f"{self.base_url}{endpoint}?Empcode={emp_code}&FromDate={from_date}&ToDate={to_date}"
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))
        return self._convert_punch_dates(response.json())

    def download_punch_data(self, from_date, to_date, emp_code="ALL"):
        return self._fetch_data(
            "DownloadPunchData", emp_code, from_date, to_date, with_time=True
        )

    def download_punch_data_mcid(self, from_date, to_date, emp_code="ALL"):
        return self._fetch_data(
            "DownloadPunchDataMCID", emp_code, from_date, to_date, with_time=True
        )

    def download_in_out_punch_data(self, from_date, to_date, emp_code="ALL"):
        return self._fetch_data(
            "DownloadInOutPunchData", emp_code, from_date, to_date, with_time=False
        )


# api = ETimeOfficeAPI(username={corporateid}:{usename}:{password}:true",password="")
# response = api.download_punch_data(from_date="25/03/2025_00:00",to_date="25/03/2025_12:22")
