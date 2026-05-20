import calendar
import datetime as dt
import sys
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.relativedelta import relativedelta

today = datetime.now()


def recruitment_close():
    """
    Closes recruitment campaigns that have reached their end date.

    """
    from recruitment.models import Recruitment

    today_date = today.date()

    recruitments = Recruitment.objects.filter(closed=False)

    for rec in recruitments:
        if rec.end_date:
            if rec.end_date == today_date:
                rec.closed = True
                rec.is_published = False
                rec.save()


def candidate_convert():
    """
    Converts candidates to a "converted" state if they already exist as users.
    """
    from horilla_auth.models import HorillaUser
    from recruitment.models import Candidate

    mails = list(
        Candidate.objects.filter(is_active=True).values_list("email", flat=True)
    )
    existing_emails = list(
        HorillaUser.objects.filter(email__in=mails).values_list("email", flat=True)
    )
    Candidate.objects.filter(
        is_active=True,
        email__in=existing_emails,
        converted=False,
    ).update(converted=True)


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell"]
):
    """
    Initializes and starts background tasks using APScheduler when the server is running.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(candidate_convert, "interval", minutes=5)
    scheduler.add_job(recruitment_close, "interval", hours=1)

    scheduler.start()
