# webhook_handler/handlers.py
from django.dispatch import receiver
from django.db.models.signals import post_save
import requests
import json
import os

@receiver(post_save)
# Webhook triggered when a new candidate is created
def handle_model_update(sender, created, instance, **kwargs):
    if sender.__name__ == 'Candidate' and created:  # Check if the sender is YourModel
        # send a request to the webhook
        url = os.environ.get("WEBHOOK_URL_NEW_CANDIDATE")
        data = {
            "username": 'Oxlac HRMS',
            "avatar_url": "https://oxlac.com/favicon.png",
            "embeds": [
                {
                    "author": {
                        "name": "Oxlac HRMS",
                        "url": "https://oxlac.com",
                        "icon_url": "https://oxlac.com/favicon.png"
                    },
                    "title": "New Candidate has applied for position " + str(instance.job_position_id),
                    "url": "https://employee.oxlac.com/candidate-view/" + str(instance.recruitment_id)+"/",
                    "description": "Candidate Name: " + instance.name + "\n" + "Email: " + instance.email,
                }
            ]
        }
        # send the request
        requests.post(url, data=json.dumps(data), headers={"Content-Type": "application/json"})
