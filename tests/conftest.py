
import pytest
from tappay.client import Client, Models

@pytest.fixture
def sandbox_client():
    return Client(
        is_sandbox=True,
        partner_key="partner_key",
        merchant_id="merchant_id"
    )

@pytest.fixture
def production_client():
    return Client(
        is_sandbox=False,
        partner_key="partner_key",
        merchant_id="merchant_id"
    )

@pytest.fixture
def card_holder():
    return Models.CardHolderData(
        phone_number="0912345678",
        name="Wang Xiao Ming",
        email="test@example.com"
    )
