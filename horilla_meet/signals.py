from datetime import datetime
from django.apps import apps
from django.dispatch import receiver
from django.db import models
from django.db.models.signals import post_save, m2m_changed

from horilla.horilla_middlewares import _thread_locals
from horilla_meet.models import GoogleMeeting
from horilla_meet.methods import create_calendar_event, update_calendar_event



@receiver(post_save, sender=GoogleMeeting)
def handle_google_meeting_save(sender, instance, created, **kwargs):
    """
    Handles creation and updates of GoogleMeeting (excluding attendees changes).
    """
    request = getattr(_thread_locals, "request")

    data = {
        "title": instance.title,
        "description": instance.description,
        "start_time": instance.start_time,
        "duration": instance.duration,
        "attendees": instance.attendees,
    }

    if created:
        created_event = create_calendar_event(request, data)
    else:
        created_event = update_calendar_event(request, data, instance.event_id)

    meet_link = created_event.get("hangoutLink", instance.meet_url)
    event_id = created_event.get("id")
    GoogleMeeting.objects.filter(id=instance.id).update(
        meet_url=meet_link, event_id=event_id
    )


if apps.is_installed("recruitment"):
    from recruitment.models import InterviewSchedule

    # @receiver(post_save, sender=InterviewSchedule)
    def create_meeting_for_interview(sender, instance, created, **kwargs):

        instance.refresh_from_db()
        title = f"Interview for {instance.candidate_id}"
        description = instance.description
        start_time = datetime.combine(instance.interview_date, instance.interview_time)
        print(start_time)
        attendees = [employee.get_mail() for employee in instance.employee_id.all()]
        attendees.append(instance.candidate_id.get_email())
        print(attendees)
        if instance.create_meeting:
            print(instance)
            print(instance.interview_date)
            print(instance.interview_time)
