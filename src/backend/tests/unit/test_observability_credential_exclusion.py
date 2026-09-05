"""FR-006 / SC-004 / contract §1: no captured span or log-record attribute may ever
equal or contain, as a substring, a bearer token or other credential value from the
triggering request — on a success path or a failure path.

Only `AuthService.validate_token` is mocked (the network/JWT-verification
boundary) — `middleware.extract_bearer_token`/`authenticate_with_email` run for
real, so the fixture token genuinely flows through the header-parsing code this
requirement is actually about, rather than being mocked away before it does.
"""

from __future__ import annotations

from unittest.mock import patch

from backend.function_app import auth_login

FIXTURE_TOKEN = "s3cr3t-fixture-bearer-token-value-should-never-be-captured"


def _assert_token_never_captured(span_exporter, log_exporter, token: str) -> None:
    for span in span_exporter.get_finished_spans():
        for value in span.attributes.values():
            assert token not in str(value)
        for event in span.events:
            for value in event.attributes.values():
                assert token not in str(value)

    for record in log_exporter.get_finished_logs():
        log_record = record.log_record
        assert token not in str(log_record.body)
        for value in log_record.attributes.values():
            assert token not in str(value)


def test_credential_excluded_on_success_path(otel_exporters, request_factory):
    span_exporter, log_exporter = otel_exporters
    req = request_factory(method="POST", url="/api/auth/login", token=FIXTURE_TOKEN)

    with patch(
        "backend.services.auth_service.AuthService.validate_token",
        return_value=(True, "test-oid", "player@example.com", None),
    ), patch("backend.api.auth.login.AccountProvisioningService") as service_cls:
        service_cls.return_value.authorize_sign_in.return_value = (
            True,
            type("Entry", (), {"roles": ["Player"], "email": "player@example.com"})(),
        )
        response = auth_login(req)

    assert response.status_code == 200
    _assert_token_never_captured(span_exporter, log_exporter, FIXTURE_TOKEN)


def test_credential_excluded_on_failure_path(otel_exporters, request_factory):
    span_exporter, log_exporter = otel_exporters
    req = request_factory(method="POST", url="/api/auth/login", token=FIXTURE_TOKEN)

    with patch(
        "backend.services.auth_service.AuthService.validate_token",
        side_effect=RuntimeError("boom"),
    ):
        response = auth_login(req)

    assert response.status_code == 500
    _assert_token_never_captured(span_exporter, log_exporter, FIXTURE_TOKEN)
