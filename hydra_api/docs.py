"""
Documentation helpers for API views
"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import authentication

# Module tags for organizing endpoints
MODULE_TAGS = {
    "auth": "Authentication",
    "asset": "Asset Management",
    "base": "Base",
    "employee": "Employee Management",
    "notifications": "Notifications",
    "payroll": "Payroll",
    "attendance": "Attendance",
    "leave": "Leave Management",
}

# Common response schemas
error_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "error": openapi.Schema(type=openapi.TYPE_STRING),
        "detail": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

success_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        "message": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

# Common parameters
pagination_params = [
    openapi.Parameter(
        "page", openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER
    ),
    openapi.Parameter(
        "page_size",
        openapi.IN_QUERY,
        description="Number of results per page",
        type=openapi.TYPE_INTEGER,
    ),
]


def document_api(
    operation_description=None,
    request_body=None,
    responses=None,
    query_params=None,
    tags=None,
    manual_parameters=None,
    **kwargs
):
    """
    Decorator for documenting API views with authentication

    Example usage:

    @document_api(
        operation_description="List all employees",
        responses={200: EmployeeSerializer(many=True)},
        tags=['Employee']
    )
    def get(self, request):
        ...
    """
    # Add pagination parameters for list views
    if manual_parameters is None and query_params == "paginated":
        manual_parameters = pagination_params

    # Add common error responses
    if responses and 400 not in responses:
        responses[400] = error_response
    if responses and 401 not in responses:
        responses[401] = error_response
    if responses and 403 not in responses:
        responses[403] = error_response

    # Add security requirement (Bearer only)
    security = [{"Bearer": []}]

    return swagger_auto_schema(
        operation_description=operation_description,
        request_body=request_body,
        responses=responses,
        manual_parameters=manual_parameters,
        tags=tags,
        security=security,
        **kwargs
    )
