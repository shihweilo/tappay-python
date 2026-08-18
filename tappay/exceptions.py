from typing import Any, Dict, Optional


class Error(Exception):
    """Base exception for all TapPay errors."""

    pass


class ClientError(Error):
    """Error raised when the client sends an invalid request."""

    pass


class ServerError(Error):
    """Error raised when the TapPay server encounters an issue."""

    pass


class AuthenticationError(ClientError):
    """Error raised when authentication fails."""

    pass


class TapPayError(Error):
    """Error raised when TapPay reports a failure in the response body.

    TapPay signals business-level failures (declined cards, invalid arguments,
    exhausted balances) with an HTTP 200 and a non-zero ``status`` field, so
    these are invisible to HTTP-level error handling. Raised only when the
    client is constructed with ``raise_on_error=True``.

    :ivar status: The non-zero ``status`` code returned by TapPay.
    :ivar msg: The human-readable ``msg`` field returned by TapPay.
    :ivar response: The full decoded response body, for callers that need
        fields such as ``rec_trade_id`` or ``bank_result_code``.
    """

    def __init__(
        self,
        status: Any,
        msg: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        self.status = status
        self.msg = msg
        self.response = response if response is not None else {}
        super().__init__(f"TapPay API error (status {status}): {msg}")


class Exceptions:
    """Namespace for TapPay exceptions (for backward compatibility)."""

    Error = Error
    ClientError = ClientError
    ServerError = ServerError
    AuthenticationError = AuthenticationError
    TapPayError = TapPayError
