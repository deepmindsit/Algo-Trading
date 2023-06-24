import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from utils.app_utils import PyObjectId


class StockModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    segment: str
    exchange: str
    symbol: str
    stock_name: str
    angel_stock_name: Optional[str] = None
    flat_stock_name: Optional[str] = None
    fyers_stock_name: Optional[str] = None
    instrument_token: str
    exchange_code: str
    fyToken: Optional[str]
    lot_size: int
    strike_price: Optional[int]
    instrument_type: Optional[str]
    option_type: Optional[str]
    expiry_date: Optional[int]
    sector: Optional[str] = ""
    is_subscribed: Optional[bool] = True
    last_traded_price: Optional[float] = 0.0
    last_traded_time: Optional[str] = ""
    last_traded_quantity: Optional[float] = 0.0
    trade_volume: Optional[float] = 0.0
    change_in_price: Optional[float] = 0.0
    change_in_percentage: Optional[float] = 0.0
    open_price: Optional[float] = 0.0
    high_price: Optional[float] = 0.0
    low_price: Optional[float] = 0.0
    close_price: Optional[float] = 0.0
    timestamp: Optional[str] = ""
    status: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "segment": "CASH",
                "exchange": "NSE",
                "stock_name": "Acc",
                "angel_stock_name": "Acc",
                "flat_stock_name": "Acc",
                "fyers_stock_name": "Acc",
                "instrument_token": 1234,
                "exchange_code": 22,
                "lot_size": 50,
                "expiry_date": 0,
                "sector": "Index",
            }
        }


class StockList(BaseModel):
    segment: str
    stock_name: Optional[str]
    from_date: Optional[datetime.date]
    to_date: Optional[datetime.date]

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
                "segment": "FUTURE",
                "stock_name": "Acc | None"
            }
        }
