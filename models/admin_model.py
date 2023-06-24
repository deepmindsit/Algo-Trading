from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from utils.app_utils import PyObjectId


class UserFilterModel(BaseModel):
    offset: Optional[int]
    limit: Optional[int]
    role: Optional[str]
    is_live: Optional[bool]
    is_subscribed: Optional[bool]
    is_copy_trade: Optional[bool]
    referral_code: Optional[str]
    from_date: Optional[date]
    to_date: Optional[date]
    status: Optional[int]

    @validator("from_date", pre=True)
    def parse_from_date(cls, value):
        if value is not None:
            return datetime.strptime(
                value,
                "%Y-%m-%d"
            ).date()
        else:
            return None

    @validator("to_date", pre=True)
    def parse_to_date(cls, value):
        if value is not None:
            return datetime.strptime(
                value,
                "%Y-%m-%d"
            ).date()
        else:
            return None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "role": "",
                "is_live": "",
                "is_subscribed": "",
                "is_copy_trade": "",
                "referral_code": "",
                "from_date": "",
                "to_date": "",
                "status": 0,
            }
        }
