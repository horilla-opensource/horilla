"""
Example API view with documentation
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from horilla_api.docs import document_api


class ExampleDocumentedView(APIView):
    """
    Example view demonstrating API documentation
    """

    @document_api(
        operation_description="Get API documentation example",
        responses={200: "Example response with documentation", 404: "Not found error"},
        tags=["Documentation Example"],
    )
    def get(self, request):
        """
        Example GET method with documentation
        """
        return Response(
            {"message": "API documentation is working correctly"},
            status=status.HTTP_200_OK,
        )
