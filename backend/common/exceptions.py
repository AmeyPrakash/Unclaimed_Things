from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    """
    Standardized error envelope adhering to TRD Section 6:
    {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Human readable summary",
            "request_id": "...",
            "details": {...}
        }
    }
    """
    response = exception_handler(exc, context)
    request = context.get('request')
    request_id = getattr(request, 'request_id', None)

    if response is not None:
        code = "API_ERROR"
        if response.status_code == 400:
            code = "VALIDATION_ERROR"
        elif response.status_code == 401:
            code = "UNAUTHORIZED"
        elif response.status_code == 403:
            code = "FORBIDDEN"
        elif response.status_code == 404:
            code = "NOT_FOUND"
        elif response.status_code == 429:
            code = "RATE_LIMITED"

        message = "An error occurred while processing your request."
        if isinstance(response.data, dict):
            if "detail" in response.data:
                message = str(response.data["detail"])
            elif "message" in response.data:
                message = str(response.data["message"])
            else:
                first_key = next(iter(response.data))
                first_val = response.data[first_key]
                if isinstance(first_val, list) and first_val:
                    message = f"{first_key}: {first_val[0]}"
                else:
                    message = f"{first_key}: {first_val}"
        elif isinstance(response.data, list) and response.data:
            message = str(response.data[0])

        error_data = {
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": response.data
            }
        }
        response.data = error_data
    else:
        # Unhandled server errors (500)
        error_data = {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "request_id": request_id
            }
        }
        response = Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
