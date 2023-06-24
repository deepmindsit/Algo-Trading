
from datetime import datetime, date, timedelta
import json
import time
from typing import List
from fastapi import HTTPException, status, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from bson import ObjectId
from config.redis_db import RedisDB
from models.user_model import UserModel
from utils.api_terminal import ApiTerminal
from utils.app_utils import AppUtils
from schemas.stocks_schema import stockModelItemList
from utils.app_constants import AppConstants
from utils.app_database import AppDatabase
from models.stocks_model import StockModel, StockList
from dateutil.relativedelta import relativedelta, TH, FR
import logging
import calendar
import requests


async def bulkInsert(request: List[StockModel]):
    db = await AppUtils.openDb()
    dbCash = AppDatabase.getName().model_cash
    dbFuture = AppDatabase.getName().model_future
    dbOption = AppDatabase.getName().model_option

    for stock in request:
        if stock.segment == AppUtils.getSegment().cash:
            if await db[dbCash].find_one({'stock_name': stock.stock_name}) is None:
                db[dbCash].insert_one(jsonable_encoder(stock))
        elif stock.segment == AppUtils.getSegment().future:
            if await db[dbFuture].find_one({'stock_name': stock.stock_name}) is None:
                stock.angel_stock_name = await getStockName(stock.stock_name)
                db[dbFuture].insert_one(jsonable_encoder(stock))
        elif stock.segment == AppUtils.getSegment().option:
            if await db[dbOption].find_one({'stock_name': stock.stock_name}) is None:
                db[dbOption].insert_one(jsonable_encoder(stock))


