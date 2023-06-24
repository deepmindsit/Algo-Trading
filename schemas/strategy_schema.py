from typing import List, Optional
from pydantic import BaseModel

# Response


def StrategySettingsModelItem(item) -> dict:
    return {
        "id": item['_id'],
        "strategy_name": item["strategy_name"],
        "premium": item["premium"],
        "is_live": item["is_live"],
        "time_frame": item["time_frame"],
        "status": item["status"],
    }


def StrategySettingsModelItemList(entity) -> list:
    return [StrategySettingsModelItem(item) for item in entity]


def StrategyMapCountModelItem(item) -> dict:
    return {
        "id": item['_id'],
        "strategy_name": item["strategy_name"],
        "map_count": item["map_count"],
        "status": item["status"],
    }


def StrategyMapCountModelItemList(entity) -> list:
    return [StrategyMapCountModelItem(item) for item in entity]


def StrategyMapModelItem(item) -> dict:
    return {
        "id": item['_id'],
        "strategy_id": item["strategy_id"],
        "user_id": item["user_id"],
        "stock_id": item["stock_id"],
        "segment": item["segment"],
        "premimum": item["premimum"],
        "user": item['user'],
        "stock": item['stock'],
        "strategy": item['strategy'],
    }


def StrategyMapsModelItemList(entity) -> list:
    return [StrategyMapModelItem(item) for item in entity]


def OrderModelItem(item) -> dict:
    return {
        "id": item['_id'],
        "client_id": item["client_id"],
        "trading_platform": item["trading_platform"],
        "order_type": item["order_type"],
        "quantity": item["quantity"],
        "entry_price": item["entry_price"],
        "exit_price": item["exit_price"],
        "order_time": item['order_time'],
        "status": item['status'],
    }


def StrategyModelItem(item) -> dict:
    return {
        "id": item['_id'],
        "strategy_setting_id": item["strategy_setting_id"],
        "strategy_name": item["strategy_name"],
        "stock_id": item["stock_id"],
        "segment": item["segment"],
        "exchange": item["exchange"],
        "stock_name": item["stock_name"],
        "angel_stock_name": item["angel_stock_name"],
        "instrument_token": item["instrument_token"],
        "exchange_code": item["exchange_code"],
        "fyToken": item["fyToken"],
        "order_type": item["order_type"],
        "lot_size": item["lot_size"],
        "high": item["high"],
        "entry": item["entry"],
        "target": item["target"],
        "sl": item["sl"],
        "tsl": item["tsl"],
        "quantity": item["quantity"],
        "profit_loss": item["profit_loss"],
        "ltp": item["ltp"],
        "change_in_percentage": item["change_in_percentage"],
        "change_in_price": item["change_in_price"],
        "is_entry": item["is_entry"],
        "entry_at": item["entry_at"],
        "entry_price": item["entry_price"],
        "is_exit": item["is_exit"],
        "exit_at": item["exit_at"],
        "exit_price": item["exit_price"],
        "created_at": item["created_at"],
        "status": item["status"],
        "order": item['order']
    }


def StrategyModelItemList(entity) -> list:
    return [StrategyModelItem(item) for item in entity]
