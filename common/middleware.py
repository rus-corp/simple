import logging
import re
import time
import uuid


from .logging import trace_id_var, user_id_var


logger = logging.getLogger("simple_bank.request")
VALID_TRACE_ID = re.compile(r"\A[A-Za-z0-9-]{8,64}\Z")


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        trace_id = incoming if VALID_TRACE_ID.match(incoming) else uuid.uuid4().hex
        trace_token = trace_id_var.set(trace_id)
        user_token = user_id_var.set("-")
        started = time.perf_counter()
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = trace_id
            logger.info(
                "%s %s -> %s in %.1fms",
                request.method, request.path, response.status_code,
                (time.perf_counter() - started) * 1000,
            )
            return response
        finally:
            trace_id_var.reset(trace_token)
            user_id_var.reset(user_token)