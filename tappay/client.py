import logging
import os
from platform import python_version
from typing import Any, Dict, Optional, Tuple, Union

import requests

from tappay._version import __version__
from tappay.exceptions import Exceptions
from tappay.models import Models

logger = logging.getLogger(__name__)

#: Retained for backward compatibility; prefer :data:`tappay.__version__`.
VERSION = __version__

#: A ``(connect, read)`` pair in seconds. The connect value sits just above a
#: multiple of the common 3 second TCP retransmission window, as recommended by
#: the ``requests`` documentation.
DEFAULT_TIMEOUT: Tuple[float, float] = (3.05, 27.0)

#: Anything ``requests`` accepts for its ``timeout`` argument. ``None`` means
#: "block indefinitely" and is strongly discouraged for server-side use.
TimeoutType = Union[float, Tuple[float, float], None]


class _Unset:
    """Sentinel distinguishing "argument omitted" from an explicit ``None``."""

    def __repr__(self) -> str:
        return "<unset>"


_UNSET = _Unset()

_REDACTED = "***REDACTED***"

#: Keys whose values are credentials, card secrets, or cardholder PII. Matched
#: case-insensitively against both request payloads and response bodies, at any
#: depth, before anything is handed to the logger.
_SENSITIVE_KEYS = frozenset(
    {
        # Credentials
        "partner_key",
        "x-api-key",
        "authorization",
        # Card secrets and handles
        "prime",
        "card_key",
        "card_token",
        "card_number",
        # Partial PAN returned in `card_info`
        "bin_code",
        "last_four",
        # Cardholder PII
        "phone_number",
        "name",
        "email",
        "zip_code",
        "address",
        "national_id",
    }
)


