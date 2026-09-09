# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.1] - 2026-09-09

Corrections found by checking the SDK against the current TapPay documentation.
Two of these are defects introduced in 0.7.0. 0.7.0 was tagged but never
published to PyPI, so no released version ever exposed them.

### Fixed
- **`Models.Currencies` listed 11 currencies TapPay does not accept.** 0.7.0
  shipped JPY, GBP, AUD, EUR, CNY, KRW, SGD, THB, PHP, IDR and VND, none of
  which are documented. They autocompleted in an IDE and looked sanctioned.
  TapPay documents exactly four, each tied to an acquirer: TWD (most acquirers),
  HKD (Bank of China), MYR (RAZER PAY) and USD (Global Payments). The removed
  members are gone rather than deprecated, since keeping them would keep
  suggesting currencies that fail at the API. Plain currency strings are still
  accepted, so a currency TapPay adds later remains usable.
- **`raise_on_error=True` raised on a normal end-of-pagination.** The Record API
  answers `status: 2` for "end of list, no more records under the given filter",
  which is how paging terminates. 0.7.0 treated every non-zero status as a
  failure, so paging to the end of any query raised `TapPayError`. Benign
  statuses are now scoped per endpoint via `BENIGN_STATUSES`; `2` is benign for
  `/tpc/transaction/query` only and still raises everywhere else.
- **Full refunds were unreachable.** `refund()` required `amount`, but TapPay
  documents it as needed "only for partial refund" — omitting it refunds the
  whole transaction. `amount` is now optional and dropped from the request when
  `None`. Passing `0` still sends `0`, since a zero-value partial refund is not
  the same as a full one.
- **The default read timeout was below TapPay's documented minimum.** It was
  27.0s, chosen from a generic `requests` convention; TapPay documents 30s
  because banks take longer at peak. A short timeout reports failure for a
  transaction that may have succeeded. `DEFAULT_TIMEOUT` is now `(3.05, 30.0)`.

### Notes
- Verified against the TapPay Backend, Advanced Features and Reference pages as
  of 2026-09-09. TapPay publishes no API changelog, so these are differences
  observed against the current documentation, not a dated diff.
- Still outstanding and deferred to 0.8.0: `pay_by_token` accepts no cardholder
  (whose `phone_number` and `email` are required for 3D-secure token payments);
  `CardHolderData` is missing `name_en`, `phone_number_country_code`,
  `member_id` and `bank_member_id`, and validates none of the documented field
  lengths; `filters` and `details` are required by this SDK but optional in the
  API; and nine documented endpoints remain unimplemented, including
  reconciliation, card metadata and update-cardholder.

## [0.7.0] - 2026-08-18

### Added
- **Connection pooling.** The client now holds a `requests.Session`, so repeated
  calls reuse an established TLS connection instead of paying for a fresh
  handshake each time. Added `Client.close()` and context manager support to
  release pooled connections.
- **Selective retries.** The read-only endpoints (`get_records`,
  `get_trade_history`) retry twice on connection errors and HTTP
  429/500/502/503/504 with exponential backoff. Payment, refund, capture, bind
  and remove endpoints are deliberately excluded: TapPay exposes no idempotency
  key, so retrying a request that actually succeeded upstream would charge the
  cardholder twice. Configure with `max_retries=`, disable with `max_retries=0`.
- **`raise_on_error` and `TapPayError`.** TapPay reports declines and other
  business failures with an HTTP 200 and a non-zero `status` field, which
  HTTP-level error handling cannot see. Constructing the client with
  `raise_on_error=True` now raises `TapPayError`, carrying `.status`, `.msg` and
  the full `.response`. Defaults to `False` to preserve existing behaviour.
- **Currency selection.** `pay_by_prime`, `pay_by_token` and `bind_card` accept a
  keyword-only `currency`, defaulting to TWD as before. `Models.Currencies` is
  now a `str`-backed enum covering 15 currencies, and plain strings are accepted
  so a newly supported currency is usable before this list catches up.
- **`InvalidResponseError`.** A 2xx response whose body is not valid JSON (an
  HTML error page from a proxy or WAF, or an empty body) previously surfaced as
  a bare `json.JSONDecodeError` from inside `requests`, with no indication of
  which host or call produced it. It now raises `InvalidResponseError`, carrying
  the status, host, content type and body length, and preserving the original
  decode error as `__cause__`. It subclasses `ServerError`, so existing handlers
  keep working. The body itself is never included in the message, because
  exception text routinely reaches logs and error trackers and an unparseable
  body cannot be redacted by key.
- `dev` optional dependency group (`pip install -e ".[dev]"`), a `[tool.mypy]`
  configuration, and a mypy step in CI.
