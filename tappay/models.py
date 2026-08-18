from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Models:
    """Namespace for TapPay models."""

    class Currencies:
        """Currency constants."""

        TWD = "TWD"

    class CardHolderData(BaseModel):
        """Card holder data model using Pydantic v2.

        This model provides automatic validation and serialization
        for cardholder information required by TapPay APIs.
        """

        phone_number: str = Field(..., description="Cardholder's phone number")
        name: str = Field(..., description="Cardholder's full name")
        email: EmailStr = Field(..., description="Cardholder's email address")
        zip_code: Optional[str] = Field(None, description="Cardholder's zip code")
        address: Optional[str] = Field(None, description="Cardholder's address")
        national_id: Optional[str] = Field(None, description="Cardholder's national ID")

        model_config = {
            "json_schema_extra": {
                "examples": [
                    {
                        "phone_number": "0912345678",
                        "name": "Joe Chen",
                        "email": "test@example.com",
                        "zip_code": "100",
                        "address": "台北市中正區",
                        "national_id": "A123456789",
                    }
                ]
            }
        }

        def to_dict(self) -> dict:
            """Convert the model to a dictionary, excluding None values.

            This method maintains backward compatibility with the previous
            implementation while leveraging Pydantic's serialization.

            Returns:
                dict: Dictionary representation with None values excluded
            """
            return self.model_dump(exclude_none=True, by_alias=False)
