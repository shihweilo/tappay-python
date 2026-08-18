#!/usr/bin/env python3
"""
Example demonstrating Pydantic v2 validation in TapPay SDK.

This example shows how Pydantic v2 provides automatic validation
and helpful error messages when creating CardHolderData objects.
"""

from pydantic import ValidationError

from tappay import Client, Models


def example_valid_cardholder():
    """Example of creating a valid CardHolderData object."""
    print("=" * 60)
    print("Example 1: Valid CardHolderData")
    print("=" * 60)

    card_holder = Models.CardHolderData(
        phone_number="0912345678",
        name="Wang Xiao Ming",
        email="test@example.com",
        zip_code="100",
        address="台北市中正區",
    )

    print("✓ CardHolderData created successfully!")
    print(f"  Name: {card_holder.name}")
    print(f"  Email: {card_holder.email}")
    print(f"  Phone: {card_holder.phone_number}")
    print()

    # Convert to dictionary (for API calls)
    data_dict = card_holder.to_dict()
    print(f"✓ Serialized to dict: {data_dict}")
    print()


def example_invalid_email():
    """Example showing email validation."""
    print("=" * 60)
    print("Example 2: Invalid Email Validation")
    print("=" * 60)

    try:
        _card_holder = Models.CardHolderData(
            phone_number="0912345678",
            name="Wang Xiao Ming",
            email="invalid-email",  # Invalid email format
        )
    except ValidationError as e:
        print("✗ Validation failed (as expected):")
        print(f"  {e.errors()[0]['msg']}")
        print(f"  Field: {e.errors()[0]['loc'][0]}")
        print()


def example_missing_required_fields():
    """Example showing required field validation."""
    print("=" * 60)
    print("Example 3: Missing Required Fields")
    print("=" * 60)

    try:
        _card_holder = Models.CardHolderData(
            phone_number="0912345678",
            # Missing 'name' and 'email' required fields
        )
    except ValidationError as e:
        print("✗ Validation failed (as expected):")
        for error in e.errors():
            print(f"  Missing field: {error['loc'][0]}")
        print()


def example_optional_fields():
    """Example showing optional fields can be omitted."""
    print("=" * 60)
    print("Example 4: Optional Fields")
    print("=" * 60)

    # Only required fields
    card_holder = Models.CardHolderData(
        phone_number="0912345678",
        name="Wang Xiao Ming",
        email="test@example.com",
    )

    print("✓ CardHolderData created with only required fields")
    data_dict = card_holder.to_dict()
    print(f"  Serialized (None values excluded): {data_dict}")
    print()


def example_with_client():
    """Example showing usage with TapPay client."""
    print("=" * 60)
    print("Example 5: Using with TapPay Client")
    print("=" * 60)

    # Initialize client (sandbox mode)
    client = Client(
        is_sandbox=True,
        partner_key="your_partner_key",
        merchant_id="your_merchant_id",
    )

    # Create validated cardholder data
    _card_holder = Models.CardHolderData(
        phone_number="0912345678",
        name="Wang Xiao Ming",
        email="test@example.com",
    )

    print("✓ Client initialized")
    print("✓ CardHolderData validated and ready for API calls")
    print(f"  API Host: {client.api_host}")
    print()


if __name__ == "__main__":
    print("\n🎯 TapPay SDK - Pydantic v2 Validation Examples\n")

    example_valid_cardholder()
    example_invalid_email()
    example_missing_required_fields()
    example_optional_fields()
    example_with_client()

    print("=" * 60)
    print("✨ All examples completed!")
    print("=" * 60)