def _redact(value: Any) -> Any:
    """Return a copy of ``value`` with sensitive fields replaced.

    Recurses through nested mappings and sequences so that container fields
    such as ``cardholder`` and ``card_secret`` are cleaned in place rather than
    blanked wholesale, keeping the surrounding structure useful for debugging.
    """
    if isinstance(value, dict):
        return {
            key: (_REDACTED if str(key).lower() in _SENSITIVE_KEYS else _redact(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def _redacted_body(response: requests.Response) -> Any:
    """Render a response body for logging without leaking card secrets."""
    try:
        return _redact(response.json())
    except ValueError:
        try:
            return f"<{len(response.content)} bytes, unparsed>"
        except TypeError:  # pragma: no cover - non-standard response object
            return "<unparsed>"


class Client:
    """Client for interacting with the TapPay API."""

    def __init__(
        self,
        is_sandbox: bool,
        partner_key: Optional[str] = None,
        merchant_id: Optional[str] = None,
        app_name: Optional[str] = None,
        app_version: Optional[str] = None,
        timeout: TimeoutType = DEFAULT_TIMEOUT,
    ):
        """
        Create a Client object to start making calls to TapPay APIs.

        :param bool is_sandbox: Define runtime environment (sandbox or production)
        :param str partner_key: Your TapPay partner key (optional)
        :param str merchant_id: Your TapPay merchant ID (optional)
        :param str app_name: This optional value is added to the user-agent header
        :param str app_version: This optional value is added to the user-agent header
        :param timeout: Default request timeout in seconds, as a float or a
            ``(connect, read)`` tuple. Passing ``None`` disables the timeout and
            lets a stalled request block the calling thread forever.
        """
        if not isinstance(is_sandbox, bool):
            raise TypeError(
                f"expected bool for parameter `is_sandbox`, {type(is_sandbox)} found"
            )

        self.partner_key = partner_key or os.environ.get("TAPPAY_PARTNER_KEY")
        self.merchant_id = merchant_id or os.environ.get("TAPPAY_MERCHANT_ID")

        if self.partner_key is None:
            raise ValueError("Missing required value for `partner_key`")
        if self.merchant_id is None:
            raise ValueError("Missing required value for `merchant_id`")

        self.timeout = timeout

        subdomain = "sandbox" if is_sandbox else "prod"
        self.api_host = f"{subdomain}.tappaysdk.com"

        user_agent = f"tappay-python/{__version__} python/{python_version()}"

        if app_name and app_version:
            user_agent += f" {app_name}/{app_version}"

        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": user_agent,
            "x-api-key": self.partner_key,
        }

    def pay_by_prime(
        self,
        prime: str,
        amount: int,
        details: str,
        card_holder_data: Models.CardHolderData,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Make a payment using "prime" obtained from TapPay frontend SDK
        Ref: https://docs.tappaysdk.com/tutorial/zh/back.html#pay-by-prime-api
        """
        if not isinstance(card_holder_data, Models.CardHolderData):
            raise TypeError(
                f"expected `CardHolderData` type for parameter "
                f"`card_holder_data`, {type(card_holder_data)} found"
            )

        params = {
            "prime": prime,
            "amount": amount,
            "currency": Models.Currencies.TWD,
            "details": details,
            "cardholder": card_holder_data.to_dict(),
        }

        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key_and_merchant_id(
            "/tpc/payment/pay-by-prime", params, timeout
        )

    def pay_by_token(
        self,
        card_key: str,
        card_token: str,
        amount: int,
        details: str,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Make a payment using previously obtained card secrets (key & token)
        Ref: https://docs.tappaysdk.com/tutorial/zh/back.html#pay-by-card-token-api
        """
        params = {
            "card_key": card_key,
            "card_token": card_token,
            "amount": amount,
            "currency": Models.Currencies.TWD,
            "details": details,
        }

        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key_and_merchant_id(
            "/tpc/payment/pay-by-token", params, timeout
        )

    def refund(
        self,
        rec_trade_id: str,
        amount: int,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Refund a payment
        Ref: https://docs.tappaysdk.com/tutorial/zh/back.html#refund-api
        """
        params = {
            "rec_trade_id": rec_trade_id,
            "amount": amount,
        }

        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key("/tpc/transaction/refund", params, timeout)

    def get_records(
        self,
        filters_dict: Dict[str, Any],
        page: int = 0,
        records_per_page: int = 50,
        order_by_dict: Optional[Dict[str, Any]] = None,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
    ) -> Optional[Dict[str, Any]]:
        """
        Query historical records
        Ref: https://docs.tappaysdk.com/tutorial/zh/back.html#record-api
        """
        params = {
            "records_per_page": records_per_page,
            "page": page,
            "filters": filters_dict,
        }

        if order_by_dict:
            params["order_by"] = order_by_dict

        return self.__post_with_partner_key("/tpc/transaction/query", params, timeout)

    def capture_today(
        self,
        rec_trade_id: str,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
    ) -> Optional[Dict[str, Any]]:
        """
        Capture specific payment record
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-today-api
        """
        params = {
            "rec_trade_id": rec_trade_id,
        }

        return self.__post_with_partner_key("/tpc/transaction/cap", params, timeout)

    def cancel_capture(
        self,
        rec_trade_id: str,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
    ) -> Optional[Dict[str, Any]]:
        """
        Cancel a specific capture
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-cancel-api
        """
        params = {
            "rec_trade_id": rec_trade_id,
        }

        return self.__post_with_partner_key(
            "/tpc/transaction/cap/cancel", params, timeout
        )

    def get_trade_history(
        self,
        rec_trade_id: str,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
    ) -> Optional[Dict[str, Any]]:
        """
        Get record and status of a specific transaction
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#trade-history-api
        """
        params = {
            "rec_trade_id": rec_trade_id,
        }

        return self.__post_with_partner_key(
            "/tpc/transaction/trade-history", params, timeout
        )

    def bind_card(
        self,
        prime: str,
        card_holder_data: Models.CardHolderData,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Bind new credit card
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#bind-card-api
        """
        if not isinstance(card_holder_data, Models.CardHolderData):
            raise TypeError(
                f"expected `CardHolderData` type for parameter "
                f"`card_holder_data`, {type(card_holder_data)} found"
            )

        params = {
            "prime": prime,
            "currency": Models.Currencies.TWD,
            "cardholder": card_holder_data.to_dict(),
        }

        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key_and_merchant_id(
            "/tpc/card/bind", params, timeout
        )

    def remove_card(
        self,
        card_key: str,
        card_token: str,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
    ) -> Optional[Dict[str, Any]]:
        """
        Remove bound credit card
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#remove-card-api
        """
        params = {
            "card_key": card_key,
            "card_token": card_token,
        }

        return self.__post_with_partner_key("/tpc/card/remove", params, timeout)

    def cancel_refund(
        self,
        rec_trade_id: str,
        *,
        timeout: Union[TimeoutType, _Unset] = _UNSET,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Cancel a single refund
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#refund-cancel-api
        """
        params = {
            "rec_trade_id": rec_trade_id,
        }

        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key(
            "/tpc/transaction/refund/cancel", params, timeout
        )

    def __post_with_partner_key(
        self,
        request_uri: str,
        params: Dict[str, Any],
        timeout: Union[TimeoutType, _Unset] = _UNSET,
    ) -> Optional[Dict[str, Any]]:
        params = dict(params, partner_key=self.partner_key)
        return self.__post(request_uri, params, timeout)

    def __post_with_partner_key_and_merchant_id(
        self,
        request_uri: str,
        params: Dict[str, Any],
        timeout: Union[TimeoutType, _Unset] = _UNSET,
    ) -> Optional[Dict[str, Any]]:
        params = dict(params, merchant_id=self.merchant_id)
        return self.__post_with_partner_key(request_uri, params, timeout)

    def __post(
        self,
        request_uri: str,
        params: Dict[str, Any],
        timeout: Union[TimeoutType, _Unset] = _UNSET,
    ) -> Optional[Dict[str, Any]]:
        uri = f"https://{self.api_host}{request_uri}"
        params = dict(params)

        effective_timeout = self.timeout if isinstance(timeout, _Unset) else timeout

        # Guarded so the redaction pass is skipped entirely when debug logging
        # is off, and so credentials are never formatted into a log record.
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("POST to: %s", uri)
            logger.debug("POST headers: %s", _redact(self.headers))
            logger.debug("POST params: %s", _redact(params))
            logger.debug("POST timeout: %s", effective_timeout)

        response = requests.post(
            uri, json=params, headers=self.headers, timeout=effective_timeout
        )
        return self.__parse(response)

    def __parse(self, response: requests.Response) -> Optional[Dict[str, Any]]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("response status: %s", response.status_code)
            logger.debug("response content: %s", _redacted_body(response))

        if response.status_code == 401:
            message = f"{response.status_code} response from {self.api_host}"
            raise Exceptions.AuthenticationError(message)
        elif response.status_code == 204:
            return None
        elif 200 <= response.status_code < 300:
            return response.json()
        elif 400 <= response.status_code < 500:
            message = f"{response.status_code} response from {self.api_host}"
            raise Exceptions.ClientError(message)
        elif 500 <= response.status_code < 600:
            message = f"{response.status_code} response from {self.api_host}"
            raise Exceptions.ServerError(message)

        # Fallback for unexpected status codes
        message = f"Unexpected status code {response.status_code} from {self.api_host}"
        raise Exceptions.ServerError(message)
