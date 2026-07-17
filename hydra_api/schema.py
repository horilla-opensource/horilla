"""
Schema configuration for API documentation
"""

from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.utils import swagger_auto_schema


class ModuleTaggingAutoSchema(SwaggerAutoSchema):
    """
    Custom schema generator that automatically tags operations based on their module
    """

    def get_tags(self, operation_keys):
        # Extract module name from the operation keys
        if len(operation_keys) > 1:
            # Use the first part of the URL path as the tag (e.g., 'employee', 'attendance')
            return [operation_keys[0]]
        return super().get_tags(operation_keys)


class OrderedTagSchemaGenerator(OpenAPISchemaGenerator):
    """
    Custom schema generator to enforce tag ordering.

    Places 'auth' first, followed by remaining tags sorted alphabetically.
    """

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request=request, public=public)

        # Collect all tag names used in operations
        tag_names = set()
        for path_item in schema.paths.values():
            for method_name in (
                "get",
                "put",
                "post",
                "delete",
                "options",
                "head",
                "patch",
                "trace",
            ):
                operation = getattr(path_item, method_name, None)
                if operation and getattr(operation, "tags", None):
                    for t in operation.tags:
                        if t:
                            tag_names.add(t)

        # Desired order: 'auth' first, then others alphabetically
        ordered_names = ["auth"] + sorted([t for t in tag_names if t != "auth"])

        # Build top-level tags list in the specified order
        schema.tags = [{"name": name} for name in ordered_names]
        return schema


def api_doc(**kwargs):
    """
    Decorator for documenting API views

    Example usage:

    @api_doc(
        responses={200: EmployeeSerializer(many=True)},
        operation_description="List all employees",
        tags=['Employee']
    )
    def get(self, request):
        ...
    """
    return swagger_auto_schema(**kwargs)


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

# Security definitions are already configured in rest_conf.py
