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
