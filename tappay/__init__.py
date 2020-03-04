import sys
import os
import logging
from platform import python_version

import requests

if sys.version_info[0] == 3:
    string_types = (str, bytes)
    from urllib.parse import urlparse

else:
    string_types = (unicode, str)
    from urlparse import urlparse

try:
    from json import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


logger = logging.getLogger("tappay")

__version__ = '0.4.0'


class Exceptions(object):

    class Error(Exception):
        pass

    class ClientError(Error):
        pass

    class ServerError(Error):
        pass

    class AuthenticationError(ClientError):
        pass


class Models(object):

    class Currencies(object):
        TWD = "TWD"

    class CardHolderData(object):

        phone_number = None
        name = None
        email = None
        zip_code = None
        address = None
        national_id = None

        def __init__(self,
                     phone_number, name, email,
                     zip_code=None, address=None, national_id=None):

            self.phone_number = phone_number
            self.name = name
            self.email = email
            self.zip_code = zip_code
            self.address = address
            self.national_id = national_id

        def to_dict(self):

            result_dict = {
                "phone_number": self.phone_number,
                "name": self.name,
                "email": self.email,
            }

            if self.zip_code:
                result_dict["zip_code"] = self.zip_code
            if self.address:
                result_dict["address"] = self.address
            if self.national_id:
                result_dict["national_id"] = self.national_id

            return result_dict


