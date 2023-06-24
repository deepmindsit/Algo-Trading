import json
import math
from fastapi import HTTPException, status, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from config.redis_db import RedisDB
from models.strategy_model import *
from models.user_model import UserModel
from schemas.admin_schema import UserLimited
from schemas.stocks_schema import stockLimitedItem
from schemas.strategy_schema import *
from utils.api_terminal import ApiTerminal
from utils.app_constants import AppConstants
from utils.app_database import AppDatabase
from utils.app_utils import ApiCalls, AppUtils, Requests

import pandas as pd
import numpy as np
import requests
import logging
from datetime import datetime, timedelta


async def createSettings(request: StrategySettingsModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbName = AppDatabase.getName().strategy_setting
        user = await db[dbUser].find_one({'app_id': requestedUser})
        if user is not None and AppUtils.getRole().admin in user['role']:
            if await db[dbName].find_one({'strategy_name': request.strategy_name}) is None:
                await db[dbName].insert_one(jsonable_encoder(request))
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"{request.strategy_name} : added successfully.")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, f"{request.strategy_name} : already added.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def updateSettings(id: str, request: StrategyUpdateSettingsModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbName = AppDatabase.getName().strategy_setting

        user = await db[dbUser].find_one({'app_id': requestedUser})
        if user is not None and AppUtils.getRole().admin in user['role']:
            settings = await db[dbName].find_one({'_id': id})
            if settings is not None:
                await db[dbName].update_one({'_id': id}, {'$set': jsonable_encoder(request)})
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"{settings['strategy_name']} updated successfully.")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy Settings not found.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def mappedUser(requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbStrategy = AppDatabase.getName().strategy_setting
        dbMapStrategy = AppDatabase.getName().map_strategy

        user = await db[dbUser].find_one({'app_id': requestedUser})
        if user is not None and AppUtils.getRole().admin in user['role']:
            strategyList = []
            async for strategy in db[dbStrategy].find({'is_live': True}):
                mapCount = await db[dbMapStrategy].count_documents({'strategy_id': strategy['_id']})
                strategy['map_count'] = mapCount
                strategyList.append(strategy)
            return AppUtils.responseWithData(True, status.HTTP_200_OK, "data fetched successfully", StrategyMapCountModelItemList(strategyList))
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def deleteSettings(id: str, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbName = AppDatabase.getName().strategy_setting

        user = await db[dbUser].find_one({'app_id': requestedUser})
        if user is not None and AppUtils.getRole().admin in user['role']:
            settings = await db[dbName].find_one({'_id': id})
            if settings is not None:
                await db[dbName].delete_one({'_id': id})
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"{settings['strategy_name']} deleted successfully.")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy Settings not found.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def listSettings(requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbName = AppDatabase.getName().strategy_setting

        user = await db[dbUser].find_one({'app_id': requestedUser})
        if user is not None and AppUtils.getRole().admin in user['role']:
            user = await db[dbUser].find_one({'app_id': requestedUser})
            settings = []
            async for setting in db[dbName].find():
                settings.append(setting)
            if len(settings) <= 0:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy Settings not exists.")
            else:
                return AppUtils.responseWithData(True, status.HTTP_200_OK, "Strategy Settings fetched successsfully", StrategySettingsModelItemList(settings))
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def createMap(requestList: List[MapStrategyModel], requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbName = AppDatabase.getName().map_strategy
        user = await db[dbUser].find_one({'app_id': requestedUser})
        if user is not None and AppUtils.getRole().admin in user['role']:
            for request in requestList:
                if await db[dbName].find_one({'strategy_id': request.strategy_id, 'user_id': request.user_id, 'stock_id': request.stock_id}) is None:
                    await db[dbName].insert_one(jsonable_encoder(request))

            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"Mapped successfully.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def deleteMap(id: str, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbName = AppDatabase.getName().map_strategy

        user = await db[dbUser].find_one({'app_id': requestedUser})
        if user is not None and AppUtils.getRole().admin in user['role']:
            strategy = await db[dbName].find_one({'_id': id})
            if strategy is not None:
                await db[dbName].delete_one({'_id': id})
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Strategy mapping removed successfully.")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy mapping not found.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def listMap(filterBy: MapStrategyModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbStock = AppDatabase.getName().model_future
        dbStrategySetting = AppDatabase.getName().strategy_setting
        dbName = AppDatabase.getName().map_strategy

        user = await db[dbUser].find_one({'app_id': requestedUser})
        if user is not None and AppUtils.getRole().admin in user['role']:
            user = await db[dbUser].find_one({'app_id': requestedUser})
            maps = []
            query = {}

            if filterBy is not None:
                if filterBy.strategy_id is not None:
                    query['strategy_id'] = filterBy.strategy_id
                if filterBy.user_id is not None:
                    query['user_id'] = filterBy.user_id
                if filterBy.stock_id is not None:
                    query['stock_id'] = filterBy.stock_id
                if filterBy.segment is not None:
                    query['segment'] = filterBy.segment
                if filterBy.premimum is not None:
                    query['premimum'] = filterBy.premimum

            async for map in db[dbName].find(query):
                user = await db[dbUser].find_one({'_id': map['user_id']})
                stock = await db[dbStock].find_one({'_id': map['stock_id']})
                strategy = await db[dbStrategySetting].find_one({'_id': map['strategy_id']})
                if user is not None:
                    map['user'] = UserLimited(user)
                else:
                    map['user'] = None

                if stock is not None:
                    map['stock'] = stockLimitedItem(stock)
                else:
                    map['stock'] = None

                if stock is not None:
                    map['strategy'] = StrategySettingsModelItem(strategy)
                else:
                    map['strategy'] = None

                maps.append(map)
            if len(maps) <= 0:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy mapping doesn't exists.")
            else:
                return AppUtils.responseWithData(True, status.HTTP_200_OK, "Strategy mapping fetched successsfully", StrategyMapsModelItemList(maps))
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def getHistoricalData():
    try:
        db = await AppUtils.openDb()
        dbFuture = AppDatabase.getName().model_future
        dbSetting = AppDatabase.getName().strategy_setting

        timeFrames = []
        async for setting in db[dbSetting].find({'is_live': True}):
            timeFrames.append(setting['time_frame'].replace("M", ""))

        for timeFrame in timeFrames:
            async for stock in db[dbFuture].find():
                symbol = f"{stock['exchange']}:{stock['stock_name']}"

                logging.info(f"symbol: {symbol} - {timeFrame}")
                await getCandelData(symbol=symbol, timeFrame=timeFrame, exchangeCode=stock['exchange_code'])

                logging.info(f"symbol: {symbol} - 15")
                await getCandelData(symbol=symbol, timeFrame=15, exchangeCode=stock['exchange_code'], level=True)

    except Exception as ex:
        print(f"Error >>: {str(ex)}")
        logging.error(f"Error: {ex}")


async def getCandelData(symbol, timeFrame, exchangeCode, startTime: str = None, endTime: str = None, present: bool = False, level: bool = False, newTimeFrame: int = None):
    try:
        db = await AppUtils.openDb()
        dbAccount = AppDatabase.getName().account
        account = await db[dbAccount].find_one({'client_id': AppUtils.getSettings().FYERS_CLIENT})

        if newTimeFrame is not None:
            resolution = newTimeFrame
        else:
            resolution = timeFrame

        if present:
            # startDate = await AppUtils.combineDateTime((datetime.now() - timedelta(days=1)).strftime("%d %b %y"), "915")
            # endDate = await AppUtils.combineDateTime((datetime.now() - timedelta(days=1)).strftime("%d %b %y"), "1530")

            # startDate = await AppUtils.combineDateTime(AppConstants.currentDayDate, "915")
            # endDate = await AppUtils.combineDateTime(AppConstants.currentDayDate, "1530")

            if startTime is not None:
                startDate = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), startTime)
            else:
                startDate = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "915")

            if endTime is not None:
                endDate = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), endTime)
            else:
                endDate = AppUtils.getCurrentDateTimeStamp()
        else:
            startDate = await AppUtils.combineDateTime(AppConstants.previousDayDate, "915")
            endDate = await AppUtils.combineDateTime(AppConstants.previousDayDate, "1530")

        if account is not None:
            url = f"https://api.fyers.in/data-rest/v2/history/?symbol={symbol}&resolution={resolution}&date_format=0&range_from={startDate}&range_to={endDate}&cont_flag=0"

            accessToken = f"{account['api_key']}:{account['access_token']}"
            header = {"Content-Type": "application/json",
                      "Authorization": accessToken}
            # print(f"url: {url}")
            # print(f"header: {header}")
            # response = await ApiCalls.apiCallHelper(urls=url, http_method=Requests.GET, header=header)
            response = requests.get(url, headers=header, timeout=3)
            logging.info(f"Response: --- {response.json()}")
            if response.status_code == 200:
                candles = response.json()['candles']
                if present:
                    key = f"{AppConstants.candle}{exchangeCode}_{timeFrame}"
                elif level:
                    key = f"{AppConstants.candle}level_{exchangeCode}_{timeFrame}"
                else:
                    key = f"{AppConstants.candle}historical_{exchangeCode}_{timeFrame}"
                RedisDB.setJson(key=key, data=candles)
                return True
            else:
                print(f">> Error : ${response.json()}")
                logging.error(f">> -- Error: {response.json()}")
                return False
        else:
            return False
    except Exception as ex:
        print(f"{str(ex)}")