- Python 3.13 added to the CI test matrix and the package classifiers.

### Changed
- `requests` floor raised to 2.26 and `urllib3>=1.26` added as an explicit
  dependency; both are required for the `Retry(allowed_methods=...)` API.
- CI is split into a `quality` job (ruff and mypy on one interpreter) and a
  `test` matrix. Current mypy releases cannot target Python 3.8, and type
  checking does not need to repeat across every interpreter.
- `--cov=tappay` removed from pytest `addopts`, so a bare `pytest` no longer
  fails when `pytest-cov` is absent. Coverage is requested explicitly in CI.
- README badge corrected from black to ruff, which is what the project uses.
- Test coverage is now 100% (235 statements), up from 92%.

### Upgrade notes
- **If you mock `tappay.client.requests.post` in your tests, those mocks will no
  longer intercept anything.** The client now issues requests through
  `client.session.post`; patch that instead.
- `Models.Currencies` changed from a plain class to a `str` enum. Members still
  compare equal to their string form and still serialize as `"TWD"` through
  `json.dumps`, but `str()` and f-strings render them as `Currencies.TWD` on
  Python 3.11+. Never interpolate a member into a request payload.

## [0.6.1] - 2026-08-18

### Security
- **Credentials and cardholder PII are no longer written to logs.** Debug logging
  previously emitted the full request headers (including the `x-api-key` partner
  key), the full request body (`partner_key`, `prime`, `card_key`, `card_token`
  and the whole `cardholder` block), and the raw response body (including
  `card_secret` and `card_info`). Any application running with `logging.DEBUG`
  enabled was writing payment credentials and personal data to its logs. These
  values are now replaced with `***REDACTED***` before reaching the logger.
- Debug log records are now built lazily and guarded by `logger.isEnabledFor()`,
  so no redaction or response parsing happens when debug logging is off.

### Added
- **Request timeouts.** `Client` accepts a `timeout` argument, defaulting to
  `DEFAULT_TIMEOUT` (`(3.05, 27.0)` seconds). Previously requests had no timeout
  at all, so a stalled TapPay endpoint could block the calling thread forever and
  exhaust a web application's worker pool. Every API method also accepts a
  keyword-only `timeout` to override the client default per call.
- `py.typed` marker (PEP 561), so the type hints this library already ships are
  now visible to consumers' type checkers instead of being silently ignored.

### Fixed
- `tappay.__version__` reported `0.5.2` while the package was `0.6.0`. The version
  is now declared only in `pyproject.toml` and read from the installed
  distribution metadata, so `__version__`, `client.VERSION` and the `User-Agent`
  header can no longer drift apart.
- `AuthenticationError` was raised as a bare class and carried no message; it now
  reports `"401 response from <host>"` like the other error branches.
- Return annotations on the API methods said `Dict[str, Any]` but every method can
  return `None` on an HTTP 204. They are now `Optional[Dict[str, Any]]`.
- Removed a block of leftover development scratch notes from `client.py`.

### Notes
- Passing `timeout=None` to `Client(...)` restores the old unbounded behaviour.
  Passing `timeout=None` to an individual call means "inherit the client default";
  omitting it entirely does the same.
- `CardHolderData` silently ignores unknown keyword arguments (Pydantic's default),
  so a misspelled field is dropped without warning. `EmailStr` validation added in
  0.6.0 is also stricter than the plain `str` field it replaced. Both are unchanged
  in this release but worth knowing when upgrading from 0.5.x.

## [0.6.0] - 2025-12-17

### Added
- **Pydantic v2 Integration**: Migrated `CardHolderData` model to use Pydantic v2's `BaseModel`
  - Automatic data validation with clear error messages
  - Email validation using `EmailStr` type
  - Type safety and IDE autocomplete support
  - Automatic serialization/deserialization
  - JSON schema generation for API documentation
- Added `email-validator` dependency for email validation
- Added example file demonstrating Pydantic v2 validation features (`examples/pydantic_validation.py`)

### Changed
- `CardHolderData` now requires keyword arguments instead of positional arguments (Pydantic v2 requirement)
- Updated `to_dict()` method to use Pydantic's `model_dump()` for better performance
- Bumped version to 0.6.0

### Migration Guide
If you were using positional arguments:
```python
# Old (v0.5.x)
card_holder = Models.CardHolderData("0912345678", "Wang Xiao Ming", "test@example.com")

# New (v0.6.0+)
card_holder = Models.CardHolderData(
    phone_number="0912345678",
    name="Wang Xiao Ming",
    email="test@example.com",
)
```

## [0.5.2] - 2024-XX-XX

### Changed
- Previous version before Pydantic integration
