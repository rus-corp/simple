import logging
import re

from django.urls import reverse
from rest_framework.test import APIClient

from common.logging import RequestContextFilter, trace_id_var


ACCOUNT_URL = reverse("accounts:account-detail")


def test_trace_id_is_returned_and_attached_to_logs(api_client: APIClient, caplog):
    caplog.handler.addFilter(RequestContextFilter())

    with caplog.at_level(logging.INFO):
        traced = api_client.get(ACCOUNT_URL, HTTP_X_REQUEST_ID="client-trace-12345")
        generated = api_client.get(ACCOUNT_URL)
        unsafe = api_client.get(ACCOUNT_URL, HTTP_X_REQUEST_ID="bad id\n!")

    # A valid client id is kept, so one trace can span several services.
    assert traced["X-Request-ID"] == "client-trace-12345"
    assert re.fullmatch(r"[0-9a-f]{32}", generated["X-Request-ID"])
    assert re.fullmatch(r"[0-9a-f]{32}", unsafe["X-Request-ID"])
    assert generated["X-Request-ID"] != unsafe["X-Request-ID"]

    request_logs = [
        record for record in caplog.records
        if record.name == "simple_bank.request"
    ]
    assert [record.trace_id for record in request_logs] == [
        traced["X-Request-ID"],
        generated["X-Request-ID"],
        unsafe["X-Request-ID"],
    ]
    # The context does not leak outside the request.
    assert trace_id_var.get() == "-"
