from unittest.mock import Mock, patch

import pytest

from tappay.client import Client, Models
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
                card_holder_data=Models.CardHolderData("p", "n", "e"),
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
