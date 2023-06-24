from ast import List
import asyncio
import enum
import json
import base64
import os
import redis
import requests
from pydoc import cli
from typing import Optional
from urllib import request
import motor.motor_asyncio
from utils.app_constants import AppConstants
from datetime import datetime, timedelta
from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_mail import ConnectionConfig, FastMail
from fastapi.encoders import jsonable_encoder
from pydantic import BaseSettings
from bson import ObjectId
from pyfcm import FCMNotification
from enum import Enum
from hashlib import blake2b
import logging


class WebSocketState(enum.Enum):
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2


class Settings(BaseSettings):
    ENVIRONMENT: str
    APIVERSION: str
    TPAPIVERSION: str
    REDIS_PORT: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE: int
    SECRET_KEY: str
    FSERVICEKEY: str
    BASEURL_DEV: str
    BASEURL_UAT: str
    BASEURL_PROD: str
    REDIS_PASS: str
    MONGO_DEV: str
    MONGO_UAT: str
    MONGO_PROD: str
    FYERS_WS: str
    FYERS_CLIENT: str
    FLAT_TRADE_CLIENT: str

    class Config:
        env_file = ".env"
        case_sensitive = True


class MailDetails(BaseSettings):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str

    class Config:
        env_file = ".env"
        case_sensitive = True


class TPKeyDetails(BaseSettings):
    FYERS_APP_ID: str
    FLAT_TRADE_APP_ID: str
    FLAT_TRADE_APP_SECRET: str

    class Config:
        env_file = ".env"
        case_sensitive = True


class Environment(str, Enum):
    dev = "DEV"
    uat = "UAT"
    prod = "PROD"
    test = "Test"
    live = "Live"


class Segment(str, Enum):
    live = "LIVE"
    cash = "CASH"
    future = "FUTURE"
    option = "OPTION"


class Role(str, Enum):
    user = "USER"
    superAdmin = "SUPER ADMIN"
    admin = "ADMIN"


class TradingPlatform(str, Enum):
    fyers = "Fyers"
    angelBroking = "Angel One"
    flatTrade = "Flat Trade"


class Action(str, Enum):
    add = "ADD"
    view = "VIEW"
    edit = "EDIT"
    delete = "DELETE"


class StrategyStatus(str, Enum):
    ready = "READY"
    open = "OPEN"
    target = "TARGET"
    slhit = "SLHIT"
    sqroff = "SQROFF"


class OrderType(str, Enum):
    buy = "BUY"
    sell = "SELL"
    bracketOrder = "BRACKET ORDER"
    slOrder = "SL ORDER"
    slOrderError = "SL ORDER ERROR"
    modifyOrder = "MODIFY ORDER"
    marketOrder = "MARKET ORDER"
    exitOrder = "EXIT ORDER"
    exitOrderError = "EXIT ORDER ERROR"


class Color(str, Enum):
    white = "WHITE"
    green = "GREEN"
    red = "RED"


class WsPlatform(str, Enum):
    fyers = "Fyers"
    flatTrade = "FlatTrade"
    angelOne = "AngelOne"


class WsAction(str, Enum):
    subscribe = "subscribe"
    unsubscribe = "unsubscribe"


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class Requests(enum.IntEnum):
    PUT = 1
    DELETE = 2
    GET = 3
    POST = 4