class Client(object):

    def __init__(self,
                 is_sandbox,
                 partner_key=None,
                 merchant_id=None,
                 app_name=None,
                 app_version=None
                 ):

        """
        Create a Client object to start making calls to TapPay APIs.
        :param bool is_sandbox: Define runtime environment (sandbox or production)
        :param str partner_key: Your TapPay partner key (optional)
        :param str merchant_id: Your TapPay merchant ID (optional)
        :param str app_name: This optional value is added to the user-agent header
        :param str app_name: This optional value is added to the user-agent header
        """

        # Parameter validations

        if not isinstance(is_sandbox, bool):
            raise TypeError("expected bool for parameter `is_sandbox`, "
                            "{} found".format(type(is_sandbox)))

        self.partner_key = partner_key or os.environ.get('TAPPAY_PARTNER_KEY', None)
        self.merchant_id = merchant_id or os.environ.get('TAPPAY_MERCHANT_ID', None)

        if self.partner_key is None:
            raise ValueError("Missing required value for `partner_key`")
        if self.merchant_id is None:
            raise ValueError("Missing required value for `merchant_id`")

        # Set API endpoint for given environment

        subdomain = "sandbox" if is_sandbox else "prod"
        self.api_host = '{}.tappaysdk.com'.format(subdomain)

        # Setup API request headers

        user_agent = 'tappay-python/{} python/{}'.format(__version__,
                                                         python_version())

        # Set optional app-metadata in user-agent if specified
        if app_name and app_version:
            user_agent += ' {}/{}'.format(app_name, app_version)

        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': user_agent,
            'x-api-key': self.partner_key,
        }

    def pay_by_prime(self,
                     prime,
                     amount,
                     details,
                     card_holder_data,
                     **kwargs):

        """
        Make a payment using "prime" obtained from TapPay frontend SDK
        Ref: https://docs.tappaysdk.com/tutorial/zh/back.html#pay-by-prime-api
        :param str prime: The "prime token"
        :param int amount: Payment amount
        :param str details: detailed description of the transaction
        :param CardHolderData card_holder_data: Info of card holder
        """

        # validate parameter types
        if not isinstance(card_holder_data, Models.CardHolderData):
            raise TypeError(
                "expected `CardHolderData` type for "
                "parameter `card_holder_data`, {} found".format(
                    type(card_holder_data)))

        params = {
          "prime": prime,
          "amount": amount,
          "currency": Models.Currencies.TWD,
          "details": details,
          "cardholder": card_holder_data.to_dict(),
        }

        # add additional keyword arguments
        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key_and_merchant_id(
            '/tpc/payment/pay-by-prime',
            params
        )

    def pay_by_token(self,
                     card_key,
                     card_token,
                     amount,
                     details,
                     **kwargs):

        """
        Make a payment using previously obtained card secrets (key & token)
        Ref: https://docs.tappaysdk.com/tutorial/zh/back.html#pay-by-card-token-api
        :param str card_key: Previously obtained card-key
        :param str card_token: Previously obtained card-token
        :param int amount: Payment amount
        :param str details: detailed description of the transaction
        """

        params = {
            "card_key": card_key,
            "card_token": card_token,
            "amount": amount,
            "currency": Models.Currencies.TWD,
            "details": details,
        }

        # add additional keyword arguments
        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key_and_merchant_id(
            '/tpc/payment/pay-by-token',
            params
        )

    def refund(self, rec_trade_id, amount, **kwargs):

        """
        Refund a payment
        Ref: https://docs.tappaysdk.com/tutorial/zh/back.html#refund-api
        :param str rec_trade_id: Transaction record ID from TapPay
        :param int amount: Refund amount
        """

        params = {
            "rec_trade_id": rec_trade_id,
            "amount": amount,
        }

        # add additional keyword arguments
        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key('/tpc/transaction/refund', params)

    def get_records(self,
                    filters_dict,
                    page=0, records_per_page=50,
                    order_by_dict=None):

        """
        Query historical records
        Ref: https://docs.tappaysdk.com/tutorial/zh/back.html#record-api
        :param dict filters_dict: Filter dict defined by TapPay
        :param int page: Target page number
        :param records_per_page: Records per page
        :param dict order_by_dict: Sort by dict defined by TapPay
        """

        params = {
            "records_per_page": records_per_page,
            "page": page,
            "filters": filters_dict,
        }

        if order_by_dict:
            params["order_by"] = order_by_dict

        return self.__post_with_partner_key('/tpc/transaction/query', params)

    # Advanced features

    def capture_today(self, rec_trade_id):

        """
        Capture specific payment record
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-today-api
        :param str rec_trade_id: Transaction record ID from TapPay
        """

        params = {
            "rec_trade_id": rec_trade_id,
        }

        return self.__post_with_partner_key('/tpc/transaction/cap', params)

    def cancel_capture(self, rec_trade_id):

        """
        Cancel a specific capture
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-cancel-api
        :param str rec_trade_id: Transaction record ID from TapPay
        """

        params = {
            "rec_trade_id": rec_trade_id,
        }

        return self.__post_with_partner_key(
            '/tpc/transaction/cap/cancel',
            params
        )

    def get_trade_history(self, rec_trade_id):

        """
        Get record and status of a specific transaction
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#trade-history-api
        :param str rec_trade_id: Transaction record ID from TapPay
        """

        params = {
            "rec_trade_id": rec_trade_id,
        }

        return self.__post_with_partner_key(
            '/tpc/transaction/trade-history',
            params
        )

    def bind_card(self,
                  prime,
                  card_holder_data,
                  **kwargs):

        """
        Bind new credit card
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#bind-card-api
        :param str prime: The "prime token"
        :param CardHolderData card_holder_data: Info of card holder
        """

        # validate parameter types
        if not isinstance(card_holder_data, Models.CardHolderData):
            raise TypeError(
                "expected `CardHolderData` type for "
                "parameter `card_holder_data`, {} found".format(
                    type(card_holder_data)))

        params = {
            "prime": prime,
            "currency": Models.Currencies.TWD,
            "cardholder": card_holder_data.to_dict(),
        }

        # add additional keyword arguments
        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key_and_merchant_id(
            '/tpc/card/bind',
            params
        )

    def remove_card(self,
                    card_key,
                    card_token):

        """
        Remove bound credit card
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#remove-card-api
        :param str card_key: Card key
        :param str card_token: Card token
        """

        params = {
            "card_key": card_key,
            "card_token": card_token,
        }

        return self.__post_with_partner_key(
            '/tpc/card/remove',
            params
        )

    def cancel_refund(self, rec_trade_id, **kwargs):

        """
        Cancel a single refund
        Ref: https://docs.tappaysdk.com/tutorial/zh/advanced.html#refund-cancel-api
        :param str rec_trade_id: Transaction record ID from TapPay
        """

        params = {
            "rec_trade_id": rec_trade_id,
        }

        # add additional keyword arguments
        if kwargs:
            params.update(**kwargs)

        return self.__post_with_partner_key(
            '/tpc/transaction/refund/cancel',
            params
        )

    # Utility methods

    def __post_with_partner_key(self, request_uri, params):

        params = dict(params, partner_key=self.partner_key)
        return self.__post(request_uri, params)

    def __post_with_partner_key_and_merchant_id(self, request_uri, params):

        params = dict(params, merchant_id=self.merchant_id)
        return self.__post_with_partner_key(request_uri, params)

    def __post(self, request_uri, params):

        uri = 'https://' + self.api_host + request_uri

        params = dict(params)

        logger.debug("POST to: {}".format(uri))
        logger.debug("POST headers: {}".format(self.headers))
        logger.debug("POST params: {}".format(params))

        return self.__parse(requests.post(uri,
                                          json=params,
                                          headers=self.headers))

    def __parse(self, response):

        logger.debug("response status: {}".format(response.status_code))
        logger.debug("response content: {}".format(response.content))

        if response.status_code == 401:
            raise Exceptions.AuthenticationError
        elif response.status_code == 204:
            return None
        elif 200 <= response.status_code < 300:
            return response.json()
        elif 400 <= response.status_code < 500:
            message = "{code} response from {host}".format(
                code=response.status_code, host=self.api_host)
            raise Exceptions.ClientError(message)
        elif 500 <= response.status_code < 600:
            message = "{code} response from {host}".format(
                code=response.status_code, host=self.api_host)
            raise Exceptions.ServerError(message)
