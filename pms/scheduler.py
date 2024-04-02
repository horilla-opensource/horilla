from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from notifications.signals import notify


def cyclic_feedback_creation():
    from pms.models import Feedback
    
    try:
        feedbacks = Feedback.objects.filter(
            cyclic_next_start_date=datetime.today().date()
        )
        for feedback in feedbacks:
            if feedback.cyclic_feedback:
                feedback_obj = Feedback()
                for field in feedback._meta.fields:
                    if field.name not in [
                        "id",
                        "cyclic_next_start_date",
                        "cyclic_next_end_date",
                    ]:
                        setattr(feedback_obj, field.name, getattr(feedback, field.name))
                title = (
                    f"{feedback_obj.review_cycle.split('- cyclic')[0]} - cyclic {feedback_obj.start_date}"
                    if "- cyclic" in feedback_obj.review_cycle
                    else f"{feedback_obj.review_cycle} - cyclic {feedback_obj.start_date}"
                )
                feedback_obj.review_cycle = title
                feedback_obj.status = "Not Started"
                feedback_obj.start_date = feedback.cyclic_next_start_date
                feedback_obj.end_date = feedback.cyclic_next_end_date
                feedback_obj.save()
                
                feedback.cyclic_feedback = False
                feedback.save()

                return feedback_obj

    except Exception as e:
        print(e)


scheduler = BackgroundScheduler()
cron_trigger = CronTrigger(hour=8)
scheduler.add_job(cyclic_feedback_creation, cron_trigger)
scheduler.start()
