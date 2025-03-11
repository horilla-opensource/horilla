from django.db import models

class Message(models.Model):
		user_message = models.TextField()
		bot_message = models.TextField()
		timestamp = models.DateTimeField(auto_now_add=True)