async def create(request: List[StockModel], requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user

        adUser = await db[dbUser].find_one({'app_id': requestedUser})
        if adUser is not None:
            if AppUtils.getRole().admin in adUser['role']:
                await bulkInsert(request=request)
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Stocks Inserted Successfully")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def deleteStocks(db, dbStock, stock):
    # Delete from Db
    await db[dbStock].delete_one({'_id': stock['_id']})
    key = f"{AppConstants.stock}{stock['exchange_code']}"
    stockData = RedisDB.getJson(key=key)
    # Delete from Redis
    if stockData:
        AppConstants.delData(key=key)


async def delete(request: StockList, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbCash = AppDatabase.getName().model_cash
        dbFuture = AppDatabase.getName().model_future
        dbOption = AppDatabase.getName().model_option
        dbUser = AppDatabase.getName().user

        adUser = await db[dbUser].find_one({'app_id': requestedUser})
        if adUser is not None:
            if adUser['role'] == AppUtils.getRole().admin:
                if request.segment == AppUtils.getSegment().cash:
                    if request.stock_name is not None:
                        stock = await db[dbCash].find_one({'stock_name': request.stock_name})
                        if stock is not None:
                            await deleteStocks(db=db, dbStock=dbCash, stock=stock)
                            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Stock deleted successfully")
                        else:
                            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Stock not found")
                    else:
                        async for stock in db[dbCash].find():
                            await deleteStocks(db=db, dbStock=dbCash, stock=stock)
                        return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Stocks deleted successfully")
                elif request.segment == AppUtils.getSegment().future:
                    if request.stock_name is not None:
                        stock = await db[dbFuture].find_one({'stock_name': request.stock_name})
                        if stock is not None:
                            await deleteStocks(db=db, dbStock=dbFuture, stock=stock)
                            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Stock deleted successfully")
                        else:
                            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Stock not found")
                    else:
                        async for stock in db[dbFuture].find():
                            await deleteStocks(db=db, dbStock=dbFuture, stock=stock)
                        return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Stocks deleted successfully")
                elif request.segment == AppUtils.getSegment().option:
                    if request.stock_name is not None:
                        stock = await db[dbOption].find_one({'stock_name': request.stock_name})
                        if stock is not None:
                            await deleteStocks(db=db, dbStock=dbOption, stock=stock)
                            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Stock deleted successfully")
                        else:
                            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Stock not found")
                    else:
                        async for stock in db[dbOption].find():
                            await deleteStocks(db=db, dbStock=dbOption, stock=stock)
                        return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Stocks deleted successfully")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def getDataFromRedis(stock):
    liveData = RedisDB.getJson(f"{AppConstants.stock}{stock['fyToken']}")
    if liveData is not None:
        try:
            stock['last_traded_price'] = liveData['ltp']
            stock['trade_volume'] = liveData['min_volume']
            stock['timestamp'] = liveData['timestamp']
            stock['open_price'] = liveData['open_price']
            stock['high_price'] = liveData['high_price']
            stock['low_price'] = liveData['low_price']
            stock['close_price'] = liveData['close_price']
            stock['change_in_price'] = liveData['change_in_price']
            stock['change_in_percentage'] = liveData['change_in_percentage']

        # ((NP-OP)/OP)*100 = PG
        except Exception as ex:
            print(f"{str(ex)}")
    elif stock['change_in_price'] == 0 and float(stock["close_price"]) != 0:
        stock["change_in_price"] = round(
            float(stock["last_traded_price"]) - float(stock["close_price"]), 2)
        stock["change_in_percentage"] = round(
            ((float(stock["last_traded_price"]) - float(stock["close_price"]))/float(stock["close_price"])) * 100.0, 2)
    return stock


async def getLTPDataFromRedis(db, dbStrategy, exchange_code):
    ltp = None
    print(f"stock_code : {exchange_code}")
    liveData = RedisDB.getJson(
        f"stock_{exchange_code}")
    if liveData is not None:
        ltp = liveData['last_traded_price']
    else:
        if dbStrategy == AppDatabase.getName().strategy_cash:
            stock = await db[AppDatabase.getName().model_cash].find_one({'exchange_code': exchange_code})
            ltp = stock['last_traded_price']
        if dbStrategy == AppDatabase.getName().strategy_future:
            stock = await db[AppDatabase.getName().model_future].find_one({'exchange_code': exchange_code})
            ltp = stock['last_traded_price']
        if dbStrategy == AppDatabase.getName().strategy_option:
            stock = await db[AppDatabase.getName().model_option].find_one({'exchange_code': exchange_code})
            ltp = stock['last_traded_price']
    return ltp


async def list(request: StockList):
    try:
        db = await AppUtils.openDb()
        dbCash = AppDatabase.getName().model_cash
        dbFuture = AppDatabase.getName().model_future
        dbOption = AppDatabase.getName().model_option

        stocks = []
        if request.segment == AppUtils.getSegment().future:
            if request.stock_name is not None:
                stock = await db[dbFuture].find_one({'stock_name': request.stock_name})
                if stock is not None:
                    stock = await getDataFromRedis(stock=stock)
                    stocks.append(stock)
            else:
                async for stock in db[dbFuture].find():
                    stock = await getDataFromRedis(stock=stock)
                    stocks.append(stock)
        elif request.segment == AppUtils.getSegment().option:
            if request.stock_name is not None:
                stock = await db[dbOption].find_one({'stock_name': request.stock_name})
                if stock is not None:
                    stock = await getDataFromRedis(stock=stock)
                    stocks.append(stock)
            else:
                expiry_date = await AppUtils.getExpiryDate()
                async for stock in db[dbOption].find({'expiry_date': expiry_date}):
                    stock = await getDataFromRedis(stock=stock)
                    stocks.append(stock)

        if len(stocks) <= 0:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Stocks not exists")
        else:
            return AppUtils.responseWithData(True, status.HTTP_200_OK, "Stocks exists", stockModelItemList(stocks))

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def getStockName(stockName):
    end_of_month = datetime.today() + relativedelta(day=31)
    last_thursday = end_of_month + relativedelta(weekday=TH(-1))
    dateT = last_thursday.strftime("%d")
    yearT = last_thursday.strftime("%y")
    # WIPRO26AUG21FUT
    # WIPRO21AUGFUT
    return stockName.replace(yearT, dateT).replace("FUT", yearT+"FUT")


async def updateFutureContract(requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbFuture = AppDatabase.getName().model_future
        dbOption = AppDatabase.getName().model_option

        adUser = await db[dbUser].find_one({'app_id': requestedUser})
        if adUser is not None:
            if AppUtils.getRole().admin in adUser['role']:

                # current_date = datetime.today().strftime("%Y-%m-%d")
                # end_of_month = datetime.today() + relativedelta(day=31)
                # last_thursday = end_of_month + relativedelta(weekday=TH(-1))
                # thursday = last_thursday.strftime("%Y-%m-%d")

                # if current_date == thursday:
                header = {"Content-Type": "application/json"}
                url = "https://v2api.aliceblueonline.com/restpy/contract_master?exch=NFO"
                r = requests.post(url, headers=header)
                logging.info(f"Get Encryption Key response {r.text}")
                stocks = r.json()["NFO"]
                cData = datetime.now()
                days_in_month = calendar.monthrange(
                    cData.year, cData.month)[1]
                monthFormat = cData + timedelta(days=days_in_month)
                mf = monthFormat.strftime("%b").upper()
                # await db[dbFuture].delete_many({})
                await db[dbOption].delete_many({})
                for stock in stocks:
                    isExists = False
                    if (stock["symbol"] == "NIFTY" or stock["symbol"] == "BANKNIFTY") and str(mf) in stock["formatted_ins_name"] and stock["instrument_type"] == "OPTIDX":
                        segment = "OPTION"
                        isExists = await db[dbOption].find_one({'stock_name': stock["trading_symbol"]})

                    # if (stock["symbol"] == "NIFTY" or stock["symbol"] == "BANKNIFTY") and str(mf) in stock["trading_symbol"] and stock["instrument_type"] == "FUTIDX":
                    #     segment = "FUTURE"
                    #     isExists = await db[dbOption].find_one({'stock_name': stock["trading_symbol"]})

                    if isExists is None:
                        angel_stock_name = await getStockName(stock["trading_symbol"])
                        stock_obj = StockModel(
                            id=(str(ObjectId())),
                            segment=segment,
                            exchange="NSE",
                            symbol=stock["symbol"],
                            stock_name=stock["trading_symbol"],
                            angel_stock_name=angel_stock_name,
                            instrument_token="",
                            exchange_code=stock["token"],
                            instrument_type=stock["instrument_type"],
                            option_type=stock["option_type"],
                            lot_size=stock["lot_size"],
                            strike_price=stock["strike_price"],
                            expiry_date=stock["expiry_date"],
                            sector="",
                        )

                        if stock["instrument_type"] == "OPTIDX":
                            await db[dbOption].insert_one(jsonable_encoder(stock_obj))

                        # else:
                        #     await db[dbFuture].insert_one(jsonable_encoder(stock_obj))

                await updateStockNames(requestedUser)
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def updateStockNames(requestedUser: UserModel):
    await updateFyersTradeName(requestedUser)
    # await updateFlatTradeName(requestedUser)


async def updateFyersTradeName(requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbFuture = AppDatabase.getName().model_future
        dbOption = AppDatabase.getName().model_option
        dbAccount = AppDatabase.getName().account

        adUser = await db[dbUser].find_one({'app_id': requestedUser})
        # print(adUser)
        if adUser is not None:
            if AppUtils.getRole().admin in adUser['role']:
                account = await db[dbAccount].find_one({'client_id': AppUtils.getSettings().FYERS_CLIENT})
                accessToken = None
                # print(account)
                if account is None:
                    return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Trading platform not exists")
                else:
                    created_date = datetime.strptime(
                        account['token_generated_at'], '%Y-%m-%d').date()
                    if created_date != date.today():
                        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Access token not generated")
                    else:
                        accessToken = f"{account['api_key']}:{account['access_token']}"

                if accessToken is not None:

                    header = {"Content-Type": "application/json",
                              "Authorization": accessToken}

                    url = ApiTerminal.fyersApi['getQuotes']

                    async for stock in db[dbFuture].find():
                        symbol = f"{stock['exchange']}:{stock['stock_name']}"
                        if stock['fyToken'] is None:
                            stock = await updateFyersNameStock(header, url, symbol, stock)
                            await db[dbFuture].update_one({'_id': stock['_id']}, {'$set': jsonable_encoder(stock)})

                    # Get Script Expiry Date
                    expiry_date = await AppUtils.getExpiryDate()
                    print(f"expiry_date: {expiry_date}")
                    async for stock in db[dbOption].find({'expiry_date': expiry_date}):
                        symbol = f"{stock['exchange']}:{stock['stock_name']}"
                        if stock['fyToken'] is None:
                            stock = await updateFyersNameStock(header, url, symbol, stock)
                            print(
                                f"{stock['stock_name']} : {stock['fyToken']}")
                            await db[dbOption].update_one({'_id': stock['_id']}, {'$set': jsonable_encoder(stock)})
                            # time.sleep(1)
                else:
                    return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Access Token failed")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def updateFyersNameStock(header, url, symbol, stock):
    try:
        url = f"{url}{symbol}"
        response = requests.get(url, headers=header)
        if response.status_code == 200:
            quoteData = response.json()['d'][0]['v']
            # print('------------------------')
            # print(quoteData['lp'])
            # print(quoteData['tt'])
            # print(quoteData['open_price'])
            # print(quoteData['high_price'])
            # print(quoteData['low_price'])
            # print(quoteData['prev_close_price'])
            # print(quoteData['fyToken'])
            # print('------------------------')
            if quoteData is not None:
                stock['last_traded_price'] = quoteData['lp']
                stock['last_traded_time'] = quoteData['tt']
                stock['open_price'] = quoteData['open_price']
                stock['high_price'] = quoteData['high_price']
                stock['low_price'] = quoteData['low_price']
                stock['close_price'] = quoteData['prev_close_price']
                stock['fyToken'] = quoteData['fyToken']
                stock['fyers_stock_name'] = quoteData['symbol']
        return stock
    except Exception as ex:
        print(f"{str(ex)}")


async def updateFlatTradeName(requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbFuture = AppDatabase.getName().model_future
        dbOption = AppDatabase.getName().model_option
        dbAccount = AppDatabase.getName().account

        adUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adUser is not None:
            if AppUtils.getRole().admin in adUser['role']:
                account = await db[dbAccount].find_one({'user_id': adUser['_id'], 'client_id': AppUtils.getSettings().FLAT_TRADE_CLIENT})
                accessToken = None
                # print(account)
                if account is None:
                    return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Trading platform not exists")
                else:
                    created_date = datetime.strptime(
                        account['token_generated_at'], '%Y-%m-%d').date()
                    if created_date != date.today():
                        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Access token not generated")
                    else:
                        accessToken = account['access_token']

                if accessToken is not None:
                    async for stock in db[dbFuture].find():
                        # Get Script Expiry Date
                        expiry_date = await AppUtils.getExpiryDate()
                        async for stock in db[dbOption].find({'expiry_date': expiry_date}):
                            jData = {
                                "uid": account['client_id'],
                                "exch": "NFO",
                                "token": stock['exchange_code'],
                            }

                            payload = 'jData=' + \
                                json.dumps(jData) + f'&jKey={accessToken}'

                            getData = True
                            if "flat_stock_name" in stock and stock['flat_stock_name'] is not None:
                                getData = False
                            if getData:
                                stock = await updateFlatNameStock(ApiTerminal.flatTradeApi['getQuotes'], payload, stock)
                                print(stock['flat_stock_name'])
                                await db[dbOption].update_one({'_id': stock['_id']}, {'$set': jsonable_encoder(stock)})
                                # time.sleep(1)
                    else:
                        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Access Token failed")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def updateFlatNameStock(url, payload, stock):
    try:
        # print(f"{url} - {payload}")
        response = requests.post(url, data=payload)
        # print(response)
        if response.status_code == 200:
            data = response.json()
            if data['stat'] == "Ok":
                stock['flat_stock_name'] = data['tsym']
        return stock
    except Exception as ex:
        print(f"{str(ex)}")
