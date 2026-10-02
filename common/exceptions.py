import json
import logging

from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def logging_exception_handler(exc, context):
    """Logs every rejected API request with the reason sent to the client."""
    response = exception_handler(exc, context)
    # Unhandled errors return None here and are logged by Django with a traceback.
    if response is not None:
        logger.warning(
            "Request rejected view=%s status=%s reason=%s",
            type(context["view"]).__name__,
            response.status_code,
            json.dumps(response.data, default=str),
        )
    return response
