
# TapPay Python SDK

![CI](https://github.com/shihweilo/tappay-python/workflows/CI/badge.svg)
[![PyPI version](https://badge.fury.io/py/tappay.svg)](https://badge.fury.io/py/tappay)
[![Python Versions](https://img.shields.io/pypi/pyversions/tappay.svg)](https://pypi.org/project/tappay/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> [!IMPORTANT]
> **Python 2 Support Dropped**: As of version 0.5.0, this library no longer supports Python 2.7. Please use Python 3.8 or newer.

> [!NOTE]
> **Pydantic v2 Integration**: As of version 0.6.0, this library uses Pydantic v2 for enhanced data validation, type safety, and automatic serialization. This provides better error messages and ensures data integrity when working with TapPay APIs.

> [!NOTE]
> **Typed**: As of version 0.6.1, this package ships a `py.typed` marker (PEP 561), so mypy, Pyright, and your IDE will use the library's own type hints.

> [!NOTE]
> **Connection reuse**: As of version 0.7.0, the client holds a pooled `requests.Session`, so repeated calls reuse an established TLS connection instead of renegotiating one each time. Close it with `client.close()` or use the client as a context manager.

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
    merchant_id="YOUR_MERCHANT_ID",
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
    email="test@example.com",
)

# Make payment
response = client.pay_by_prime(
    prime="prime_token_from_frontend",
    amount=100,
    details="Order #123",
    card_holder_data=card_holder,
)
print(response)
```

### Pay by Token

```python
response = client.pay_by_token(
    card_key="card_key",
    card_token="card_token",
    amount=100,
    details="Subscription",
)
```

### Refunds

```python
response = client.refund(
    rec_trade_id="rec_trade_id",
    amount=100,
)
```

### Currencies

Payments settle in TWD by default. Pass `currency` to override it, using either a
`Models.Currencies` member or a plain currency string:

```python
response = client.pay_by_prime(
    prime="prime_token_from_frontend",
    amount=100,
    details="Order #123",
    card_holder_data=card_holder,
    currency=tappay.Models.Currencies.USD,
)
```

### Handling failures

TapPay reports business failures such as a declined card with an HTTP 200 and a
non-zero `status` in the response body, so they are invisible to HTTP-level error
handling. By default the response is returned as-is and it is your job to check:

```python
response = client.pay_by_prime(...)
if response["status"] != 0:
    ...  # declined, invalid argument, insufficient balance, and so on
```

Pass `raise_on_error=True` to have the client raise `TapPayError` instead:

```python
client = tappay.Client(is_sandbox=False, raise_on_error=True)

try:
    response = client.pay_by_prime(...)
except tappay.TapPayError as exc:
    print(exc.status, exc.msg, exc.response["rec_trade_id"])
```

The exception hierarchy is:

| Exception | Raised when |
| --- | --- |
| `AuthenticationError` | HTTP 401 |
| `ClientError` | HTTP 4xx |
| `ServerError` | HTTP 5xx, or an unexpected status code |
| `InvalidResponseError` | A 2xx body that is not valid JSON (subclasses `ServerError`) |
| `TapPayError` | Non-zero `status` in a 2xx body (only with `raise_on_error=True`) |

All of them subclass `tappay.Error`.

An intermediary such as a proxy or WAF can answer with an HTML error page under a
2xx status. That previously surfaced as a bare `json.JSONDecodeError` from inside
`requests`; it now raises `InvalidResponseError`, reporting the status, host,
content type, and body length. The body itself is deliberately left out of the
message, since exception text tends to end up in logs and error trackers.

### Connection reuse and retries

Each client owns a pooled session. Close it when you are done, or use the client
as a context manager:

```python
with tappay.Client(is_sandbox=False) as client:
    client.pay_by_prime(...)
```

The read-only query endpoints (`get_records`, `get_trade_history`) retry twice on
connection errors and on HTTP 429/500/502/503/504, with exponential backoff.
Payment, refund, capture, bind, and remove endpoints are **never** retried
automatically: TapPay exposes no idempotency key, so retrying a request that
actually succeeded upstream would charge the cardholder twice. Tune the retry
count with `max_retries=`, or disable it with `max_retries=0`.

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
pip install -e ".[dev]"
```

### Testing

Run tests using pytest:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=tappay --cov-report=term-missing
```

Type check with mypy:

```bash
mypy tappay
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
