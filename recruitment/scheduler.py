import calendar
import datetime as dt
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.relativedelta import relativedelta

today = datetime.now()


def recruitment_close():

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

    from django.contrib.auth.models import User

    from recruitment.models import Candidate

    candidates = Candidate.objects.filter(is_active=True)
    mails = list(Candidate.objects.values_list("email", flat=True))
    existing_emails = list(
        User.objects.filter(username__in=mails).values_list("email", flat=True)
    )
    for cand in candidates:
        if cand.email in existing_emails:
            cand.converted = True
            cand.save()


scheduler = BackgroundScheduler()
scheduler.add_job(candidate_convert, "interval", seconds=10)
scheduler.add_job(recruitment_close, "interval", hours=1)

scheduler.start()
