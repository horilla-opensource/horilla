import os

from django.shortcuts import render
from .models import Message
import requests

def chat_view(request):
    if request.method == "POST":
        user_message = request.POST.get('message')
        # bot_message = get_ai_response(user_message)
        bot_message = "Bot Message"
        Message.objects.create(user_message=user_message, bot_message=bot_message)
    messages = Message.objects.all()
    return render(request, 'chatbot/chat.html', {'messages': messages})

def get_ai_response(user_input: str) -> str:
    # Set up the API endpoint and headers for DeepSeek
    endpoint = "https://api.deepseek.com/chat/completions"  # Replace with the actual DeepSeek API endpoint
    headers = {
        "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY')}",  # Replace with your actual DeepSeek API key
        "Content-Type": "application/json",
    }

    # Data payload
    messages = get_existing_messages()
    messages.append({"role": "user", "content": f"{user_input}"})
    data = {
        "model": "deepseek-chat",
        "stream":False,
        "messages": messages,
    }

    # Make the API request
    response = requests.post(endpoint, headers=headers, json=data)
    response_data = response.json()
    ai_message = response_data['choices'][0]['message']['content']
    return ai_message

def get_existing_messages() -> list:
    """
    Get all messages from the database and format them for the API.
    """
    formatted_messages = []

    for message in Message.objects.values('user_message', 'bot_message'):
        formatted_messages.append({"role": "user", "content": message['user_message']})
        formatted_messages.append({"role": "assistant", "content": message['bot_message']})

    return formatted_messages