import importlib.metadata
import json
import logging
import pathlib
from unittest.mock import Mock, patch

import pytest
import requests

import tappay
from tappay.client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRYABLE_PATHS,
    VERSION,
    Client,
    Models,
    _redact,
)
from tappay.exceptions import (
    AuthenticationError,
    ClientError,
    ServerError,
    TapPayError,
)
from tests.conftest import mock_post

WRITE_PATHS = (
    "/tpc/payment/pay-by-prime",
    "/tpc/payment/pay-by-token",
    "/tpc/transaction/refund",
    "/tpc/transaction/refund/cancel",
    "/tpc/transaction/cap",
    "/tpc/transaction/cap/cancel",
    "/tpc/card/bind",
    "/tpc/card/remove",
)


# --- Construction ---------------------------------------------------------


def test_client_initialization_sandbox(sandbox_client):
    assert sandbox_client.api_host == "sandbox.tappaysdk.com"
    assert sandbox_client.partner_key == "partner_key"
    assert sandbox_client.merchant_id == "merchant_id"


def test_client_initialization_production(production_client):
    assert production_client.api_host == "prod.tappaysdk.com"


def test_is_sandbox_must_be_a_bool():
    with pytest.raises(TypeError, match="expected bool"):
        Client(is_sandbox="yes", partner_key="pk", merchant_id="mid")


def test_credentials_fall_back_to_environment(monkeypatch):
    monkeypatch.setenv("TAPPAY_PARTNER_KEY", "env_pk")
    monkeypatch.setenv("TAPPAY_MERCHANT_ID", "env_mid")

    client = Client(is_sandbox=True)

    assert client.partner_key == "env_pk"
    assert client.merchant_id == "env_mid"


def test_explicit_credentials_win_over_environment(monkeypatch):
    monkeypatch.setenv("TAPPAY_PARTNER_KEY", "env_pk")
    monkeypatch.setenv("TAPPAY_MERCHANT_ID", "env_mid")

    client = Client(is_sandbox=True, partner_key="arg_pk", merchant_id="arg_mid")

    assert client.partner_key == "arg_pk"
    assert client.merchant_id == "arg_mid"


def test_missing_partner_key_is_rejected(monkeypatch):
    monkeypatch.delenv("TAPPAY_PARTNER_KEY", raising=False)
    with pytest.raises(ValueError, match="partner_key"):
        Client(is_sandbox=True, merchant_id="mid")


def test_missing_merchant_id_is_rejected(monkeypatch):
    monkeypatch.delenv("TAPPAY_MERCHANT_ID", raising=False)
    with pytest.raises(ValueError, match="merchant_id"):
        Client(is_sandbox=True, partner_key="pk")


def test_partner_key_is_sent_as_the_api_key_header(sandbox_client):
    assert sandbox_client.headers["x-api-key"] == "partner_key"
    assert sandbox_client.headers["Content-Type"] == "application/json"


# --- Request shape, per endpoint -----------------------------------------


def test_pay_by_prime(sandbox_client, card_holder, post):
    response = sandbox_client.pay_by_prime(
        prime="test_prime", amount=100, details="test", card_holder_data=card_holder
    )

    assert response["status"] == 0
    uri, body = post.call_args.args[0], post.call_args.kwargs["json"]
    assert uri == "https://sandbox.tappaysdk.com/tpc/payment/pay-by-prime"
    assert body["prime"] == "test_prime"
    assert body["amount"] == 100
    assert body["currency"] == "TWD"
    assert body["details"] == "test"
    assert body["cardholder"] == card_holder.to_dict()
    # This endpoint is authenticated with both credentials.
    assert body["partner_key"] == "partner_key"
    assert body["merchant_id"] == "merchant_id"


def test_pay_by_prime_rejects_a_non_model_cardholder(sandbox_client):
    with pytest.raises(TypeError, match="CardHolderData"):
        sandbox_client.pay_by_prime(
            prime="p", amount=100, details="d", card_holder_data={}
        )


def test_pay_by_token(sandbox_client, post):
    sandbox_client.pay_by_token(
        card_key="ck", card_token="ct", amount=250, details="Subscription"
    )

    uri, body = post.call_args.args[0], post.call_args.kwargs["json"]
    assert uri == "https://sandbox.tappaysdk.com/tpc/payment/pay-by-token"
    assert body["card_key"] == "ck"
    assert body["card_token"] == "ct"
    assert body["amount"] == 250
    assert body["details"] == "Subscription"
    assert body["merchant_id"] == "merchant_id"


