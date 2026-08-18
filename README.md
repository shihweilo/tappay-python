
# TapPay Python SDK

![CI](https://github.com/shihweilo/tappay-python/workflows/CI/badge.svg)
[![PyPI version](https://badge.fury.io/py/tappay.svg)](https://badge.fury.io/py/tappay)
[![Python Versions](https://img.shields.io/pypi/pyversions/tappay.svg)](https://pypi.org/project/tappay/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> [!IMPORTANT]
> **Python 2 Support Dropped**: As of version 0.5.0, this library no longer supports Python 2.7. Please use Python 3.8 or newer.

> [!NOTE]
> **Pydantic v2 Integration**: As of version 0.6.0, this library uses Pydantic v2 for enhanced data validation, type safety, and automatic serialization. This provides better error messages and ensures data integrity when working with TapPay APIs.

> [!NOTE]
> **Typed**: As of version 0.6.1, this package ships a `py.typed` marker (PEP 561), so mypy, Pyright, and your IDE will use the library's own type hints.

This is the unofficial Python client library for TapPay's Backend API. To use it you'll need a TapPay account. Sign up at [tappaysdk.com](https://www.tappaysdk.com).

## Installation

Install using pip:

```bash
pip install tappay
```

## Usage

### Initialization

```python
import tappay

# Initialize the client
client = tappay.Client(
    is_sandbox=True, 
    partner_key="YOUR_PARTNER_KEY", 
    merchant_id="YOUR_MERCHANT_ID"
)
```

For production, you can set `TAPPAY_PARTNER_KEY` and `TAPPAY_MERCHANT_ID` environment variables and omit them in the constructor:

```python
client = tappay.Client(is_sandbox=False)
```

### Timeouts

Every request carries a timeout by default: `(3.05, 27.0)` seconds, as a
`(connect, read)` pair. Override it for all calls on a client:

```python
client = tappay.Client(is_sandbox=False, timeout=10.0)
```

Or for a single call, using the keyword-only `timeout` argument available on
every API method:

```python
response = client.refund(rec_trade_id="rec_trade_id", amount=100, timeout=(3.05, 60.0))
```

Passing `timeout=None` to the constructor disables the timeout entirely, which
lets a stalled request block the calling thread indefinitely. This is almost
never what you want in a server process.

### Logging

The client logs request and response details at `DEBUG` level. Credentials
(`partner_key`, `x-api-key`), card handles (`prime`, `card_key`, `card_token`),
and cardholder PII (name, email, phone number, address, national ID) are
replaced with `***REDACTED***` before anything reaches the logger, so enabling
debug logging will not spill payment data into your log aggregator.

```python
import logging

logging.getLogger("tappay.client").setLevel(logging.DEBUG)
```

### Pay by Prime

```python
# Create cardholder data
card_holder = tappay.Models.CardHolderData(
    phone_number="0912345678",
    name="Wang Xiao Ming",
    email="test@example.com"
)

# Make payment
response = client.pay_by_prime(
    prime="prime_token_from_frontend",
    amount=100,
    details="Order #123",
    card_holder_data=card_holder
)
print(response)
```

### Pay by Token

```python
response = client.pay_by_token(
    card_key="card_key",
    card_token="card_token",
    amount=100,
    details="Subscription"
)
```

### Refunds

```python
response = client.refund(
    rec_trade_id="rec_trade_id",
    amount=100
)
```

For more API details, please refer to the [TapPay Backend API Documentation](https://docs.tappaysdk.com/tutorial/zh/back.html).

## Development

### Setup

1. Clone the repository:

```bash
git clone https://github.com/shihweilo/tappay-python.git
cd tappay-python
```

2. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
pip install pytest pytest-cov ruff
```

### Testing

Run tests using pytest:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=tappay
```

### Linting and Formatting

Check code with ruff:

```bash
ruff check .
```

Format code with ruff:

```bash
ruff format .
```

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.
