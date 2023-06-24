import asyncio
from datetime import date, datetime, timedelta
import math
from fastapi import status, WebSocket
from fastapi.encoders import jsonable_encoder
from config.auth import AuthHandler
from config.redis_db import RedisDB
from models.user_model import UserModel
from utils.app_constants import AppConstants
from utils.app_database import AppDatabase
from utils.app_utils import AppUtils

# Login With Fyers
import json
import logging
import websockets
from threading import Thread, Timer

from utils.strategy_utils import StrgyUtils


async def start_websocket(requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbName = AppDatabase.getName().account

        user = await db[dbUser].find_one({'app_id': requestedUser})

        if user is not None:
            if AppUtils.getRole().admin in user['role']:
                account = await db[dbName].find_one({'client_id': AppUtils.getSettings().FYERS_CLIENT})
                accessToken = None
                if account is None:
                    return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Trading platform not exists")
                else:
                    url = AppUtils.getSettings().FYERS_WS
                    created_date = datetime.strptime(
                        account['token_generated_at'], '%Y-%m-%d').date()
                    if created_date != date.today():
                        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Access token not generated")
                    else:
                        accessToken = f"{account['api_key']}:{account['access_token']}"
                        url = f"{url}{accessToken}"
                        print(url)

                if accessToken is not None:
                    await StartWebStocket(wsObj=AppConstants.futureSegmentObj, url=url)

        return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Started successfully")
    except Exception as ex:
        print(f"Error: {ex}")
        # log.error(f"{ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def StartWebStocket(wsObj, url: str):
    if wsObj is not None:
        await wsObj.close()

    wsObj = websockets.connect(url, ping_timeout=None)

    async with wsObj as websocket:
        # Sends a message.
        AppConstants.websocket = websocket
        await sub_scripts(websocket)
        await sub_stocks(websocket)

        # Receives the replies.
        async for message in websocket:
            try:
                parsedData = await parse_binary(message)
                if len(parsedData) > 0:
                    # print('---------------------------------------')
                    # print(parsedData)
                    # print('---------------------------------------')
                    # Single Tick Data
                    key = f"{AppConstants.stock}{parsedData[0]['fyToken']}"
                    RedisDB.setJson(key, parsedData[0])
                    # List Of Tick Data
                    candleKey = f"{AppConstants.candle}{parsedData[0]['fyToken']}"
                    candleData = RedisDB.getJson(key=candleKey)
                    if candleData is not None:
                        candleData.append(parsedData[0])
                    else:
                        candleData = []
                        candleData.append(parsedData[0])
                    RedisDB.setJson(candleKey, candleData)

                    await checkStrategy1Entries(parsedData[0])
                    await checkStrategy2Entries(parsedData[0])
            except Exception as ex:
                logging.error(f"Error: {ex}")

    thread = Thread(target=wsObj.run_forever)
    thread.daemon = True
    thread.start()
    return True


async def sub_scripts(ws):
    try:
        db = await AppUtils.openDb()
        dbFuture = AppDatabase.getName().model_future
        data = []
        async for script in db[dbFuture].find({'is_subscribed': True}):
            data.append(script)
        subscribe = await SubscribeToken(data)
        if subscribe is not None:
            print(subscribe)
            await ws.send(json.dumps(jsonable_encoder(subscribe)))
    except Exception as e:
        print(f"Sub ws: {e}")


async def sub_stocks(ws):
    stockData = RedisDB.getJson(key="ws_stocks")
    if stockData is not None:
        subscribe = await SubscribeToken(stockData)
        if subscribe is not None:
            await ws.send(json.dumps(jsonable_encoder(subscribe)))


async def SubscribeToken(stockData):
    subscribe = {
        "T": "SUB_L2", "L2LIST": [], "SUB_T": 1
    }
    symbols = []

    if stockData is not None:
        for stock in stockData:
            symbols.append(stock['fyers_stock_name'])
        subscribe['L2LIST'] = symbols
    else:
        subscribe = None
    return subscribe


async def parse_binary(packet):
    try:
        message = packet
        if isinstance(message, str):
            return []

        decrypted_packet_items = []

        for i in range(len(packet)):
            if len(message) == 0:
                continue
            (fyToken, timestamp, fyCode, fyFlag, pktLen) = AppConstants.FY_P_HEADER_FORMAT.unpack(
                message[:AppConstants.FY_P_LEN_HEADER])

            if str(fyToken)[:2] not in ["10", "11", "12"]:
                continue

            packet_data = {"timestamp": timestamp,
                           "fyToken": fyToken, "fyCode": fyCode}
            message = message[AppConstants.FY_P_LEN_HEADER:]

            pc, ltp, op, hp, lp, cp, mop, mhp, mlp, mcp, mv = AppConstants.FY_P_COMMON_7208.unpack(
                message[: AppConstants.FY_P_LEN_COMN_PAYLOAD])

            packet_data["ltp"] = ltp/pc
            packet_data["open_price"] = op/pc
            packet_data["high_price"] = hp/pc
            packet_data["low_price"] = lp/pc
            packet_data["close_price"] = cp/pc
            # packet_data["min_open_price"] = mop/pc
            # packet_data["min_high_price"] = mhp/pc
            # packet_data["min_low_price"] = mlp/pc
            # packet_data["min_close_price"] = mcp/pc
            # packet_data["min_volume"] = mv

            # if int(fyCode) not in [7202, 7207, 27]:
            #     message = message[AppConstants.FY_P_LEN_COMN_PAYLOAD:]
            #     ltq, ltt, atP, vtt, totBuy, totSell = AppConstants.FY_P_EXTRA_7208.unpack(
            #         message[: AppConstants.FY_P_LEN_EXTRA_7208])
            #     packet_data["last_traded_qty"] = ltq
            #     packet_data["last_traded_time"] = ltt
            #     packet_data["avg_trade_price"] = atP
            #     packet_data["vol_traded_today"] = vtt
            #     packet_data["tot_buy_qty"] = totBuy
            #     packet_data["tot_sell_qty"] = totSell

            #     packet_data["market_pic"] = []

            #     message = message[AppConstants.FY_P_LEN_EXTRA_7208:]
            #     for i in range(0, 10):
            #         prc, qty, num_ord = AppConstants.FY_P_MARKET_PIC.unpack(
            #             message[:AppConstants.FY_P_LEN_BID_ASK])
            #         packet_data["market_pic"].append(
            #             {"price": prc/pc, "qty": qty, "num_orders": num_ord})
            #         message = message[AppConstants.FY_P_LEN_BID_ASK:]

            packet_data["change_in_price"] = round(
                float(packet_data["ltp"]) - float(packet_data["close_price"]), 2)
            packet_data["change_in_percentage"] = round(
                ((float(packet_data["ltp"]) - float(packet_data["close_price"]))/float(packet_data["close_price"])) * 100.0, 2)

            decrypted_packet_items.append(packet_data)
        return decrypted_packet_items
    except Exception as e:
        print(f"Error: ws parse binary {e}")

#################################################################
# Check Entries
#################################################################


async def checkStrategy1Entries(currentStock):
    try:
        stockKey = f"{AppConstants.strategy_1}stock"
        stockData = RedisDB.getJson(key=stockKey)
        if stockData is not None:
            for stock in stockData:
                timeFrame = int(
                    stock['setting']['time_frame'].replace("M", ""))

                # Check Entries
                entryKey = f"{AppConstants.strategy_1}entry_{timeFrame}"
                entryData = RedisDB.getJson(key=entryKey)
                if entryData is not None:
                    await StrgyUtils.checkEntry(
                        timeFrame, 700, stockKey, stock, entryKey, entryData, currentStock)
    except Exception as ex:
        print(f"Error: {ex}")


async def checkStrategy2Entries(currentStock):
    try:
        stockKey = f"{AppConstants.strategy_2}stock"
        stockData = RedisDB.getJson(key=stockKey)
        if stockData is not None:
            for stock in stockData:
                timeFrame = int(
                    stock['setting']['time_frame'].replace("M", ""))

                # Check Entries
                entryKey = f"{AppConstants.strategy_2}entry_{timeFrame}"
                entryData = RedisDB.getJson(key=entryKey)
                if entryData is not None:
                    await StrgyUtils.checkEntry(
                        timeFrame, 700, stockKey, stock, entryKey, entryData, currentStock)
    except Exception as ex:
        print(f"Error: {ex}")


async def checkWsIsRunning(requestedUser: UserModel):
    try:
        marketStartTime = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "918")
        marketEndTime = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "1529")
        if AppUtils.getCurrentDateTimeStamp() > marketStartTime and AppUtils.getCurrentDateTimeStamp() < marketEndTime:
            wsStocks = RedisDB.getJson(key="ws_stocks")
            if wsStocks is not None and len(wsStocks) > 0:
                stock = RedisDB.getJson(
                    key=f"{AppConstants.stock}{wsStocks[0]['fyToken']}")
                if stock is not None:
                    marketTime = int(
                        (datetime.now() - timedelta(seconds=10)).timestamp())
                    if stock['timestamp'] < marketTime:
                        await start_websocket(requestedUser)
                else:
                    await start_websocket(requestedUser)
        else:
            print(f"Not an market hour")
    except Exception as ex:
        print(f"Error ws check: {ex}")