def test_refund(sandbox_client, post):
    sandbox_client.refund(rec_trade_id="rec", amount=100)

    uri, body = post.call_args.args[0], post.call_args.kwargs["json"]
    assert uri == "https://sandbox.tappaysdk.com/tpc/transaction/refund"
    assert body == {"rec_trade_id": "rec", "amount": 100, "partner_key": "partner_key"}
    # Refunds authenticate with the partner key alone.
    assert "merchant_id" not in body


def test_cancel_refund(sandbox_client, post):
    sandbox_client.cancel_refund("rec")

    uri, body = post.call_args.args[0], post.call_args.kwargs["json"]
    assert uri == "https://sandbox.tappaysdk.com/tpc/transaction/refund/cancel"
    assert body["rec_trade_id"] == "rec"


def test_capture_today(sandbox_client, post):
    sandbox_client.capture_today("rec")

    uri, body = post.call_args.args[0], post.call_args.kwargs["json"]
    assert uri == "https://sandbox.tappaysdk.com/tpc/transaction/cap"
    assert body["rec_trade_id"] == "rec"


def test_cancel_capture(sandbox_client, post):
    sandbox_client.cancel_capture("rec")

    assert (
        post.call_args.args[0]
        == "https://sandbox.tappaysdk.com/tpc/transaction/cap/cancel"
    )


def test_get_trade_history(sandbox_client, post):
    sandbox_client.get_trade_history("rec")

    assert (
        post.call_args.args[0]
        == "https://sandbox.tappaysdk.com/tpc/transaction/trade-history"
    )


def test_get_records_defaults(sandbox_client, post):
    sandbox_client.get_records({"time": {"start_time": 1}})

    uri, body = post.call_args.args[0], post.call_args.kwargs["json"]
    assert uri == "https://sandbox.tappaysdk.com/tpc/transaction/query"
    assert body["filters"] == {"time": {"start_time": 1}}
    assert body["page"] == 0
    assert body["records_per_page"] == 50
    assert "order_by" not in body


def test_get_records_with_pagination_and_ordering(sandbox_client, post):
    sandbox_client.get_records(
        {"time": {}}, page=3, records_per_page=10, order_by_dict={"attribute": "time"}
    )

    body = post.call_args.kwargs["json"]
    assert body["page"] == 3
    assert body["records_per_page"] == 10
    assert body["order_by"] == {"attribute": "time"}


def test_bind_card(sandbox_client, card_holder, post):
    sandbox_client.bind_card(prime="p", card_holder_data=card_holder)

    uri, body = post.call_args.args[0], post.call_args.kwargs["json"]
    assert uri == "https://sandbox.tappaysdk.com/tpc/card/bind"
    assert body["prime"] == "p"
    assert body["cardholder"] == card_holder.to_dict()
    assert body["merchant_id"] == "merchant_id"


def test_bind_card_rejects_a_non_model_cardholder(sandbox_client):
    with pytest.raises(TypeError, match="CardHolderData"):
        sandbox_client.bind_card(prime="p", card_holder_data={"name": "x"})


def test_remove_card(sandbox_client, post):
    sandbox_client.remove_card("ck", "ct")

    uri, body = post.call_args.args[0], post.call_args.kwargs["json"]
    assert uri == "https://sandbox.tappaysdk.com/tpc/card/remove"
    assert body["card_key"] == "ck"
    assert body["card_token"] == "ct"


def test_extra_kwargs_are_merged_into_the_request_body(sandbox_client, post):
    sandbox_client.refund("rec", 100, bank_refund_id="BR1")

    assert post.call_args.kwargs["json"]["bank_refund_id"] == "BR1"


def test_production_client_targets_the_production_host(production_client):
    with mock_post(production_client) as mocked:
        production_client.capture_today("rec")

    assert mocked.call_args.args[0].startswith("https://prod.tappaysdk.com/")


# --- Currency -------------------------------------------------------------


def test_currency_defaults_to_twd(sandbox_client, card_holder, post):
    sandbox_client.pay_by_prime(
        prime="p", amount=1, details="d", card_holder_data=card_holder
    )

    assert post.call_args.kwargs["json"]["currency"] == "TWD"


