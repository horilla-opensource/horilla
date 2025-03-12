import os

from django.shortcuts import render
from pymsgbox import prompt

from employee.models import AIPolicy
from .models import Message
import requests

from .piplines import get_ai_response


def chat_view(request):
    if request.method == "POST":
        user_message = request.POST.get('message')
        bot_message = get_ai_response(user_message, request.user)
        # bot_message = "Bot Message"
        Message.objects.create(user_message=user_message, bot_message=bot_message,user=request.user)
    messages = Message.objects.filter(user=request.user)
    return render(request, 'chatbot/chat.html', {'messages': messages})


