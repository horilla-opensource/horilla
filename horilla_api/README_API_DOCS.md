# Horilla API Documentation

This document provides information on how to use and maintain the API documentation for Horilla HRMS.

## Accessing API Documentation

The API documentation is available at the following URLs:

- **Swagger UI**: `/api/swagger/` - Interactive documentation with testing capabilities
- **ReDoc**: `/api/redoc/` - Clean, responsive documentation for easier reading
- **JSON Schema**: `/api/swagger.json` - Raw schema for integration with other tools

## Features

- **Interactive Documentation**: Test API endpoints directly from the browser
- **Module Organization**: Endpoints are grouped by module (employee, attendance, etc.)
- **Authentication Support**: Bearer (JWT) only. Basic authentication is disabled.
- **Request/Response Examples**: Clear examples of data formats
- **Versioning**: API versions are clearly indicated

## For Developers: Adding Documentation to New Endpoints

### Using the `document_api` Decorator

```python
from horilla_api.docs import document_api

class MyAPIView(APIView):
    @document_api(
        operation_description="Description of what this endpoint does",
        request_body=MyRequestSerializer,
        responses={
            200: MyResponseSerializer,
            400: "Bad request error description"
        },
        tags=['Module Name']
    )
    def get(self, request):
        # Your view logic here
        pass
```

### Common Parameters

For paginated list views:

```python
@document_api(
    operation_description="List all items with pagination",
    responses={200: MySerializer(many=True)},
    query_params='paginated'
)
```

## Maintaining Documentation

- Documentation automatically updates when API endpoints change
- Security schemes (Bearer/JWT) are configured in `rest_conf.py`
- Basic authentication has been removed across all interfaces`
- Module tags are defined in `horilla_api/docs.py`

## Testing Documentation

1. Start the development server
2. Navigate to `/api/swagger/` or `/api/redoc/`
3. Verify all endpoints are properly documented
4. Test authentication flows
5. Check that all modules are properly organized

## Troubleshooting

If endpoints are not appearing in documentation:
- Ensure the URL is included in the `patterns` list in `horilla_api/urls.py`
- Check that the view is using proper decorators
- Verify the serializer is correctly defined

If you see a Basic authorization option in Swagger:
- Clear your browser cache and refresh `/api/swagger/`
- Confirm `SWAGGER_SETTINGS` only contains the `Bearer` scheme