@pytest.mark.parametrize(
    "currency", [Models.Currencies.USD, "USD"], ids=["enum", "plain-string"]
)
def test_currency_can_be_overridden(sandbox_client, card_holder, post, currency):
    sandbox_client.pay_by_prime(
        prime="p",
        amount=1,
        details="d",
        card_holder_data=card_holder,
        currency=currency,
    )

    assert post.call_args.kwargs["json"]["currency"] == "USD"


def test_currency_applies_to_token_payments_and_card_binding(
    sandbox_client, card_holder, post
):
    sandbox_client.pay_by_token(
        card_key="ck", card_token="ct", amount=1, details="d", currency="JPY"
    )
    assert post.call_args.kwargs["json"]["currency"] == "JPY"

    sandbox_client.bind_card(
        prime="p", card_holder_data=card_holder, currency=Models.Currencies.HKD
    )
    assert post.call_args.kwargs["json"]["currency"] == "HKD"


def test_currency_enum_serializes_to_a_plain_code():
    """Guards against a `Currencies.TWD` repr reaching the API as the value."""
    encoded = json.dumps({"currency": Models.Currencies.TWD})

    assert encoded == '{"currency": "TWD"}'
    assert Models.Currencies.TWD == "TWD"


# --- Session, pooling and retries ----------------------------------------


def test_requests_go_through_the_pooled_session(sandbox_client, card_holder):
    """The module-level `requests.post` must no longer be used."""
    with patch.object(requests, "post") as module_post:
        with mock_post(sandbox_client) as session_post:
            sandbox_client.pay_by_prime(
                prime="p", amount=1, details="d", card_holder_data=card_holder
            )

    assert session_post.call_count == 1
    module_post.assert_not_called()


def test_session_is_reused_across_calls(sandbox_client):
    session = sandbox_client.session
    with mock_post(sandbox_client):
        sandbox_client.capture_today("a")
        sandbox_client.capture_today("b")

    assert sandbox_client.session is session


def test_read_only_endpoints_retry(sandbox_client):
    for path in RETRYABLE_PATHS:
        adapter = sandbox_client.session.get_adapter(
            f"https://{sandbox_client.api_host}{path}"
        )
        assert adapter.max_retries.total == DEFAULT_MAX_RETRIES, path


def test_write_endpoints_never_retry(sandbox_client):
    """A retried payment could double-charge, so these must stay at zero."""
    for path in WRITE_PATHS:
        adapter = sandbox_client.session.get_adapter(
            f"https://{sandbox_client.api_host}{path}"
        )
        assert adapter.max_retries.total == 0, path


def test_retry_policy_permits_post_and_targets_transient_failures(sandbox_client):
    adapter = sandbox_client.session.get_adapter(
        f"https://{sandbox_client.api_host}{RETRYABLE_PATHS[0]}"
    )
    retry = adapter.max_retries

    assert "POST" in retry.allowed_methods
    assert 503 in retry.status_forcelist
    assert 400 not in retry.status_forcelist
    assert retry.backoff_factor > 0


def test_retries_can_be_disabled():
    client = Client(is_sandbox=True, partner_key="pk", merchant_id="mid", max_retries=0)

    for path in RETRYABLE_PATHS:
        adapter = client.session.get_adapter(f"https://{client.api_host}{path}")
        assert adapter.max_retries.total == 0


def test_retry_mounts_are_scoped_to_this_clients_host(sandbox_client):
    """Sandbox retry mounts must not leak onto the production host."""
    adapter = sandbox_client.session.get_adapter(
        f"https://prod.tappaysdk.com{RETRYABLE_PATHS[0]}"
    )

    assert adapter.max_retries.total == 0


def test_close_releases_the_session(sandbox_client):
    with mock_post(sandbox_client):
        sandbox_client.capture_today("rec")

    sandbox_client.close()  # must not raise, and is safe to call again
    sandbox_client.close()


def test_client_works_as_a_context_manager():
    client = Client(is_sandbox=True, partner_key="pk", merchant_id="mid")

    with patch.object(client.session, "close") as closer:
        with client as entered:
            assert entered is client
            closer.assert_not_called()

    closer.assert_called_once()


# --- Timeout handling -----------------------------------------------------


