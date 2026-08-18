from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
import requests

from tappay.client import Client, Models


@pytest.fixture
def sandbox_client():
    return Client(is_sandbox=True, partner_key="partner_key", merchant_id="merchant_id")


@pytest.fixture
def production_client():
    return Client(
        is_sandbox=False, partner_key="partner_key", merchant_id="merchant_id"
    )


@pytest.fixture
def card_holder():
    return Models.CardHolderData(
        phone_number="0912345678", name="Wang Xiao Ming", email="test@example.com"
    )


@contextmanager
def mock_post(client, status_code=200, payload=None):
    """Patch a client's pooled session and yield the mocked ``post``.

    Patching the session rather than ``requests.post`` keeps these tests
    honest about the transport the client actually uses.
    """
    response = Mock(spec=requests.Response)
    response.status_code = status_code
    response.json.return_value = {"status": 0} if payload is None else payload
    response.content = b"{}"
    with patch.object(client.session, "post", return_value=response) as mocked:
        yield mocked


@contextmanager
def mock_bad_json(
    client,
    status_code=200,
    content=b"<html><body>504 Gateway Time-out</body></html>",
    content_type="text/html",
):
    """Patch the transport to return a 2xx whose body is not JSON."""
    response = Mock(spec=requests.Response)
    response.status_code = status_code
    response.json.side_effect = ValueError("Expecting value: line 1 column 1")
    response.content = content
    response.headers = {"Content-Type": content_type}
    with patch.object(client.session, "post", return_value=response) as mocked:
        yield mocked


@pytest.fixture
def post(sandbox_client):
    """Mocked transport for the sandbox client, for the common 200 case."""
    with mock_post(sandbox_client) as mocked:
        yield mocked
