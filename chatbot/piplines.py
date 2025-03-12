import os

import requests

from chatbot.models import Message
from employee.models import Policy, AIPolicy


def build_policies_summarization_and_refining():
    prompt = """
    سوف اعطيك قائمه بقوانين الشركه لكل بند واريدك ان تستخلص القوانين منها بتنسيق مختصر وسهل عليك لانه سوف يتم اعطئه لك لتجاوب علي اسئله الموظفين
    \n
    """
    policies = Policy.objects.all()


    # inject policies in the prompt
    for policy in policies:
        prompt += '\n'
        prompt += f"\n{policy.title}: {policy.body}"
        prompt += "\n"

    endpoint = "https://api.deepseek.com/chat/completions"  # Replace with the actual DeepSeek API endpoint
    headers = {
        "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY')}",
        # Replace with your actual DeepSeek API key
        "Content-Type": "application/json",
    }

    data = {
        "model": "deepseek-chat",
        "stream": False,
        "messages": [{"role": "user", "content": f"{prompt}"}],
    }

    # Make the API request
    response = requests.post(endpoint, headers=headers, json=data)
    response_data = response.json()
    ai_message = response_data['choices'][0]['message']['content']
    AIPolicy.objects.all().delete()
    ai_policy = AIPolicy.objects.create(
        policy_text=ai_message,
    )

def get_existing_messages(user) -> list:
    """
    Get all messages from the database and format them for the API.
    """
    formatted_messages = []
    for message in Message.objects.filter(user=user).values('user_message', 'bot_message'):
        formatted_messages.append({"role": "user", "content": message['user_message']})
        formatted_messages.append({"role": "assistant", "content": message['bot_message']})

    return formatted_messages

def get_ai_response(user_input: str, user) -> str:
    # Set up the API endpoint and headers for DeepSeek
    endpoint = "https://api.deepseek.com/chat/completions"  # Replace with the actual DeepSeek API endpoint
    headers = {
        "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY')}",  # Replace with your actual DeepSeek API key
        "Content-Type": "application/json",
    }

    # Data payload
    messages = get_existing_messages(user)

    # insert prompt
    prompt = "بناء علي سياسه الشركه التاليه اريدك ان تجاوب علي اسئلة الموظف في شركة وجدي مؤمن واريد كل اجاباتك ان تكون في سياق اللوائح فقط واذا كان هناك اي شئ لست متاكد منه اطلب من الموظف ان يتاكد من قسم الموارد البشريه في الشركه وايضا اجعل لغتك العاميه المصريه ولكن بشكل مهذب هاهي اللوائح في الشركه:"
    prompt += '\n'
    ai_policy = AIPolicy.objects.first()
    prompt += ai_policy.policy_text
    messages.insert(0,
        {
            'role': 'user', "content": prompt
        }
    )
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
