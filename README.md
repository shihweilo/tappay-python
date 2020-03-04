TapPay Client Library for Python
===============================

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

This is the Python client library for TapPay's Backend API. To use it you'll
need a TapPay account. Sign up at [tappaysdk.com][signup].

* [Installation](#installation)
* [Usage](#usage)
* [Backend API](#backend-api)
* [License](#license)


Installation
------------

To install the Python client library using pip:

    pip install tappay

To upgrade your installed client library using pip:

    pip install tappay --upgrade

Alternatively, you can clone the repository via the command line:

    git clone git@github.com:shihweilo/tappay-python.git

or by opening it on GitHub desktop.


Usage
-----

Begin by importing the `tappay` module:

```python
import tappay
```

Then construct a client object with your `partner_key` and `merchant_id`:

```python
client = tappay.Client(is_sandbox, partner_key, merchant_id)
```

For production, you can specify the `TAPPAY_PARTNER_KEY` and `TAPPAY_MERCHANT_ID`
environment variables instead of specifying the key and secret explicitly.

You will have to provide a boolean flag `is_sandbox` as first parameter 
to indicate if using sandbox(test) environment.


## Backend API

### Make a payment by prime token

```python

card_holder_data = tappay.Models.CardHolderData(phone, name, email)
response_data_dict = client.pay_by_prime(prime_token, amount, payment_details, card_holder_data)
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/back.html#pay-by-prime-api](https://docs.tappaysdk.com/tutorial/zh/back.html#pay-by-prime-api)

### Make a payment by card token

```python

response_data_dict = client.pay_by_token(card_key, card_token, amount, payment_details)
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/back.html#pay-by-card-token-api](https://docs.tappaysdk.com/tutorial/zh/back.html#pay-by-card-token-api)

### Refund

```python
response_data_dict = client.refund(rec_trade_id, refund_amount)
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/back.html#refund-api](https://docs.tappaysdk.com/tutorial/zh/back.html#refund-api)

### Cancel Refund

```python
response_data_dict = client.cancel_refund(rec_trade_id)
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/advanced.html#refund-cancel-api](https://docs.tappaysdk.com/tutorial/zh/advanced.html#refund-cancel-api)

### Get payment record

```python
response_data_dict = client.get_records({
    "bank_transaction_id": bank_transaction_id
})
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/back.html#record-api](https://docs.tappaysdk.com/tutorial/zh/back.html#record-api)

### Capture payment

```python
response_data_dict = client.capture_today(rec_trade_id)
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-today-api](https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-today-api)

### Cancel Capture

```python
response_data_dict = client.cancel_capture(rec_trade_id)
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-cancel-api](https://docs.tappaysdk.com/tutorial/zh/advanced.html#cap-cancel-api)

### Get transaction record

```python
response_data_dict = client.get_trade_history(rec_trade_id)
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/advanced.html#trade-history-api](https://docs.tappaysdk.com/tutorial/zh/advanced.html#trade-history-api)

### Bind card

```python
response_data_dict = client.bind_card(prime, card_holder_data)
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/advanced.html#bind-card-api](https://docs.tappaysdk.com/tutorial/zh/advanced.html#bind-card-api)

### Remove card

```python
response_data_dict = client.remove_card(card_key, card_token
```

Docs: [https://docs.tappaysdk.com/tutorial/zh/advanced.html#remove-card-api](https://docs.tappaysdk.com/tutorial/zh/advanced.html#remove-card-api)


License
-------

This library is released under the [MIT License][license].

[signup]: https://www.tappaysdk.com
[license]: LICENSE.txt
