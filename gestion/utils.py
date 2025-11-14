import logging
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now, add the exception logging.
    # We log all 5xx errors.
    if response is not None and 500 <= response.status_code <= 599:
        logger.error(
            "Unhandled exception processing request for %s",
            context['request'].path,
            exc_info=(type(exc), exc, exc.__traceback__)
        )

    return response