def test_default_timeout_is_applied(sandbox_client, post):
    sandbox_client.capture_today("id")

    assert post.call_args.kwargs["timeout"] == DEFAULT_TIMEOUT


def test_client_level_timeout_override(card_holder):
    client = Client(is_sandbox=True, partner_key="pk", merchant_id="mid", timeout=5.0)
    with mock_post(client) as mocked:
        client.pay_by_prime(
            prime="p", amount=1, details="d", card_holder_data=card_holder
        )

    assert mocked.call_args.kwargs["timeout"] == 5.0


def test_per_call_timeout_overrides_client_default(sandbox_client, card_holder, post):
    sandbox_client.pay_by_prime(
        prime="p",
        amount=1,
        details="d",
        card_holder_data=card_holder,
        timeout=(1.0, 2.0),
    )

    assert post.call_args.kwargs["timeout"] == (1.0, 2.0)


def test_explicit_none_timeout_is_preserved(sandbox_client, post):
    """`None` means "no timeout" and must not be swallowed by the sentinel."""
    sandbox_client.capture_today("id", timeout=None)

    assert post.call_args.kwargs["timeout"] is None


def test_timeout_is_not_forwarded_as_an_api_field(sandbox_client, post):
    sandbox_client.refund("rec", 100, timeout=9.0)

    assert "timeout" not in post.call_args.kwargs["json"]


def test_timeout_propagates_to_every_endpoint(sandbox_client, card_holder, post):
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
        (
            "pay_by_prime",
            ("prime", 1, "d"),
            {"card_holder_data": card_holder},
        ),
    ]

    for method_name, args, kwargs in calls:
        getattr(sandbox_client, method_name)(*args, timeout=3.5, **kwargs)
        assert post.call_args.kwargs["timeout"] == 3.5, method_name


# --- Log redaction --------------------------------------------------------


def test_credentials_and_pii_are_redacted_in_request_logs(caplog):
    caplog.set_level(logging.DEBUG, logger="tappay.client")
    client = Client(
        is_sandbox=True, partner_key="SECRET_PARTNER_KEY", merchant_id="mid"
    )
    card_holder = Models.CardHolderData(
        phone_number="0912345678",
        name="Wang Xiao Ming",
        email="secret@example.com",
        national_id="A123456789",
    )

    with mock_post(client):
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

    with mock_post(
        sandbox_client,
        payload={
            "status": 0,
            "rec_trade_id": "REC123",
            "card_secret": {
                "card_key": "SECRET_CARD_KEY",
                "card_token": "SECRET_CARD_TOKEN",
            },
            "card_info": {"bin_code": "424242", "last_four": "4242"},
        },
    ):
        sandbox_client.capture_today("rec")

    for secret in ("SECRET_CARD_KEY", "SECRET_CARD_TOKEN", "424242", "4242"):
        assert secret not in caplog.text, f"{secret} leaked into logs"

    assert "REC123" in caplog.text


def test_redaction_is_skipped_when_debug_logging_is_off(sandbox_client, caplog):
    """No response parsing work should happen when debug logging is disabled."""
    caplog.set_level(logging.INFO, logger="tappay.client")

    with mock_post(sandbox_client) as mocked:
        sandbox_client.capture_today("rec")
        # Parsed once to build the return value, never for logging.
        assert mocked.return_value.json.call_count == 1

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


# --- Version and typing metadata -----------------------------------------


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


def test_user_agent_omits_app_details_when_incomplete():
    client = Client(
        is_sandbox=True, partner_key="pk", merchant_id="mid", app_name="MyApp"
    )

    assert "MyApp" not in client.headers["User-Agent"]


def test_package_ships_a_py_typed_marker():
    marker = pathlib.Path(tappay.__file__).parent / "py.typed"

    assert marker.is_file()


# --- HTTP-level error handling -------------------------------------------


def test_authentication_error_carries_a_message(sandbox_client):
    with mock_post(sandbox_client, status_code=401):
        with pytest.raises(AuthenticationError) as exc_info:
            sandbox_client.capture_today("id")

    assert str(exc_info.value) == "401 response from sandbox.tappaysdk.com"


def test_client_error_on_4xx(sandbox_client):
    with mock_post(sandbox_client, status_code=400):
        with pytest.raises(ClientError, match="400 response"):
            sandbox_client.capture_today("id")


