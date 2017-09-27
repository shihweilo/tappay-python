# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals, print_function

import os, warnings, hashlib, hmac, time, uuid, sys
import logging
from platform import python_version

import requests


logger = logging.getLogger(__name__)

__version__ = '0.0.2'

if sys.version_info[0] == 3:
    string_types = (str, bytes)
else:
    string_types = (unicode, str)


class Currencies(object):

    TWD = "TWD"


class CardHolderData(object):
    
    phone_number = None
    name = None
    email = None
    zip = None
    address = None
    national_id = None
    
    def __init__(self, phone_number, name, email, zip_=None, address=None, national_id=None):
        
        self.phone_number = phone_number
        self.name = name
        self.email = email
        self.zip = zip_
        self.address = address
        self.national_id = national_id

    def to_dict(self):

        result_dict = {
            "phonenumber": self.phone_number,
            "name": self.name,
            "email": self.email,
        }

        if self.zip:
            result_dict["zip"] = self.zip
        if self.address:
            result_dict["addr"] = self.address
        if self.national_id:
            result_dict["nationalid"] = self.national_id

        return result_dict


class Error(Exception):
    pass


class ClientError(Error):
    pass


class ServerError(Error):
    pass


class AuthenticationError(ClientError):
    pass


class Client(object):

    def __init__(self, partner_key, merchant_id, is_sandbox, **kwargs):

        # self.app_id = kwargs.get('app_id', None) or os.environ.get('TAPPAY_APP_ID', None)
        # self.app_key = kwargs.get('app_key', None) or os.environ.get('TAPPAY_APP_KEY', None)
        # self.signature_secret = kwargs.get('signature_secret', None) or os.environ.get('NEXMO_SIGNATURE_SECRET', None)
        # self.application_id = kwargs.get('application_id', None)
        # self.private_key = kwargs.get('private_key', None)

        self.partner_key = partner_key
        self.merchant_id = merchant_id

        if is_sandbox:
            subdomain = "sandbox"
        else:
            subdomain = "prod"

        self.api_host = '{}.tappayapis.com'.format(subdomain)

        user_agent = 'tappay-python/{0}/{1}'.format(__version__, python_version())

        if 'app_name' in kwargs and 'app_version' in kwargs:
            user_agent += '/{0}/{1}'.format(kwargs['app_name'], kwargs['app_version'])

        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': user_agent,
            'x-api-key': self.partner_key,
        }

        self.auth_params = {}

    def pay_by_prime_token(self, prime, amount, details, card_holder_data, remember, partner_trade_id=None):

        # validate parameter types
        if not isinstance(card_holder_data, CardHolderData):
            raise TypeError("expected `CardHolderData` type for parameter `card_holder_data`, {} found".format(type(card_holder_data)))

        if not isinstance(amount, int):
            raise TypeError("expected int for parameter `amount`, {} found".format(type(amount)))

        if not isinstance(remember, bool):
            raise TypeError("expected bool for parameter `remember`, {} found".format(type(remember)))

        if not isinstance(details, string_types):
            raise TypeError("expected string for parameter `details`, {} found".format(type(details)))

        # validate parameter value
        if amount <= 0:
            raise ValueError("parameter `amount` must be positive")

        # validate parameter length
        if len(details) > 100:
            raise ValueError("parameter `details` length must be <= 100")

        if partner_trade_id and len(partner_trade_id) > 50:
            raise ValueError("parameter `partner_trade_id` length must be <= 50")

        params = {
          "prime": prime,
          "partnerkey": self.partner_key,
          "merchantid": self.merchant_id,
          "amount": amount,
          "currency": Currencies.TWD,
          "details": details,
          "cardholder": card_holder_data.to_dict(),
          "instalment": 0,
          "remember": remember
        }

        if partner_trade_id:
            params["ptradeid"] = partner_trade_id

        return self.__post('/tpc/partner/directpay/paybyprime', params)

    def pay_by_card_token(self, params):
        raise NotImplementedError

    def refund(self, rec_trade_id, amount):

        # validate parameter types
        if not isinstance(rec_trade_id, string_types):
            raise TypeError("expected string for parameter `rec_trade_id`, {} found".format(
                type(rec_trade_id)))

        if not isinstance(amount, int):
            raise TypeError("expected int for parameter `amount`, {} found".format(type(amount)))

        # validate parameter value
        if amount <= 0:
            raise ValueError("parameter `amount` must be positive")

        params = {
            "partnerkey": self.partner_key,
            "rectradeid": rec_trade_id,
            "amount": amount,
        }

        return self.__post('/tpc/partner/fastrefund', params)

    def get_records(self, filters_dict=None, page_zero_indexed=0, records_per_page=50):

        # validate parameter types
        if not isinstance(page_zero_indexed, int):
            raise TypeError("expected int for parameter `page_zero_indexed`, {} found".format(type(page_zero_indexed)))

        if not isinstance(records_per_page, int):
            raise TypeError("expected int for parameter `records_per_page`, {} found".format(type(records_per_page)))

        # validate parameter value
        if page_zero_indexed < 0:
            raise ValueError("parameter `page_zero_indexed` must be >= 0")

        if not 1 <= records_per_page <= 200:
            raise ValueError("parameter `records_per_page` must be between 1 and 200")

        params = {
            "partnerkey": self.partner_key,
            "recordsperpage": records_per_page,
            "page": page_zero_indexed,
        }

        if filters_dict:
            params["filters"] = filters_dict

        return self.__post('/tpc/partner/getrecordsplus', params)

    def capture_today(self, params):
        raise NotImplementedError

    def __post(self, request_uri, params):

        uri = 'https://' + self.api_host + request_uri

        params = dict(params)

        logger.debug("uri: {}".format(uri))
        logger.debug("POST headers: {}".format(self.headers))
        logger.debug("POST params: {}".format(params))

        return self.__parse(requests.post(uri, json=params, headers=self.headers))

    def __parse(self, response):

        logger.debug(response.status_code)
        logger.debug(response.content)

        if response.status_code == 401:
            raise AuthenticationError
        elif response.status_code == 204:
            return None
        elif 200 <= response.status_code < 300:
            return response.json()
        elif 400 <= response.status_code < 500:
            message = "{code} response from {host}".format(code=response.status_code, host=self.api_host)

            raise ClientError(message)
        elif 500 <= response.status_code < 600:
            message = "{code} response from {host}".format(code=response.status_code, host=self.api_host)

            raise ServerError(message)
