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


scheduler = BackgroundScheduler()
scheduler.add_job(recruitment_close, "interval", hours=1)

scheduler.start()