class AppUtils():

    def responseWithData(responseStatus, statusCode, message, responseData):
        # compressData = AppConstants.compressJson(responseData)
        # encode = base64.b64encode(compressData)
        data = {}
        data['status'] = responseStatus
        data['status_code'] = statusCode
        data['message'] = message
        data['data'] = responseData
        # data['data'] =  base64.b64encode(AppConstants.compressJson(responseData))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(data))

    def responseWithoutData(responseStatus, statusCode, message):
        data = {}
        data['status'] = responseStatus
        data['status_code'] = statusCode
        data['message'] = message
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(data))

    def responseAllStrategy(responseStatus, statusCode, message, responseData, performanceData):
        # compressData = AppConstants.compressJson(responseData)
        # encode = base64.b64encode(compressData)
        data = {}
        data['status'] = responseStatus
        data['status_code'] = statusCode
        data['message'] = message
        data['data'] = responseData
        data['performance'] = performanceData
        # data['data'] =  base64.b64encode(AppConstants.compressJson(responseData))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(data))

    def mtmResponse(responseStatus, statusCode, message, responseData):
        # compressData = AppConstants.compressJson(responseData)
        # encode = base64.b64encode(compressData)
        data = {}
        data['status'] = responseStatus
        data['status_code'] = statusCode
        data['message'] = message
        data['profit_loss'] = responseData
        # data['data'] =  base64.b64encode(AppConstants.compressJson(responseData))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(data))

    async def get_db_client(db_client, MONGODB_DATABASE_URL):
        """Return database client instance."""
        db_client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGODB_DATABASE_URL)
        return db_client

    async def openDb(isAsync: bool = False):
        if AppConstants.dbClient is None:
            MONGODB_DATABASE_URL = None
            # Mongo Connections
            if AppUtils.getSettings().ENVIRONMENT == AppUtils.getEnvironment().dev:
                MONGODB_DATABASE_URL = AppUtils.getSettings().MONGO_DEV
            elif AppUtils.getSettings().ENVIRONMENT == AppUtils.getEnvironment().uat:
                MONGODB_DATABASE_URL = AppUtils.getSettings().MONGO_UAT
            else:
                MONGODB_DATABASE_URL = AppUtils.getSettings().MONGO_PROD

            # Motor
            db_client: motor.motor_asyncio.AsyncIOMotorClient = None

            AppConstants.dbClient = await AppUtils.get_db_client(db_client, MONGODB_DATABASE_URL)

            # MotorClient to be at the top level of the module
            # to always return the current loop.
            AppConstants.dbClient.get_io_loop = asyncio.get_running_loop

            return AppConstants.dbClient.yaari_bot
        else:
            return AppConstants.dbClient.yaari_bot

    async def closeDB(db: motor.motor_asyncio.AsyncIOMotorClient):
        db.close()

    async def openProdDb():
        client = await config.database.get_prod_db_client()
        return client.tradebot

    def responseRedirect(redirectUrl):
        return RedirectResponse(redirectUrl)

    def getSettings() -> Settings:
        return Settings()

    def getMail() -> MailDetails:
        return MailDetails()

    def getTPKeyDetails() -> TPKeyDetails:
        return TPKeyDetails()

    def getEnvironment() -> Environment:
        return Environment

    def setup_logger(name, level=logging.ERROR) -> logging.Logger:
        FORMAT = "[%(levelname)s  %(name)s %(module)s:%(lineno)s - %(funcName)s() - %(asctime)s]\n\t %(message)s \n"
        TIME_FORMAT = "%d.%m.%Y %I:%M:%S %p"
        if AppUtils.getSettings().ENVIRONMENT == AppUtils.getEnvironment().dev:
            FILENAME = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), 'serverlog.log')
        else:
            FILENAME = '/var/log/serverlog.log'

        logging.basicConfig(
            format=FORMAT,
            datefmt=TIME_FORMAT,
            level=level,
            force=True,
            encoding='utf-8',
            filename=FILENAME,
            filemode='w'
        )

        logger = logging.getLogger(name)
        return logger

    def getSegment() -> Segment:
        return Segment

    def getRole() -> Role:
        return Role

    def getTradingPlatform() -> TradingPlatform:
        return TradingPlatform

    def getAction() -> Action:
        return Action

    def getStrategyStatus() -> StrategyStatus:
        return StrategyStatus

    def getOrderType() -> OrderType:
        return OrderType

    def getColor() -> Color:
        return Color

    def getWsPlatform() -> WsPlatform:
        return WsPlatform

    def getWsAction() -> WsAction:
        return WsAction

    def encodeValue(value):
        return base64.b64encode(value.encode('utf-8'))

    def decodeValue(value):
        return base64.b64decode(value).decode('utf-8')

    def encodeData(value):
        encodeValue = value.encode("ascii")
        bencode = base64.b64encode(encodeValue)
        encodeData = bencode.decode("ascii")
        return encodeData

    def decodeData(value):
        encodeValue = value.encode("ascii")
        bdecode = base64.b64decode(encodeValue)
        decodeData = bdecode.decode("ascii")
        return decodeData

    def encryptKey(value):
        h = blake2b(key=b'SVAppKey', digest_size=16)
        bCode = value.encode('utf-8')
        h.update(bCode)
        return h.hexdigest()

    def getIpAddress(request: Request):
        return request.client.host

    def convert2Decimal(input):     # 0.0356    .00 / .05
        sval = 0.05
        aval = (sval * (round(input/sval)))
        return round(aval, 2)

    def round2(input):
        val = round(float(input), 2)
        strVal = str(val).split('.')
        splitBy = strVal[1]
        if len(splitBy) > 1:
            if int(splitBy[1]) > 5:
                if (int(splitBy[0]) + 1) == 10:
                    roundVal = f"{strVal[0]}.10"
                else:
                    roundVal = f"{strVal[0]}.{(int(splitBy[0]) + 1)}0"
            else:
                roundVal = f"{strVal[0]}.{int(splitBy[0])}5"
        else:
            roundVal = f"{strVal[0]}.{int(splitBy[0])}0"
        return roundVal

    async def combineDateTime(date: str, time: str):
        try:
            return int(datetime.combine(datetime.strptime(
                date, "%d %b %y"), datetime.strptime(time, "%H%M").time()).timestamp())
        except Exception as ex:
            print(f"Error: {ex}")
            return None

    def getCurrentDateTime():
        return datetime.now()

    def getCurrentDateTimeStamp():
        return int(datetime.now().timestamp())

    async def getExpiryDate():
        cDate = datetime.now()  # + timedelta(days=1)
        day_shift = (3 - cDate.weekday()) % 7
        expiry_date = await AppUtils.combineDateTime((cDate + timedelta(days=day_shift)).strftime("%d %b %y"), "530")
        expiry_date *= 1000
        return expiry_date

    def calculateRiskReward(input1, input2, quantity):
        riskReward = (float(input1) - float(input2)) * float(quantity)
        return AppUtils.round2(riskReward)
        return round(aval, 2)

    async def updateNewField(db, dbName, fileds):
        try:
            await db[dbName].update_many({}, {'$set': fileds})
            return True
        except Exception as ex:
            print(f"Error: {ex}")
            return None

    def sendPushNotification(fcm_token, message_title=None, message_body=None, data_message=None):
        if message_title is not None and message_body is not None and data_message is not None:
            return FCMNotification(api_key=AppUtils.getSettings().FSERVICEKEY).notify_multiple_devices(
                registration_ids=fcm_token, message_title=message_title, message_body=message_body, data_message=data_message)
        elif message_title is not None and message_body is not None and data_message is None:
            return FCMNotification(api_key=AppUtils.getSettings().FSERVICEKEY).notify_multiple_devices(
                registration_ids=fcm_token, message_title=message_title, message_body=message_body)
        elif message_title is None and message_body is None and data_message is not None:
            return FCMNotification(api_key=AppUtils.getSettings().FSERVICEKEY).notify_multiple_devices(
                registration_ids=fcm_token, data_message=data_message)

    async def sendWsMessage(message):
        try:
            for index, con in enumerate(AppConstants.wsConnection):
                if con.client_state.value == WebSocketState.CONNECTED.value:
                    await con.send_text(data=json.dumps(message))
                else:
                    AppConstants.wsConnection.pop(index)
        except Exception as ex:
            print(f"Error ws send message: {ex}")

    def emailConfig():
        config = ConnectionConfig(
            MAIL_USERNAME=AppUtils.getMail().MAIL_USERNAME,
            MAIL_PASSWORD=AppUtils.getMail().MAIL_PASSWORD,
            MAIL_FROM=AppUtils.getMail().MAIL_FROM,
            MAIL_PORT=AppUtils.getMail().MAIL_PORT,
            MAIL_SERVER=AppUtils.getMail().MAIL_SERVER,
            MAIL_FROM_NAME=AppUtils.getMail().MAIL_FROM_NAME,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            TEMPLATE_FOLDER=f'{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/templates/email'
        )
        return config

    async def sendEmail(message, template):
        fm = FastMail(AppUtils.emailConfig())
        await fm.send_message(message, template_name=template)


class ApiCalls():

    async def apiCallHelper(urls, http_method, header=None, data=None, params=None):
        # helper formats the url and reads error codes nicely
        url = urls
        if params is not None:
            url = url.format(**params)
        response = await ApiCalls.apiCall(url, http_method, header, data)
        if response.status_code != 200:
            raise AppUtils.responseWithoutData(
                False, status.HTTP_200_OK, request.HTTPError(response.text))
        return response.json()

    async def apiCall(url, http_method, headers, data):
        r = None
        if http_method is Requests.POST:
            r = requests.post(url, json=data, headers=headers)
        elif http_method is Requests.DELETE:
            r = requests.delete(url, headers=headers)
        elif http_method is Requests.PUT:
            r = requests.put(url, json=data, headers=headers)
        elif http_method is Requests.GET:
            r = requests.get(url, headers=headers)
        return r