async def listStrategy(filterBy: StrategyFilterModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbStrategy = AppDatabase.getName().strategy
        dbStrategySetting = AppDatabase.getName().strategy_setting
        dbOrder = AppDatabase.getName().strategy_order

        strategyQuery = {}
        user_id = None

        if filterBy is not None:
            user_id = filterBy.user_id
            if filterBy.strategy_id is not None:
                strategyQuery['strategy_setting_id'] = filterBy.strategy_id
            if filterBy.stock_name is not None:
                strategyQuery['symbol'] = filterBy.stock_name.upper()
            if filterBy.segment is not None:
                strategyQuery['segment'] = filterBy.segment
            if filterBy.status is not None:
                strategyQuery['status'] = filterBy.status

        if user_id is None:
            user = await db[dbUser].find_one({'app_id': requestedUser})
            user_id = user['_id']

        if user_id is not None:
            prevDay = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "000")
            # prevDay = await AppUtils.combineDateTime(AppConstants.currentDayDate, "000")
            strategies = []
            strategyQuery['entry_at'] = {'$not': {'$lte': prevDay}}
            # strategyQuery['symbol'] = "NIFTY"
            async for strgy in db[dbStrategy].find(strategyQuery).sort([('entry_at', -1)]):
                order = await db[dbOrder].find_one(
                    {'strategy_id': strgy['_id'], 'user_id': user_id})
                if order is not None:
                    strategy = jsonable_encoder(strgy)
                    # Get LTP from redis
                    key = f"{AppConstants.stock}{strategy['fyToken']}"
                    stock = RedisDB.getJson(key=key)
                    if stock is not None:
                        strategy['ltp'] = stock['ltp']
                        strategy['change_in_percentage'] = round(
                            (float(stock["ltp"]) - float(stock["close_price"])), 2)
                        strategy['change_in_price'] = round(
                            (float(stock["ltp"]) - float(stock["close_price"]))/float(stock["close_price"] * 100.0), 2)
                    else:
                        strategy['ltp'] = 0.00
                        strategy['change_in_percentage'] = 0.00
                        strategy['change_in_price'] = 0.00
                    strategy['quantity'] = order['quantity']
                    strategy['entry_price'] = order['entry_price']
                    strategy['exit_price'] = order['exit_price']
                    strategy['order'] = OrderModelItem(order)

                    if "entry_at" in order:
                        strategy['entry_at'] = order['entry_at']

                    if "exit_at" in order:
                        strategy['exit_at'] = order['exit_at']

                    strgySetting = await db[dbStrategySetting].find_one({'_id': strategy['strategy_setting_id']})
                    if strgySetting is not None:
                        strategy['strategy_name'] = strgySetting['strategy_name']
                    else:
                        strategy['strategy_name'] = ""
                    strategies.append(strategy)

            if len(strategies) <= 0:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategies not yet generated")
            else:
                return AppUtils.responseWithData(True, status.HTTP_200_OK, "Strategies fetched successsfully", StrategyModelItemList(strategies))
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def listStrategyHistory(request: StrategyFilterModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbStrategy = AppDatabase.getName().strategy
        dbStrategySetting = AppDatabase.getName().strategy_setting
        dbOrder = AppDatabase.getName().strategy_order

        if request.user_id is not None:
            user = await db[dbUser].find_one({'_id': request.user_id})
        else:
            user = await db[dbUser].find_one({'app_id': requestedUser})

        if user is not None:
            strategies = []
            strategyQuery = {}

            if request.from_date is not None:
                strategyQuery['created_at'] = {
                    '$gte': request.from_date.strftime('%Y-%m-%d'),
                }
            if request.to_date is not None:
                if request.is_admin:
                    strategyQuery['created_at']['$lte'] = await AppUtils.combineDateTime(request.to_date.strftime(
                        '%Y-%m-%d'), "000")
                else:
                    strategyQuery['created_at']['$lte'] = request.to_date.strftime(
                        '%Y-%m-%d')
            if request.strategy_id is not None:
                strategyQuery['strategy_setting_id'] = request.strategy_id
            if request.stock_name is not None:
                strategyQuery['symbol'] = request.stock_name.upper()
            if request.status is not None:
                strategyQuery['status'] = request.status
            async for strgy in db[dbStrategy].find(strategyQuery).sort([('entry_at', -1)]):
                order = await db[dbOrder].find_one(
                    {'strategy_id': strgy['_id'], 'user_id': user['_id']})
                if order is not None:
                    strategy = jsonable_encoder(strgy)
                    # Get LTP from redis
                    key = f"{AppConstants.stock}{strategy['fyToken']}"
                    stock = RedisDB.getJson(key=key)
                    if stock is not None:
                        strategy['ltp'] = stock['ltp']
                        strategy['change_in_percentage'] = round(
                            (float(stock["ltp"]) - float(stock["close_price"])), 2)
                        strategy['change_in_price'] = round(
                            (float(stock["ltp"]) - float(stock["close_price"]))/float(stock["close_price"] * 100.0), 2)
                    else:
                        strategy['ltp'] = 0.00
                        strategy['change_in_percentage'] = 0.00
                        strategy['change_in_price'] = 0.00

                    strategy['quantity'] = order['quantity']
                    strategy['order'] = OrderModelItem(order)
                    strgySetting = await db[dbStrategySetting].find_one({'_id': strategy['strategy_setting_id']})
                    if strgySetting is not None:
                        strategy['strategy_name'] = strgySetting['strategy_name']
                    else:
                        strategy['strategy_name'] = ""
                    strategies.append(strategy)

            if len(strategies) <= 0:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategies not yet generated")
            else:
                return AppUtils.responseWithData(True, status.HTTP_200_OK, "Strategies fetched successsfully", StrategyModelItemList(strategies))
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def placeLiveOrder(brokerType):
    try:
        if brokerType == AppUtils.getTradingPlatform().flatTrade:
            jData = {
                "uid": "MADUA10",
                "actid": "MADUA10",
                "exch": "NFO",
                "tsym": "BANKNIFTY20APR23P39700",
                "qty": "25",
                "prc": "0.0",
                "prd": "M",
                "trantype": "B",
                "prctyp": "MKT",
                "ret": "DAY",
                "ordersource": "API"
            }
            payload = "jData=" + \
                json.dumps(jData) + \
                f"&jKey={'df1498a38e6b76e4bab23b95533dbbe7ac6b23a0b22ac681c6ed14dc8cfad9ca'}"
            response = requests.post(
                ApiTerminal.flatTradeApi['placeOrder'], data=payload)
            if response.status_code == 200:
                data = response.json()
                if data['stat'] == "Ok":
                    orderId = data['norenordno']
                    orderLog = "Buy Order placed successfully"
                else:
                    isOrderPlace = False
                    orderLog = response.json()
            else:
                orderLog = response.json()  # "Failed to placed buy order successfully"
                isOrderPlace = False
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, f"FlatTrade :{orderLog}")
        elif brokerType == AppUtils.getTradingPlatform().fyers:
            accessToken = f"RR39ELEFO4-100:eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE2ODE2MTc3NjIsImV4cCI6MTY4MTY5MTQ0MiwibmJmIjoxNjgxNjE3NzYyLCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCa08zTmlvQm5ZVUoydElzeVNReGZ1TEdOSXhCNWt1a28xMVhUeS1EU2JmTzNwVUYwOFRydlc3eGdMZDl6M21qQVEyT0l5X2twS0l2eThXQW1UWTI1QWZQVW5YZFdwWGVnakpZWi1uS2tXM1o5VU5LMD0iLCJkaXNwbGF5X25hbWUiOiJPTkRJVklMTFUgQVRITUFSQU8gU1VOREFSQVJBTUFOIiwib21zIjoiSzEiLCJmeV9pZCI6IlhPMDE0MDMiLCJhcHBUeXBlIjoxMDAsInBvYV9mbGFnIjoiTiJ9.M3qy3wTqKjhA2_SK3ilYac5GzlnGSRnGNfjmWhnjXRo"
            header = {"Content-Type": "application/json",
                      "Authorization": accessToken}
            jData = {
                "symbol": "NSE:BANKNIFTY2342039700PE",
                "qty": 25,
                "type": 2,
                "side": -1,
                "productType": "INTRADAY",
                "limitPrice": 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": "False",
                "stopLoss": 0,
                "takeProfit": 0
            }

            response = requests.post(
                ApiTerminal.fyersApi['placeOrder'], data=json.dumps(jData), headers=header)

            if response.status_code == 200:
                data = response.json()
                if data['s'] == "Ok":
                    orderId = data['id']
                    orderLog = f"{orderId} Buy Order placed successfully"
                else:
                    isOrderPlace = False
                    orderLog = response.json()
            else:
                orderLog = response.json()  # "Failed to placed buy order successfully"
                isOrderPlace = False

            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, f"Fyers: {orderLog}")
        elif brokerType == AppUtils.getTradingPlatform().angelBroking:
            apiKey = "pEehMbHy"
            accessToken = f"eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6IkRJWUQ3ODMyIiwicm9sZXMiOjAsInVzZXJ0eXBlIjoiVVNFUiIsImlhdCI6MTY4MTg2MzQ4OCwiZXhwIjoxNzY4MjYzNDg4fQ.WE0Y_GfV0L6Mg-ilJxJtK7ph89sr2mGUcSzec52Gh5np1_LmyxjVNAdCFrVEVgmLmeyRCIAfFH3uutWtvBHB0w"
            header = {
                'Authorization': f'Bearer {accessToken}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
                'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
                'X-MACAddress': 'MAC_ADDRESS',
                'X-PrivateKey': apiKey
            }

            jData = {
                "variety": "NORMAL",
                "tradingsymbol": "BANKNIFTY20APR2338900CE",
                "symboltoken": "52678",
                "transactiontype": "BUY",
                "exchange": "NSE",
                "ordertype": "MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": 0,
                "squareoff": 0,
                "stoploss": 0,
                "quantity": 25
            }

            # jData = {
            #     "variety": "NORMAL",
            #     "tradingsymbol": "SBIN-EQ",
            #     "symboltoken": "3045",
            #     "transactiontype": "BUY",
            #     "exchange": "NSE",
            #     "ordertype": "MARKET",
            #     "producttype": "INTRADAY",
            #     "duration": "DAY",
            #     "price": 0.00,
            #     "squareoff": 0,
            #     "stoploss": 0,
            #     "quantity": 1
            # }

            response = requests.post(
                ApiTerminal.angleOneApi['placeOrder'], data=json.dumps(jData), headers=header)

            if response.status_code == 200:
                data = response.json()
                print(data)
                if data['data'] is not None and len(data['data']) > 0:
                    orderId = data['data']['orderid']
                    orderLog = f"{orderId} Buy Order placed successfully"
                else:
                    isOrderPlace = False
                    orderLog = response.json()
            else:
                orderLog = response.json()  # "Failed to placed buy order successfully"
                isOrderPlace = False
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, f"Angel One: {orderLog}")

    except Exception as ex:
        print(f"Error: {ex}")


