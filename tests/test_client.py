import importlib.metadata
import logging
import pathlib
from unittest.mock import Mock, patch

import pytest

import tappay
from tappay.client import DEFAULT_TIMEOUT, VERSION, Client, Models, _redact
from tappay.exceptions import AuthenticationError, ClientError, ServerError


def test_client_initialization_sandbox():
    client = Client(is_sandbox=True, partner_key="pk", merchant_id="mid")
    assert client.api_host == "sandbox.tappaysdk.com"
    assert client.partner_key == "pk"
    assert client.merchant_id == "mid"


def test_client_initialization_production():
    client = Client(is_sandbox=False, partner_key="pk", merchant_id="mid")
    assert client.api_host == "prod.tappaysdk.com"


def test_pay_by_prime(sandbox_client, card_holder):
    with patch("tappay.client.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": 0, "msg": "Success"}
        mock_post.return_value = mock_response

        response = sandbox_client.pay_by_prime(
            prime="test_prime", amount=100, details="test", card_holder_data=card_holder
        )

        assert response["status"] == 0
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["prime"] == "test_prime"
        assert kwargs["json"]["amount"] == 100
        assert kwargs["json"]["currency"] == "TWD"


def test_pay_by_prime_invalid_cardholder(sandbox_client):
    with pytest.raises(TypeError):
        sandbox_client.pay_by_prime(
            prime="p", amount=100, details="d", card_holder_data={}
        )


