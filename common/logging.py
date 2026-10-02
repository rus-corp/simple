import logging
from contextvars import ContextVar


trace_id_var: ContextVar[str] = ContextVar('trace_id', default='-')
user_id_var: ContextVar[str] = ContextVar('user_id', default='-')


class RequestContextFilter(logging.Filter):
    def filter(
        self,
        record: logging.LogRecord
    ) -> bool:
        record.trace_id = trace_id_var.get()
        record.user_id = user_id_var.get()
        return True


def mask_email(email: object) -> str:
    """Keeps logs readable without storing full email addresses."""
    if not isinstance(email, str) or "@" not in email:
        return "-"
    local, _, domain = email.strip().lower().rpartition("@")
    return f"{local[:1]}***@{domain}"