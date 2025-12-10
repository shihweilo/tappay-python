from typing import Optional, Dict, Any

class Models:
    """Namespace for TapPay models."""

    class Currencies:
        """Currency constants."""
        TWD = "TWD"

    class CardHolderData:
        """Card holder data model."""

        phone_number: Optional[str] = None
        name: Optional[str] = None
        email: Optional[str] = None
        zip_code: Optional[str] = None
        address: Optional[str] = None
        national_id: Optional[str] = None

        def __init__(
            self,
            phone_number: str,
            name: str,
            email: str,
            zip_code: Optional[str] = None,
            address: Optional[str] = None,
            national_id: Optional[str] = None,
        ):
            self.phone_number = phone_number
            self.name = name
            self.email = email
            self.zip_code = zip_code
            self.address = address
            self.national_id = national_id

        def to_dict(self) -> Dict[str, Any]:
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