def test_api_error_handling_401(sandbox_client):
    with patch("tappay.client.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with pytest.raises(AuthenticationError):
            sandbox_client.pay_by_prime(
                prime="p",
                amount=1,
                details="d",
                card_holder_data=Models.CardHolderData(
                    phone_number="p", name="n", email="e@example.com"
                ),
            )


def test_api_error_handling_400(sandbox_client):
    with patch("tappay.client.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        with pytest.raises(ClientError):
            sandbox_client.capture_today("id")


def test_api_error_handling_500(sandbox_client):
    with patch("tappay.client.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        with pytest.raises(ServerError):
            sandbox_client.capture_today("id")


# --- Timeout handling (0.6.1) ---------------------------------------------


def _mock_post(status_code=200, payload=None):
    """Build a patched `requests.post` returning a canned response."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.json.return_value = payload if payload is not None else {"status": 0}
    return mock_response


def test_default_timeout_is_applied(sandbox_client):
    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post()
        sandbox_client.capture_today("id")

        assert mock_post.call_args.kwargs["timeout"] == DEFAULT_TIMEOUT


def test_client_level_timeout_override(card_holder):
    client = Client(is_sandbox=True, partner_key="pk", merchant_id="mid", timeout=5.0)
    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post()
        client.pay_by_prime(
            prime="p", amount=1, details="d", card_holder_data=card_holder
        )

        assert mock_post.call_args.kwargs["timeout"] == 5.0


def test_per_call_timeout_overrides_client_default(sandbox_client, card_holder):
    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post()
        sandbox_client.pay_by_prime(
            prime="p",
            amount=1,
            details="d",
            card_holder_data=card_holder,
            timeout=(1.0, 2.0),
        )

        assert mock_post.call_args.kwargs["timeout"] == (1.0, 2.0)


def test_explicit_none_timeout_is_preserved(sandbox_client):
    """`None` means "no timeout" and must not be swallowed by the sentinel."""
    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post()
        sandbox_client.capture_today("id", timeout=None)

        assert mock_post.call_args.kwargs["timeout"] is None


def test_timeout_is_not_forwarded_as_an_api_field(sandbox_client):
    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post()
        sandbox_client.refund("rec", 100, timeout=9.0)

        assert "timeout" not in mock_post.call_args.kwargs["json"]


def test_timeout_propagates_to_every_endpoint(sandbox_client, card_holder):
    """Guard against a new method forgetting to thread `timeout` through."""
    calls = [
        ("pay_by_token", ("ck", "ct", 100, "d"), {}),
        ("refund", ("rec", 100), {}),
        ("get_records", ({"time": {}},), {}),
        ("capture_today", ("rec",), {}),
        ("cancel_capture", ("rec",), {}),
        ("get_trade_history", ("rec",), {}),
        ("remove_card", ("ck", "ct"), {}),
        ("cancel_refund", ("rec",), {}),
        ("bind_card", ("prime",), {"card_holder_data": card_holder}),
    ]

    for method_name, args, kwargs in calls:
        with patch("tappay.client.requests.post") as mock_post:
            mock_post.return_value = _mock_post()
            getattr(sandbox_client, method_name)(*args, timeout=3.5, **kwargs)

            assert mock_post.call_args.kwargs["timeout"] == 3.5, method_name


# --- Log redaction (0.6.1) ------------------------------------------------


def test_credentials_and_pii_are_redacted_in_request_logs(caplog):
    caplog.set_level(logging.DEBUG, logger="tappay.client")
    client = Client(
        is_sandbox=True,
        partner_key="SECRET_PARTNER_KEY",
        merchant_id="mid",
    )
    card_holder = Models.CardHolderData(
        phone_number="0912345678",
        name="Wang Xiao Ming",
        email="secret@example.com",
        national_id="A123456789",
    )

    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post()
        client.pay_by_prime(
            prime="SECRET_PRIME",
            amount=100,
            details="Order #1",
            card_holder_data=card_holder,
        )

    for secret in (
        "SECRET_PARTNER_KEY",
        "SECRET_PRIME",
        "0912345678",
        "Wang Xiao Ming",
        "secret@example.com",
        "A123456789",
    ):
        assert secret not in caplog.text, f"{secret} leaked into logs"

    assert "***REDACTED***" in caplog.text
    # Non-sensitive context is still useful for debugging.
    assert "Order #1" in caplog.text
    assert "sandbox.tappaysdk.com" in caplog.text


def test_card_secrets_are_redacted_in_response_logs(sandbox_client, caplog):
    caplog.set_level(logging.DEBUG, logger="tappay.client")

    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post(
            payload={
                "status": 0,
                "rec_trade_id": "REC123",
                "card_secret": {
                    "card_key": "SECRET_CARD_KEY",
                    "card_token": "SECRET_CARD_TOKEN",
                },
                "card_info": {"bin_code": "424242", "last_four": "4242"},
            }
        )
        sandbox_client.capture_today("rec")

    for secret in ("SECRET_CARD_KEY", "SECRET_CARD_TOKEN", "424242", "4242"):
        assert secret not in caplog.text, f"{secret} leaked into logs"

    assert "REC123" in caplog.text


def test_redaction_is_skipped_when_debug_logging_is_off(sandbox_client, caplog):
    """No response parsing work should happen when debug logging is disabled."""
    caplog.set_level(logging.INFO, logger="tappay.client")

    with patch("tappay.client.requests.post") as mock_post:
        response = _mock_post()
        mock_post.return_value = response
        sandbox_client.capture_today("rec")

        # Parsed once to build the return value, never for logging.
        assert response.json.call_count == 1

    assert caplog.text == ""


def test_redact_leaves_unrelated_structures_intact():
    payload = {"amount": 100, "items": [{"sku": "A1", "name": "Widget"}]}
    assert _redact(payload) == {
        "amount": 100,
        "items": [{"sku": "A1", "name": "***REDACTED***"}],
    }


def test_redact_matches_keys_case_insensitively():
    assert _redact({"Partner_Key": "s", "X-API-KEY": "s"}) == {
        "Partner_Key": "***REDACTED***",
        "X-API-KEY": "***REDACTED***",
    }


# --- Version single-sourcing (0.6.1) --------------------------------------


def test_version_matches_installed_distribution_metadata():
    assert tappay.__version__ == importlib.metadata.version("tappay")


def test_client_version_constant_matches_package_version():
    assert VERSION == tappay.__version__


def test_user_agent_reports_the_package_version(sandbox_client):
    assert sandbox_client.headers["User-Agent"].startswith(
        f"tappay-python/{tappay.__version__} python/"
    )


def test_user_agent_includes_app_name_and_version():
    client = Client(
        is_sandbox=True,
        partner_key="pk",
        merchant_id="mid",
        app_name="MyApp",
        app_version="1.2.3",
    )
    assert client.headers["User-Agent"].endswith(" MyApp/1.2.3")


def test_package_ships_a_py_typed_marker():
    marker = pathlib.Path(tappay.__file__).parent / "py.typed"
    assert marker.is_file()


# --- Error surface (0.6.1) ------------------------------------------------


def test_authentication_error_carries_a_message(sandbox_client):
    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post(status_code=401)

        with pytest.raises(AuthenticationError) as exc_info:
            sandbox_client.capture_today("id")

    assert str(exc_info.value) == "401 response from sandbox.tappaysdk.com"


def test_no_content_response_returns_none(sandbox_client):
    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post(status_code=204)

        assert sandbox_client.capture_today("id") is None


def test_unexpected_status_code_raises_server_error(sandbox_client):
    with patch("tappay.client.requests.post") as mock_post:
        mock_post.return_value = _mock_post(status_code=302)

        with pytest.raises(ServerError) as exc_info:
            sandbox_client.capture_today("id")

    assert "302" in str(exc_info.value)
