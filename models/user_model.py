from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from datetime import date, datetime
from utils.app_utils import AppUtils, PyObjectId


class UserModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    app_id: Optional[str]
    name: str
    mobile_no: str
    email_id: str
    country_name: str
    client_id: Optional[str] = None
    role: Optional[str] = AppUtils.getRole().user
    is_live: Optional[bool] = False
    is_subscribed: Optional[bool] = False
    is_copy_trade: Optional[bool] = False
    is_international: Optional[bool] = False
    referral_code: Optional[str] = ""
    f_id: Optional[str] = ""
    f_token: Optional[str] = ""
    email_verified: Optional[bool] = False
    otp: Optional[int] = 0
    otp_time: Optional[datetime] = datetime.now()
    login_token: Optional[str] = ""
    created_date: Optional[datetime] = datetime.now()
    last_login: Optional[datetime] = datetime.now()
    status: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "",
                "mobile_no": "",
                "email_id": "",
                "country_name": ""
            }
        }


class LoginModel(BaseModel):
    mobile_no: Optional[str]
    email_id: Optional[str]

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "mobile_no": "",
                "email_id": ""
            }
        }


class VerifyEmailModel(BaseModel):
    email_id: str
    token: Optional[str]
    otp: Optional[str]

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "email_id": "",
                "token": ""
            }
        }


class UpdateUserModel(BaseModel):
    name: Optional[str] = None
    mobile_no: Optional[str] = None
    email_id: Optional[str] = None
    country_name: Optional[str] = None
    role: Optional[str] = None
    is_live: Optional[bool] = None
    is_copy_trade: Optional[bool] = None
    referral_code: Optional[str] = None
    status: Optional[int] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "",
                "mobile_no": "",
                "email_id": "",
                "country_name": "",
                "role": "",
                "is_live": "",
                "is_copy_trade": "",
                "referral_code": "",
                "status": "",
            }
        }


class ListUserModel(BaseModel):
    offset: int
    limit: int
    role: Optional[str] = None
    subscription: Optional[int] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "offset": 0,
                "limit": 10,
                "role": "USER/ADVISOR/ADMIN",
                "type": "0/1"
            }
        }


class UpdateFCMModel(BaseModel):
    f_id: Optional[str] = ""
    f_token: Optional[str] = ""
    login_token: Optional[str] = ""
    last_login: Optional[datetime] = datetime.now()

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "f_id": "",
                "f_token": "",
                "login_token": "",
            }
        }
