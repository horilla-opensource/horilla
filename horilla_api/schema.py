"""
Schema configuration for API documentation
"""

from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import FilterInspector, SwaggerAutoSchema
from drf_yasg.utils import swagger_auto_schema


class SafeFilterInspector(FilterInspector):
    """
    Custom FilterInspector that safely handles views without queryset attributes.
    """

    def get_filter_backend_params(self, filter_backend):
        """
        Override to safely handle views that don't have a queryset attribute.
        """
        should_cleanup = False
        # Ensure view has queryset attribute
        if not hasattr(self.view, "queryset"):
            # Try to get queryset from get_queryset method
            if hasattr(self.view, "get_queryset"):
                import inspect

                sig = inspect.signature(self.view.get_queryset)
                params = sig.parameters

                # Check if get_queryset can be called without required parameters
                # (i.e., all params after 'self' have default values)
                can_call_without_args = True
                for param_name, param in params.items():
                    if (
                        param_name != "self"
                        and param.default == inspect.Parameter.empty
                    ):
                        can_call_without_args = False
                        break

                if can_call_without_args:
                    try:
                        queryset = self.view.get_queryset()
                        if queryset is not None:
                            self.view.queryset = queryset
                            should_cleanup = True
                        else:
                            # Return empty list if no queryset
                            return []
                    except (TypeError, AttributeError, ValueError):
                        # Fall through to try filterset_class/serializer_class
                        pass

                # If we couldn't call get_queryset or it failed, try to infer from filterset_class
                if not should_cleanup:
                    try:
                        if (
                            hasattr(self.view, "filterset_class")
                            and self.view.filterset_class
                        ):
                            if hasattr(self.view.filterset_class, "_meta") and hasattr(
                                self.view.filterset_class._meta, "model"
                            ):
                                model = self.view.filterset_class._meta.model
                                self.view.queryset = model.objects.none()
                                should_cleanup = True
                            else:
                                return []
                        elif (
                            hasattr(self.view, "serializer_class")
                            and self.view.serializer_class
                        ):
                            if hasattr(self.view.serializer_class, "Meta") and hasattr(
                                self.view.serializer_class.Meta, "model"
                            ):
                                model = self.view.serializer_class.Meta.model
                                self.view.queryset = model.objects.none()
                                should_cleanup = True
                            else:
                                return []
                        else:
                            return []
                    except (AttributeError, TypeError, ValueError):
                        return []
            else:
                # No get_queryset method, try to infer from filterset_class or serializer_class
                try:
                    if (
                        hasattr(self.view, "filterset_class")
                        and self.view.filterset_class
                    ):
                        if hasattr(self.view.filterset_class, "_meta") and hasattr(
                            self.view.filterset_class._meta, "model"
                        ):
                            model = self.view.filterset_class._meta.model
                            self.view.queryset = model.objects.none()
                            should_cleanup = True
                        else:
                            return []
                    elif (
                        hasattr(self.view, "serializer_class")
                        and self.view.serializer_class
                    ):
                        if hasattr(self.view.serializer_class, "Meta") and hasattr(
                            self.view.serializer_class.Meta, "model"
                        ):
                            model = self.view.serializer_class.Meta.model
                            self.view.queryset = model.objects.none()
                            should_cleanup = True
                        else:
                            return []
                    else:
                        return []
                except (AttributeError, TypeError, ValueError):
                    return []

        # Now call parent method with queryset available
        try:
            return super().get_filter_backend_params(filter_backend)
        except AttributeError:
            # If still fails, return empty list
            return []
        finally:
            # Clean up if we temporarily set queryset
            if should_cleanup and hasattr(self.view, "queryset"):
                try:
                    delattr(self.view, "queryset")
                except:
                    pass


class ModuleTaggingAutoSchema(SwaggerAutoSchema):
    """
    Custom schema generator that automatically tags operations based on their module.
    Also handles views without queryset attributes gracefully.
    """

    # Use our custom FilterInspector instead of the default one
    filter_inspectors = [SafeFilterInspector]

    def get_tags(self, operation_keys):
        # Extract module name from the operation keys
        if len(operation_keys) > 1:
            # Use the first part of the URL path as the tag (e.g., 'employee', 'attendance')
            return [operation_keys[0]]
        return super().get_tags(operation_keys)


class OrderedTagSchemaGenerator(OpenAPISchemaGenerator):
    """
    Custom schema generator to enforce tag ordering and auto-tag endpoints.

    Places 'auth' first, followed by remaining tags sorted alphabetically.
    Automatically tags endpoints based on their URL path if no tags are specified.
    """

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request=request, public=public)

        # Collect all tag names used in operations and auto-tag if needed
        tag_names = set()
        for path, path_item in schema.paths.items():
            # Extract module name from path (e.g., '/api/auth/login/' -> 'auth')
            path_parts = [p for p in path.split("/") if p]
            module_name = None
            if len(path_parts) > 1 and path_parts[0] == "api":
                module_name = path_parts[1] if len(path_parts) > 1 else None

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
                if operation:
                    # Auto-tag if no tags are specified
                    if not getattr(operation, "tags", None) and module_name:
                        operation.tags = [module_name]
                        tag_names.add(module_name)
                    elif getattr(operation, "tags", None):
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
