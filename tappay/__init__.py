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


logger = logging.getLogger(__name__)

__version__ = '0.2.0'


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

        self.auth_params = {}

    def pay_by_prime(self,
                     prime,
                     amount,
                     details,
                     card_holder_data,
                     order_number=None,
                     bank_transaction_id=None,
                     instalment=0,
                     delay_capture_in_days=0,
                     remember=False):

        # validate parameter types
        if not isinstance(card_holder_data, Models.CardHolderData):
            raise TypeError("expected `CardHolderData` type for "
                            "parameter `card_holder_data`, {} found".format(
                type(card_holder_data)))

        if not isinstance(amount, int):
            raise TypeError("expected int for parameter `amount`, "
                            "{} found".format(type(amount)))

        if not isinstance(remember, bool):
            raise TypeError("expected bool for parameter `remember`, "
                            "{} found".format(type(remember)))

        if not isinstance(details, string_types):
            raise TypeError("expected string for parameter `details`, "
                            "{} found".format(type(details)))

        # validate parameter value
        if amount <= 0:
            raise ValueError("parameter `amount` must be positive")

        # validate parameter length
        if len(details) >= 100:
            raise ValueError("parameter `details` length must be <= 100")

        if order_number and len(order_number) >= 50:
            raise ValueError("parameter `order_number` length must be <= 50")

        params = {
          "prime": prime,
          "partner_key": self.partner_key,
          "merchant_id": self.merchant_id,
          "amount": amount,
          "currency": Models.Currencies.TWD,
          "details": details,
          "cardholder": card_holder_data.to_dict(),
          "instalment": 0,
          "remember": remember
        }

        if order_number:
            params["order_number"] = order_number

        if bank_transaction_id:
            params["bank_transaction_id"] = bank_transaction_id

        if delay_capture_in_days > 0:
            params["delay_capture_in_days"] = delay_capture_in_days

        if instalment > 0:
            params["instalment"] = instalment

        return self.__post('/tpc/payment/pay-by-prime', params)

    def pay_by_token(self, params):
        raise NotImplementedError

    def refund(self, rec_trade_id, amount, bank_refund_id=None):

        # validate parameter types
        if not isinstance(rec_trade_id, string_types):
            raise TypeError("expected string for parameter `rec_trade_id`, "
                            "{} found".format(type(rec_trade_id)))

        if not isinstance(amount, int):
            raise TypeError("expected int for parameter `amount`, "
                            "{} found".format(type(amount)))

        # validate parameter value
        if amount <= 0:
            raise ValueError("parameter `amount` must be positive")

        params = {
            "partner_key": self.partner_key,
            "rec_trade_id": rec_trade_id,
            "amount": amount,
        }

        if bank_refund_id:
            params["bank_refund_id"] = bank_refund_id

        return self.__post('/tpc/transaction/refund', params)

    def get_records(self,
                    filters_dict,
                    page=0, records_per_page=50,
                    order_by_dict=None):

        # validate parameter types
        if not isinstance(page, int):
            raise TypeError("expected int for parameter `page`, "
                            "{} found".format(type(page)))

        if not isinstance(records_per_page, int):
            raise TypeError("expected int for parameter `records_per_page`, "
                            "{} found".format(type(records_per_page)))

        # validate parameter value
        if page < 0:
            raise ValueError("parameter `page_zero_indexed` must be >= 0")

        if not 1 <= records_per_page <= 200:
            raise ValueError("parameter `records_per_page` must be "
                             "between 1 and 200")

        params = {
            "partner_key": self.partner_key,
            "records_per_page": records_per_page,
            "page": page,
        }

        if filters_dict:
            params["filters"] = filters_dict

        if order_by_dict:
            params["order_by"] = order_by_dict

        return self.__post('/tpc/transaction/query', params)

    # Advanced features

    def capture_today(self, rec_trade_id):
        params = {
            "partner_key": self.partner_key,
            "rec_trade_id": rec_trade_id,
        }

        return self.__post('/tpc/transaction/cap', params)

    def get_trade_history(self, rec_trade_id):
        params = {
            "partner_key": self.partner_key,
            "rec_trade_id": rec_trade_id,
        }

        return self.__post('/tpc/transaction/trade-history', params)

    # Utility methods

    def __post(self, request_uri, params):

        uri = 'https://' + self.api_host + request_uri

        params = dict(params)

        logger.debug("uri: {}".format(uri))
        logger.debug("POST headers: {}".format(self.headers))
        logger.debug("POST params: {}".format(params))

        return self.__parse(requests.post(uri,
                                          json=params,
                                          headers=self.headers))

    def __parse(self, response):

        # logger.debug(response.status_code)
        # logger.debug(response.content)

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
