from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from utils.app_utils import PyObjectId


class StrategyModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    strategy_setting_id: str
    stock_id: str
    segment: str
    exchange: str
    stock_name: str
    angel_stock_name: Optional[str] = None
    instrument_token: Optional[str]
    exchange_code: str
    order_type: str
    lot_size: int
    high: float
    entry: float
    target: float
    sl: float
    profit_loss: Optional[float] = 0.0
    is_entry: Optional[bool] = False
    is_exit: Optional[bool] = False
    entry_at: Optional[datetime]
    exit_at: Optional[datetime]
    created_at: Optional[datetime] = datetime.now()
    status: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "strategy_setting_id": "",
                "stock_id": "",
                "segment": "",
                "exchange": "",
                "stock_name": "",
                "angel_stock_name": "",
                "instrument_token": 0,
                "exchange_code": 0,
                "order_type": "",
                "lot_size": 0,
                "high": "",
                "entry": "",
                "target": "",
                "sl": "",
                "profit_loss": "",
            }
        }


class OrderModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    strategy_id: str
    trading_platform: str
    client_id: str
    order_id: str
    order_type: str
    quantity: int
    price: float
    order_time: Optional[datetime] = datetime.now()
    status: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "user_id": "",
                "strategy_id": "",
                "trading_platform": "",
                "client_id": "",
                "order_id": "",
                "order_type": "",
                "quantity": "",
                "price": "",
                "order_time": "",
            }
        }


class StrategySettingsModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    strategy_name: str
    premium: int
    is_live: Optional[bool] = False
    time_frame: str
    status: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "strategy_name": "",
                "premium": 0,
                "is_live": "",
                "time_frame": "",
            }
        }


class StrategyUpdateSettingsModel(BaseModel):
    strategy_name: str
    premium: float
    is_live: Optional[bool] = False
    time_frame: str
    status: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "strategy_name": "",
                "premium": 0,
                "is_live": "",
                "time_frame": "",
            }
        }


class StrategyFilterModel(BaseModel):
    user_id: Optional[str]
    is_admin: Optional[bool]
    segment: Optional[str]
    strategy_id: Optional[str]
    stock_name: Optional[str]
    order_type: Optional[str]
    status: Optional[int]
    from_date: Optional[date]
    to_date: Optional[date]

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
                "is_admin": "",
                "segment": "",
                "strategy_id": "",
                "stock_name": "",
                "order_type": "",
                "status": 0,
                "from_date": "",
                "to_date": ""
            }
        }


class MapStrategyModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    strategy_id: str
    user_id: str
    stock_id: str
    segment: str
    premimum: str

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "strategy_id": "",
                "user_id": "",
                "stock_id": "",
                "segment": "",
                "premimum": "",
            }
        }


class UpdateMapStrategyModel(BaseModel):
    strategy_id: Optional[str]
    user_id: Optional[str]
    stock_id: Optional[str]
    segment: Optional[str]
    premimum: Optional[str]

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "strategy_id": "",
                "user_id": "",
                "stock_id": "",
                "segment": "",
                "premimum": "",
            }
        }


class CreateEntryModel(BaseModel):
    fy_token: str
    entry: float
    sl: float
    target: float
    is_international: bool

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "fy_token": "",
                "entry": 0,
                "sl": 0,
                "target": 0,
                "is_international": False,
            }
        }


class EditEntryModel(BaseModel):
    id: str
    sl: float
    target: float
    is_international: bool

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "id": "",
                "sl": 0,
                "target": 0,
                "is_international": False,
            }
        }


class ExitOrderModel(BaseModel):
    strategy_id: Optional[str] = None
    order_id: Optional[str] = None
    user_id: Optional[str] = None
    is_admin: Optional[bool] = False

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "strategy_id": "",
                "order_id": "",
                "user_id": "",
                "is_admin": False,
            }
        }
