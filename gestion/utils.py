import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.http import Http404

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now, add the exception logging.
    # We log all 5xx errors.
    if response is not None and 500 <= response.status_code <= 599:
        logger.error(
            "Unhandled exception processing request for %s: %s",
            context['request'].path,
            exc,
            exc_info=(type(exc), exc, exc.__traceback__)
        )

    # Standardize the error response format
    if response is not None:
        custom_response_data = {
            'detail': 'An error occurred.',
            'errors': {}
        }

        if isinstance(exc, DRFValidationError):
            # For DRF validation errors, the default handler usually populates response.data correctly
            custom_response_data['detail'] = 'Validation Error'
            custom_response_data['errors'] = response.data
            response.data = custom_response_data
            return response
        
        if isinstance(exc, Http404):
            custom_response_data['detail'] = 'Not Found'
            response.data = custom_response_data
            response.status_code = status.HTTP_404_NOT_FOUND
            return response

        # For other DRF exceptions, the detail is usually in response.data['detail']
        if 'detail' in response.data:
            custom_response_data['detail'] = response.data['detail']
        elif isinstance(response.data, list) and response.data:
            # Handle cases where DRF might return a list of strings directly for global errors
            custom_response_data['detail'] = ' '.join(response.data)
        else:
            # Fallback for unexpected formats
            custom_response_data['detail'] = "An unexpected error occurred."
            logger.warning(
                "DRF response data not in expected format for path %s: %s",
                context['request'].path,
                response.data
            )
        
        response.data = custom_response_data
        return response
    
    # If DRF's default exception handler returns None, it means it's an unhandled exception (usually 500 Internal Server Error)
    if response is None:
        logger.error(
            "Unhandled exception (500) processing request for %s: %s",
            context['request'].path,
            exc,
            exc_info=(type(exc), exc, exc.__traceback__)
        )
        return Response(
            {'detail': 'Internal server error. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
