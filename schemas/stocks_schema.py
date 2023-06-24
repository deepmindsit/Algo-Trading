from typing import List, Optional
from pydantic import BaseModel

# Response


def stockModelItem(item) -> dict:
    return {
        "id": item['_id'],
        "segment": item["segment"],
        "exchange": item["exchange"],
        "symbol": item["symbol"],
        "stock_name": item["stock_name"],
        "angel_stock_name": item["angel_stock_name"],
        "instrument_token": item["instrument_token"],
        "exchange_code": item["exchange_code"],
        "fyToken": item["fyToken"],
        "lot_size": item["lot_size"],
        "strike_price": item["strike_price"],
        "instrument_type": item["instrument_type"],
        "option_type": item["option_type"],
        "expiry_date": item["expiry_date"],
        "sector": item["sector"],
        "is_subscribed": item["is_subscribed"],
        "last_traded_price": item["last_traded_price"],
        "last_traded_time": item["last_traded_time"],
        "trade_volume": item["trade_volume"],
        "change_in_price": item["change_in_price"],
        "change_in_percentage": item["change_in_percentage"],
        "open_price": item["open_price"],
        "high_price": item["high_price"],
        "low_price": item["low_price"],
        "close_price": item["close_price"],
        "timestamp": item["timestamp"],
        "status": item["status"],
    }


def stockModelItemList(entity) -> list:
    return [stockModelItem(item) for item in entity]


def stockLimitedItem(item) -> dict:
    return {
        "id": item['_id'],
        "segment": item["segment"],
        "exchange": item["exchange"],
        "stock_name": item["stock_name"],
        "fyers_stock_name": item["fyers_stock_name"],
        "fyToken": item["fyToken"],
        "exchange_code": item["exchange_code"],
        "lot_size": item["lot_size"],
        "strike_price": item["strike_price"],
        "option_type": item["option_type"],
    }
