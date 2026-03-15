from django.contrib.auth import authenticate
from drf_yasg import openapi
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from horilla_api.docs import document_api

from ...api_serializers.auth.serializers import (
    GetEmployeeSerializer,
    LoginRequestSerializer,
)


class LoginAPIView(APIView):
    @document_api(
        operation_description="Authenticate user and return JWT access token with employee info",
        request_body=LoginRequestSerializer,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "employee": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "full_name": openapi.Schema(type=openapi.TYPE_STRING),
                            "employee_profile": openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description="Profile image URL",
                            ),
                        },
                    ),
                    "access": openapi.Schema(
                        type=openapi.TYPE_STRING, description="JWT access token"
                    ),
                    "face_detection": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "face_detection_image": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Face detection image URL",
                        nullable=True,
                    ),
                    "geo_fencing": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "company_id": openapi.Schema(
                        type=openapi.TYPE_INTEGER, nullable=True
                    ),
                },
            ),
        },
        tags=["auth"],
    )
    def post(self, request):
        if "username" and "password" in request.data.keys():
            username = request.data.get("username")
            password = request.data.get("password")
            user = authenticate(username=username, password=password)
            if user:
                refresh = RefreshToken.for_user(user)
                employee = user.employee_get
                face_detection = False
                face_detection_image = None
                geo_fencing = False
                company_id = None
                try:
                    face_detection = employee.get_company().face_detection.start
                except:
                    pass
                try:
                    geo_fencing = employee.get_company().geo_fencing.start
                except:
                    pass
                try:
                    face_detection_image = employee.face_detection.image.url
                except:
                    pass
                try:
                    company_id = employee.get_company().id
                except:
                    pass
                result = {
                    "employee": GetEmployeeSerializer(employee).data,
                    "access": str(refresh.access_token),
                    "face_detection": face_detection,
                    "face_detection_image": face_detection_image,
                    "geo_fencing": geo_fencing,
                    "company_id": company_id,
                }
                return Response(result, status=200)
            else:
                return Response({"error": "Invalid credentials"}, status=401)
        else:
            return Response({"error": "Please provide Username and Password"})