def test_server_error_on_5xx(sandbox_client):
    with mock_post(sandbox_client, status_code=500):
        with pytest.raises(ServerError, match="500 response"):
            sandbox_client.capture_today("id")


def test_no_content_response_returns_none(sandbox_client):
    with mock_post(sandbox_client, status_code=204):
        assert sandbox_client.capture_today("id") is None


def test_unexpected_status_code_raises_server_error(sandbox_client):
    with mock_post(sandbox_client, status_code=302):
        with pytest.raises(ServerError, match="302"):
            sandbox_client.capture_today("id")


# --- Body-level error handling (raise_on_error) ---------------------------


@pytest.fixture
def strict_client():
    return Client(
        is_sandbox=True, partner_key="pk", merchant_id="mid", raise_on_error=True
    )


def test_non_zero_status_is_returned_silently_by_default(sandbox_client):
    """The historical behaviour: a declined card looks like any other result."""
    with mock_post(sandbox_client, payload={"status": 3, "msg": "Card declined"}):
        response = sandbox_client.capture_today("rec")

    assert response == {"status": 3, "msg": "Card declined"}


def test_non_zero_status_raises_when_strict(strict_client):
    payload = {"status": 3, "msg": "Card declined", "rec_trade_id": "REC1"}
    with mock_post(strict_client, payload=payload):
        with pytest.raises(TapPayError) as exc_info:
            strict_client.capture_today("rec")

    error = exc_info.value
    assert error.status == 3
    assert error.msg == "Card declined"
    assert error.response["rec_trade_id"] == "REC1"
    assert "Card declined" in str(error)


def test_success_status_passes_through_when_strict(strict_client):
    with mock_post(strict_client, payload={"status": 0, "msg": "Success"}):
        assert strict_client.capture_today("rec")["status"] == 0


def test_body_without_a_status_field_is_left_alone_when_strict(strict_client):
    with mock_post(strict_client, payload={"records": []}):
        assert strict_client.capture_today("rec") == {"records": []}


def test_non_dict_body_is_left_alone_when_strict(strict_client):
    with mock_post(strict_client, payload=[1, 2, 3]):
        assert strict_client.capture_today("rec") == [1, 2, 3]


def test_no_content_response_is_unaffected_when_strict(strict_client):
    with mock_post(strict_client, status_code=204):
        assert strict_client.capture_today("rec") is None


def test_tappay_error_is_catchable_as_the_base_error(strict_client):
    with mock_post(strict_client, payload={"status": 3, "msg": "nope"}):
        with pytest.raises(tappay.Error):
            strict_client.capture_today("rec")


# --- Robustness of the logging path --------------------------------------


def test_non_json_response_body_is_logged_without_crashing(sandbox_client, caplog):
    """An HTML error page must not break the debug logger."""
    caplog.set_level(logging.DEBUG, logger="tappay.client")

    response = Mock(spec=requests.Response)
    response.status_code = 204
    response.json.side_effect = ValueError("no JSON object could be decoded")
    response.content = b"<html>Gateway Timeout</html>"

    with patch.object(sandbox_client.session, "post", return_value=response):
        assert sandbox_client.capture_today("rec") is None

    assert "28 bytes, unparsed" in caplog.text
    assert "Gateway Timeout" not in caplog.text


def test_unset_sentinel_has_a_readable_repr():
    from tappay.client import _UNSET

    assert repr(_UNSET) == "<unset>"


@pytest.mark.parametrize(
    ("method_name", "args", "kwargs"),
    [
        ("pay_by_prime", ("p", 1, "d"), {"card_holder_data": None}),
        ("pay_by_token", ("ck", "ct", 1, "d"), {}),
        ("bind_card", ("p",), {"card_holder_data": None}),
        ("cancel_refund", ("rec",), {}),
        ("refund", ("rec", 1), {}),
    ],
)
def test_extra_kwargs_reach_the_body_on_every_method(
    sandbox_client, card_holder, post, method_name, args, kwargs
):
    if "card_holder_data" in kwargs:
        kwargs["card_holder_data"] = card_holder

    getattr(sandbox_client, method_name)(*args, three_domain_secure=True, **kwargs)

    assert post.call_args.kwargs["json"]["three_domain_secure"] is True
