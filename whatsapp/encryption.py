import base64
import json

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEuwIBADANBgkqhkiG9w0BAQEFAASCBKUwggShAgEAAoIBAQCitHXNMGC04pSI
di+ynQjLDQd1LrExd1nYMxdOFnX/CnVEJGVEUKPdDm5M300ULugeFPx76MsjQx97
vWAgZDMEA2+WyKFAHqmgRvVoiESZZnduIj2akVjFZvA24sbFpGunaiMPq61kWUBR
0pFRw4pnXEbPQnqu9H5vEJ7W5+G6CDlJD3eeTTkM85/ch1/REJbSDyp+Tozrc0Wa
Mv5xMUbVtSjwxaqwSfdMbAfJxnaaZ5SKwgiUEIsLKsQISWX3+qq6USWOCbJs6oTV
eWgeZfxgOjCUovJsZ2TuJ4aNfMtI+dFm3OMaeB2ypa4F4lWu8pq6FVhTseQntfUu
fQv4P+iRAgMBAAECggEABGOp6ecsNLUIHMZTcxYZbqDjWp3v2c3GdraqIkko1cCK
eVQiBz3Frej9wMUlZy38xRL73Lvi/wiIiOYK+dS6K5mMIR04fGpXWSOQ60kB0MGa
5zW1Q744DttAD7r+ccaFwPZ0C7At9U8TFSIBGZuU2ET9BApfFOkzn/tqzZFj3Yjg
OgWaGCvtOGCjLgjN1CWRTq+U66SUuVEtm8cXX8o4hVGfy2ITdg10xW+88qgLqxLj
/2RKPTixjmlwp1/28Z0rotp4GFUU5yplDq86YkdYNF8wHIPx0NiEUiLmAtfZrpmM
0xyJVJbgWh8QASzOxM1lq8WOWOOhJnVnkowYJsxVgQKBgQDZisbd8n59rJQfDMbK
7/cQ0gedl7No+0taY30hSckeR73yxAvmz83jqiD6qOlbaCbb+Rx1PPKewRZybrQV
n0CdFJ5oB1lbtLY7ftIlGQx2MiI4e+lAiCn+Zo2FnIm+C6LJKWqR18vLlHKebbJK
IAHdW76roZsdqAyBSyn0fh2gXQKBgQC/d+/30lIBafNCc6oDXbZFrH9/sRqCEg1u
jOhgNjwYZ23IkBMghyhD3eAiymvUFYCQ2pUfSMqygBbFUay5h5/PF34vzJmSVwC0
6SVemod/2Z7ZcVUogplSdAW1+V4f/3pyIptgKAAqlsE7lAQJAiyd7FnXx8/Rx7Cw
IVh+Jz11xQKBgBaTOTn1HT1LeH+UYtjSeDAtq46mHH8rfNFfe6/FqXJT/ZlA0P9d
1z7l+9AnUTgkIcw4GMTt0zu4S+0KIfQQd7MVXa7r/FDw+uxHp+UjqVBmuXhlG3qP
5tO4rr0L1pt7N6RqgN2rqEFzIUXhmlvo4GipSasj9SXpt4p/U1ZE9CwdAoGBAKSU
5jMyGMeaWT4Pyl5mWV1+r4IFrHGOLvmOKdk6BWI81cOHBMn7JANiX13IffOqH/9j
xLdFjObu76PhVwWLrTUITrGrv35pRvQ7TKILVtnxKHhk0Pyndj/H93i6x8vdgVVG
piR7fdkeCS+7RdSwh8Wf+oJfASaj7h8YKscV1+C5An9SKKO185jufNw+6cToVvBG
ii91044lvc8XidFgR6t3M9cJS3pHNemIfg2dZCu7i2/UbAIrsMDt4Uv4QGOaRGr/
rZ7JoquIPXVTaUjSJLWOELUi9TDBB1F04duW/xNsKswrFIk+mT0jMO3zB/LyCT5m
BCyI7ou85astK8+e4Q12
-----END PRIVATE KEY-----
"""
PASSPHRASE = "Horilla"
APP_SECRET = "6c18bf72d5f486479bf66c5807c2b393"


class FlowEndpointException(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


def decrypt_request(body, private_pem, passphrase):
    # Extract encrypted data from the request body
    encrypted_aes_key = body["encrypted_aes_key"]
    encrypted_flow_data = body["encrypted_flow_data"]
    initial_vector = body["initial_vector"]

    private_key = serialization.load_pem_private_key(
        private_pem.encode(), password=None, backend=default_backend()
    )

    decrypted_aes_key = private_key.decrypt(
        base64.b64decode(encrypted_aes_key),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    flow_data_buffer = base64.b64decode(encrypted_flow_data)
    iv_buffer = base64.b64decode(initial_vector)

    TAG_LENGTH = 16
    encrypted_flow_data_body = flow_data_buffer[:-TAG_LENGTH]
    encrypted_flow_data_tag = flow_data_buffer[-TAG_LENGTH:]

    cipher = Cipher(
        algorithms.AES(decrypted_aes_key),
        modes.GCM(iv_buffer, encrypted_flow_data_tag),
        backend=default_backend(),
    )
    decryptor = cipher.decryptor()

    decrypted_json_string = (
        decryptor.update(encrypted_flow_data_body) + decryptor.finalize()
    )

    return {
        "decrypted_body": json.loads(decrypted_json_string.decode("utf-8")),
        "aes_key_buffer": decrypted_aes_key,
        "initial_vector_buffer": iv_buffer,
    }


def encrypt_response(response, aes_key_buffer, initial_vector_buffer):
    response_bytes = json.dumps(response).encode("utf-8")

    flipped_iv = bytearray((b ^ 0xFF) for b in initial_vector_buffer)

    cipher = Cipher(
        algorithms.AES(aes_key_buffer),
        modes.GCM(bytes(flipped_iv)),
        backend=default_backend(),
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(response_bytes) + encryptor.finalize()
    ciphertext_with_tag = ciphertext + encryptor.tag
    encrypted_message = base64.b64encode(ciphertext_with_tag).decode("utf-8")

    return encrypted_message


# -------------------------------------------------views.py ------------------------------------------------

import base64
import hashlib
import hmac
import json
import os
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Load the private key string
# PRIVATE_KEY = os.environ.get('PRIVATE_KEY')
# Example:
# '''-----BEGIN RSA PRIVATE KEY-----
# MIIE...
# ...
# ...AQAB
# -----END RSA PRIVATE KEY-----'''

# PRIVATE_KEY = settings.PRIVATE_KEY


# @csrf_exempt
# def end_point(request):
#     try:
#         # Parse the request body
#         body = json.loads(request.body)

#         # Read the request fields
#         encrypted_flow_data_b64 = body["encrypted_flow_data"]
#         encrypted_aes_key_b64 = body["encrypted_aes_key"]
#         initial_vector_b64 = body["initial_vector"]

#         decrypted_data, aes_key, iv = decrypt_request(
#             encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64
#         )

#         # Return the next screen & data to the client
#         if decrypted_data["action"] == "ping":
#             response = {"data": {"status": "active"}}

#         else:
#             response = {"screen": "screen_one", "data": {"some_key": "some_value"}}

#         # Return the response as plaintext
#         return HttpResponse(
#             encrypt_response(response, aes_key, iv), content_type="text/plain"
#         )
#     except Exception as e:
#         print(e)
#         return JsonResponse({}, status=500)


@csrf_exempt
def end_point(request):
    try:
        body = json.loads(request.body)

        encrypted_flow_data_b64 = body["encrypted_flow_data"]
        encrypted_aes_key_b64 = body["encrypted_aes_key"]
        initial_vector_b64 = body["initial_vector"]

        decrypted_data, aes_key, iv = decrypt_request(
            encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64
        )
        if decrypted_data["action"] == "ping":
            response = {"data": {"status": "active"}}
        else:
            leave_types = get_leave_types()

            response = {"screen": "screen_one", "data": {"leave_types": leave_types}}

        return HttpResponse(
            encrypt_response(response, aes_key, iv), content_type="text/plain"
        )
    except Exception as e:
        print(e)
        return JsonResponse({}, status=500)


def get_leave_types():
    """
    Fetch leave types from database or settings.
    You can modify this function based on your data source.
    """
    # Option 1: If you have a LeaveType model
    try:
        from leave.models import LeaveType

        leave_types = list(LeaveType.objects.values("id", "name"))
        # Convert any non-string IDs to strings to match the schema
        for leave_type in leave_types:
            leave_type["id"] = str(leave_type["id"])
            leave_type["title"] = str(leave_type["name"])
            del leave_type["name"]

        return leave_types

    except ImportError:
        # Option 2: Return hardcoded values if no model exists
        return [
            {"id": "1", "title": "Casual Leave"},
            {"id": "2", "title": "Sick Leave"},
            {"id": "3", "title": "Paid Leave"},
        ]


def decrypt_request(encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64):
    flow_data = b64decode(encrypted_flow_data_b64)
    iv = b64decode(initial_vector_b64)

    # Decrypt the AES encryption key
    encrypted_aes_key = b64decode(encrypted_aes_key_b64)
    private_key = load_pem_private_key(PRIVATE_KEY.encode("utf-8"), password=None)
    aes_key = private_key.decrypt(
        encrypted_aes_key,
        OAEP(
            mgf=MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None
        ),
    )

    # Decrypt the Flow data
    encrypted_flow_data_body = flow_data[:-16]
    encrypted_flow_data_tag = flow_data[-16:]
    decryptor = Cipher(
        algorithms.AES(aes_key), modes.GCM(iv, encrypted_flow_data_tag)
    ).decryptor()
    decrypted_data_bytes = (
        decryptor.update(encrypted_flow_data_body) + decryptor.finalize()
    )
    decrypted_data = json.loads(decrypted_data_bytes.decode("utf-8"))
    return decrypted_data, aes_key, iv


def encrypt_response(response, aes_key, iv):
    # Flip the initialization vector
    flipped_iv = bytearray()
    for byte in iv:
        flipped_iv.append(byte ^ 0xFF)

    # Encrypt the response data
    encryptor = Cipher(algorithms.AES(aes_key), modes.GCM(flipped_iv)).encryptor()
    return b64encode(
        encryptor.update(json.dumps(response).encode("utf-8"))
        + encryptor.finalize()
        + encryptor.tag
    ).decode("utf-8")


def is_request_signature_valid(request, app_secret, request_body):
    if not app_secret:
        print(
            "App Secret is not set up. Please Add your app secret in settings to check for request validation"
        )
        return True

    signature_header = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")
    if not signature_header.startswith("sha256="):
        print("Invalid signature header")
        return False

    signature = signature_header[7:]  # Remove "sha256="

    hmac_digest = hmac.new(
        app_secret.encode(), request_body.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, hmac_digest)


# ----------------------------------------------------------------------------------------------------------
