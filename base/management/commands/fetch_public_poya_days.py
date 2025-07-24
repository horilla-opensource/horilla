from django.core.management.base import BaseCommand
from googleapiclient.discovery import build
from datetime import datetime, date
import os

from base.models import Holidays

API_KEY = os.getenv("GOOGLE_CALENDAR_API_KEY")
CALENDAR_ID = "en.lk#holiday@group.v.calendar.google.com"

class Command(BaseCommand):
    help = "Fetch Poya holidays from Google Calendar and store in Holidays model"

    def handle(self, *args, **kwargs):
        if not API_KEY:
            self.stdout.write(self.style.ERROR("Missing GOOGLE_CALENDAR_API_KEY in environment variables."))
            return

        try:
            service = build("calendar", "v3", developerKey=API_KEY)

            current_year = date.today().year
            start_of_year = datetime(current_year, 1, 1).isoformat() + 'Z'
            end_of_year = datetime(current_year, 12, 31, 23, 59, 59).isoformat() + 'Z'

            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start_of_year,
                timeMax=end_of_year,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            count_created = 0
            for event in events:
                name = event.get('summary', '')
                date_str = event.get('start', {}).get('date')

                if "Poya" in name and date_str and name != 'Day after Vesak Full Moon Poya Day':
                    holiday_date = datetime.strptime(date_str, "%Y-%m-%d").date()


                    if not Holidays.objects.filter(name=name, start_date=holiday_date).exists():
                        Holidays.objects.create(
                            name=name,
                            start_date=holiday_date,
                            end_date=holiday_date,
                            recurring=False,
                            company_id=None,
                            is_poya_holiday=True,
                        )
                        count_created += 1

            if count_created == 0:
                self.stdout.write(self.style.WARNING("No new Poya holidays were added."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Added {count_created} Poya holidays for {current_year}."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error fetching holidays: {str(e)}"))
