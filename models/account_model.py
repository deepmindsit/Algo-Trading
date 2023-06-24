from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from datetime import date, datetime
from utils.app_utils import AppUtils, PyObjectId


class AccountModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: Optional[str]
    broker: str
    client_id: str
    api_key: Optional[str]
    api_secret: Optional[str]
    access_token: Optional[str]
    refresh_token: Optional[str]
    token_generated_at: Optional[date]
    trade_status: bool
    paper_trade: bool
    margin: Optional[float] = 0.00
    created_date: Optional[date] = date.today()
    status: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "user_id": "",
                "broker": "",
                "client_id": "",
                "api_key": "",
                "api_secret": "",
                "access_token": "",
                "refresh_token": "",
                "token_generated_at": "",
                "trade_status": False,
                "paper_trade": False,
            }
        }


class UpdateAccountModel(BaseModel):
    app_id: Optional[str]
    broker: str
    client_id: str
    api_key: Optional[str]
    api_secret: Optional[str]
    access_token: Optional[str]
    refresh_token: Optional[str]
    token_generated_at: Optional[date]
    trade_status: Optional[bool]
    paper_trade: Optional[bool]
    margin: Optional[float] = 0.00
    created_date: Optional[date] = date.today()
    status: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "user_id": "",
                "broker": "",
                "client_id": "",
                "api_key": "",
                "api_secret": "",
                "access_token": "",
                "refresh_token": "",
                "token_generated_at": "",
                "trade_status": False,
                "paper_trade": False,
            }
        }


class returnResponseModel(BaseModel):
    status: bool
    message: str


class AuthCodeModel(BaseModel):
    client_id: str
    user_id: Optional[str]
    auth_code: str

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "client_id": "",
                "auth_code": ""
            }
        }
