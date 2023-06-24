from datetime import datetime, timedelta
from typing import Any, List

import pandas as pd
from config.auth import AuthHandler
from fastapi import APIRouter
from config.redis_db import RedisDB
from models.stocks_model import StockModel, StockList
from fastapi import APIRouter, Depends
from models.user_model import UserModel
from repository import stocks_repo, strategy_1_repo, account_repo, strategy_repo, websocket_repo
from utils.app_constants import AppConstants
from utils.app_database import AppDatabase
from utils.app_utils import AppUtils
from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event
from fastapi_events.dispatcher import dispatch

from utils.candle_utils import CandleUtils

router = APIRouter(
    prefix=f"/{AppUtils.getSettings().APIVERSION}/api/stock",
    tags=['Stock']
)

auth_handler = AuthHandler()


@router.post('/create')
async def create_stocks(request: List[StockModel], requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await stocks_repo.create(request, requestedUser)

# @router.post('/back-up')
# async def backup(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
#     return await stocks_repo.backup()


@router.post('/test-api')
async def testApi(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    # await stocks_repo.updateFutureContract(requestedUser)
    # await stocks_repo.updateFyersTradeName(requestedUser)
    # await stocks_repo.updateFlatTradeName(requestedUser)
    # response = await strategy_repo.placeLiveOrder(AppUtils.getTradingPlatform().fyers)
    # response = await account_repo.resetToken(requestedUser)
    # response = await websocket_repo.publishWs()
    response = await CandleUtils.getCurrentCandle(1, "1120230831250060")
    # print('-----------------')
    # dispatch("strategy_2", payload={"id": 1})
    # print('-----------------')
    # return response
    # db = await AppUtils.openDb()
    # dbName = AppDatabase.getName().user
    # newFields = {
    #     "country_name": "India",
    #     "is_international": False,
    # }
    # await AppUtils.updateNewField(db, dbName, newFields)
    # candle = CandleUtils.getCandleData(1, 101123062935003)
    # currentCandle = CandleUtils.getCurrentCandle(1, 101123062935003)
    # print(f">>>> {candle}")
    # print(f">>>> {currentCandle}")
    # return True
    return response


@router.delete('/')
async def delete_stock(request: StockList, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await stocks_repo.delete(request, requestedUser)


@router.post('/')
async def list_stock(request: StockList, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await stocks_repo.list(request)