#################################################################
# Socket Connection
#################################################################

async def publishWs():
    try:
        jData = {
            "timestamp": 1684490399,
            "fyToken": 101123052573595,
            "fyCode": 7208,
            "ltp": 338.65,
            "open_price": 320.5,
            "high_price": 349.0,
            "low_price": 216.55,
            "close_price": 295.95,
            "min_open_price": 337.7,
            "min_high_price": 339.0,
            "min_low_price": 337.0,
            "min_close_price": 338.65,
            "min_volume": 9500,
            "last_traded_qty": 50,
            "last_traded_time": 1684490398,
            "avg_trade_price": 27313,
            "vol_traded_today": 4818450,
            "tot_buy_qty": 122450,
            "tot_sell_qty": 19300,
            "change_in_price": 42.7,
            "change_in_percentage": 14.43
        }

        await AppUtils.sendWsMessage(message=json.dumps(jData))
    except Exception as ex:
        print(f"Error ws publish: {ex}")
        return f"{ex}"


async def heartbeat(websocket: WebSocket):
    while True:
        try:
            message = await websocket.receive_text()
            if type(message) is str:
                message = json.loads(message)
                if "heartBeat" in message and message['heartBeat'] != 1:
                    await websocket.close()
                else:
                    await websocket.close()
        except websockets.exceptions.ConnectionClosed:
            break


async def connectWebsocket(websocket: WebSocket, token: str = None):
    try:
        await websocket.accept()
        if token is not None:
            auth_handler = AuthHandler()
            user = auth_handler.decode_ws_token(token)
            response = {
                'status': False,
                'status_code': status.HTTP_400_BAD_REQUEST,
            }
            if type(user) is int:
                if user == 1:
                    response['message'] = "Expired Signature"
                    response = json.dumps(response)
                    await websocket.send_text(json.dumps(response))
                else:
                    response['message'] = "Invalid Token"
                    response = json.dumps(response)
                    await websocket.send_text(json.dumps(response))
            else:
                AppConstants.wsConnection.append(websocket)
                response['status'] = True
                response['status_code'] = status.HTTP_200_OK
                response['message'] = "Connected successfully"
                response = json.dumps(response)
                await websocket.send_text(json.dumps(response))
                await asyncio.gather(heartbeat(websocket))
        else:
            response['message'] = "required fileds are missing"
            response = json.dumps(response)
            await websocket.send_text(json.dumps(response))
    except Exception as ex:
        print(f"Error: {ex}")
