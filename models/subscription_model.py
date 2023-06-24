from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from utils.app_utils import PyObjectId


class PlanModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    plan_name: str
    price: str
    period_in_days: str
    offer: Optional[str] = None
    offer_start_date: Optional[date] = None
    offer_end_date: Optional[date] = None
    description: str
    created_at: Optional[datetime] = datetime.now()
    status: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "plan_name": "",
                "price": "",
                "period_in_days": "",
                "offer": "",
                "offer_start_date": "",
                "offer_end_date": "",
                "description": "",
            }
        }


class UpdatePlanModel(BaseModel):
    plan_name: Optional[str]
    price: Optional[str]
    period_in_days: Optional[str]
    offer: Optional[str]
    offer_start_date: Optional[date]
    offer_end_date: Optional[date]
    description: Optional[str]
    status: Optional[int]

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "plan_name": "",
                "price": "",
                "period_in_days": "",
                "offer": "",
                "offer_start_date": "",
                "offer_end_date": "",
                "description": "",
            }
        }


class PlanFilterModel(BaseModel):
    period_in_days: Optional[str]
    offer_start_date: Optional[date]
    offer_end_date: Optional[date]
    status: Optional[int]

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "period_in_days": "",
                "offer_start_date": "",
                "offer_end_date": "",
                "status": 0,
            }
        }


class SubscriptionModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    plan_id: str
    from_date: Optional[date]
    to_date: Optional[date]
    status: Optional[int] = 0

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
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "user_id": "",
                "plan_id": "",
                "from_date": "",
                "to_date": "",
                "status": 0,
            }
        }


class SubscriptionFilterModel(BaseModel):
    user_id: Optional[str]
    plan_id: Optional[str]
    from_date: Optional[date]
    to_date: Optional[date]
    status: Optional[int] = 0

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
                "user_id": "",
                "plan_id": "",
                "from_date": "",
                "to_date": "",
                "status": 0,
            }
        }