async def exitLiveOrder(entry, ltp):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbAccount = AppDatabase.getName().account
        dbOrder = AppDatabase.getName().strategy_order

        fcmTokens = []
        async for order in db[dbOrder].find({'status': 0, 'strategy_id': entry['_id']}):
            user = await db[dbUser].find_one({'_id': order['user_id']})
            account = await db[dbAccount].find_one({'client_id': order['client_id']})

            orderId = "Xybyiyiaq7814"
            orderLog = "Demo Order : Exit"
            orderQnty = order['quantity']

            if order['order_id'] != orderId and account['broker'] == AppUtils.getTradingPlatform().flatTrade:
                jData = {
                    "uid": account['client_id'],
                    "actid": account['client_id'],
                    "exch": "NFO",
                    "tsym": entry['flat_stock_name'],
                    "qty": str(orderQnty),
                    "prc": "0.0",
                    "prd": "M",
                    "trantype": "S",
                    "prctyp": "MKT",
                    "ret": "DAY",
                    "ordersource": "API",
                }
                payload = "jData=" + \
                    json.dumps(jData) + f"&jKey={account['access_token']}"

                response = requests.post(
                    ApiTerminal.flatTradeApi['placeOrder'], data=payload)

                if response.status_code == 200:
                    data = response.json()
                    if data['stat'] == "Ok":
                        orderId = data['norenordno']
                        orderLog = "Sell Order placed successfully"
                    else:
                        orderLog = "Failed to placed sell order successfully"

            updateQuery = {'status': entry['status'],
                           'order_id': f"{order['order_id']} | {orderId}",
                           'order_log': f"{order['order_log']} | {orderLog}"}

            await db[dbOrder].update_one({'_id': order['_id']}, {'$set': updateQuery})

            if user['f_token'] is not None:
                fcmTokens.append(user['f_token'])

        if len(fcmTokens) > 0:
            if entry['status'] == 1:
                entryStatus = "TARGET Achieved"
            elif entry['status'] == 2:
                entryStatus = "NEW TARGET Achieved"
            elif entry['status'] == 3:
                entryStatus = "SL HIT Reached"
            elif entry['status'] == 4:
                entryStatus = "TSL HIT Reached"
            else:
                entryStatus = "LEVEL Reached"
            notificationMsg = f"{entry['stock_name']} - {entry['order_type']} {entryStatus} @{ltp}"
            return AppUtils.sendPushNotification(
                fcm_token=fcmTokens,  message_title=AppConstants.appName, message_body=notificationMsg)
    except Exception as ex:
        print(f"Error: {ex}")
