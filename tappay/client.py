import logging
import os
from platform import python_version
from typing import Any, Dict, Optional

import requests

from tappay.exceptions import Exceptions
from tappay.models import Models

logger = logging.getLogger(__name__)

# We need to access __version__ from somewhere, commonly from a package
# level or hardcoded here then imported. For now I will hardcode it here
# or pass it in. Better yet, I will define __version__ in __init__.py and
# import it here? No, circular import. I will put __version__ in a
# separate file or keep it in __init__ and pass it to Client if needed,
# or just duplicate/move it. Let's define it in client.py for now to
# avoid circular dependency if __init__ imports client. Actually, the
# original code used it in User-Agent.
VERSION = "0.5.2"


class Client:
    """Client for interacting with the TapPay API."""

    def __init__(
        self,
        is_sandbox: bool,
        partner_key: Optional[str] = None,
        merchant_id: Optional[str] = None,
        app_name: Optional[str] = None,
        app_version: Optional[str] = None,
    ):
        """
        Create a Client object to start making calls to TapPay APIs.

        :param bool is_sandbox: Define runtime environment (sandbox or production)
        :param str partner_key: Your TapPay partner key (optional)
        :param str merchant_id: Your TapPay merchant ID (optional)
        :param str app_name: This optional value is added to the user-agent header
        :param str app_version: This optional value is added to the user-agent header
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

        subdomain = "sandbox" if is_sandbox else "prod"
        self.api_host = f"{subdomain}.tappaysdk.com"

        user_agent = f"tappay-python/{VERSION} python/{python_version()}"

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
        **kwargs: Any,
    ) -> Dict[str, Any]:
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
            "/tpc/payment/pay-by-prime", params
        )

    def pay_by_token(
        self,
        card_key: str,
        card_token: str,
        amount: int,
        details: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
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
            "/tpc/payment/pay-by-token", params
        )

    def refund(self, rec_trade_id: str, amount: int, **kwargs: Any) -> Dict[str, Any]:
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

        return self.__post_with_partner_key("/tpc/transaction/refund", params)

    def get_records(
        self,
        filters_dict: Dict[str, Any],
        page: int = 0,
        records_per_page: int = 50,
        order_by_dict: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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

        return self.__post_with_partner_key("/tpc/transaction/query", params)

    def capture_today(self, rec_trade_id: str) -> Dict[str, Any]:
        """
        Capture specific payment record
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-today-api
        """
        params = {
            "rec_trade_id": rec_trade_id,
        }

        return self.__post_with_partner_key("/tpc/transaction/cap", params)

    def cancel_capture(self, rec_trade_id: str) -> Dict[str, Any]:
        """
        Cancel a specific capture
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-cancel-api
        """
        params = {
            "rec_trade_id": rec_trade_id,
        }

        return self.__post_with_partner_key("/tpc/transaction/cap/cancel", params)

    def get_trade_history(self, rec_trade_id: str) -> Dict[str, Any]:
        """
        Get record and status of a specific transaction
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#trade-history-api
        """
        params = {
            "rec_trade_id": rec_trade_id,
        }

        return self.__post_with_partner_key("/tpc/transaction/trade-history", params)

    def bind_card(
        self,
        prime: str,
        card_holder_data: Models.CardHolderData,
        **kwargs: Any,
    ) -> Dict[str, Any]:
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

        return self.__post_with_partner_key_and_merchant_id("/tpc/card/bind", params)

    def remove_card(self, card_key: str, card_token: str) -> Dict[str, Any]:
        """
        Remove bound credit card
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#remove-card-api
        """
        params = {
            "card_key": card_key,
            "card_token": card_token,
        }

        return self.__post_with_partner_key("/tpc/card/remove", params)

    def cancel_refund(self, rec_trade_id: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Cancel a single refund
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#refund-cancel-api
        """
        params = {
            "rec_trade_id": rec_trade_id,
        }

        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key("/tpc/transaction/refund/cancel", params)

    def __post_with_partner_key(
        self, request_uri: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        params = dict(params, partner_key=self.partner_key)
        return self.__post(request_uri, params)

    def __post_with_partner_key_and_merchant_id(
        self, request_uri: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        params = dict(params, merchant_id=self.merchant_id)
        return self.__post_with_partner_key(request_uri, params)

    def __post(self, request_uri: str, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = f"https://{self.api_host}{request_uri}"
        params = dict(params)

        logger.debug(f"POST to: {uri}")
        logger.debug(f"POST headers: {self.headers}")
        logger.debug(f"POST params: {params}")

        response = requests.post(uri, json=params, headers=self.headers)
        return self.__parse(response)

    def __parse(self, response: requests.Response) -> Optional[Dict[str, Any]]:
        logger.debug(f"response status: {response.status_code}")
        logger.debug(f"response content: {response.content}")

        if response.status_code == 401:
            raise Exceptions.AuthenticationError
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
