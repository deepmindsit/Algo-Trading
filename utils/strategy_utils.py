
from datetime import datetime, timedelta
import json
import math
import time

import requests
from config.redis_db import RedisDB
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException, status
from models.strategy_model import CreateEntryModel, EditEntryModel, ExitOrderModel
from models.user_model import UserModel
from repository.strategy_repo import getCandelData
from utils.api_terminal import ApiTerminal
from utils.app_constants import AppConstants
from utils.app_database import AppDatabase
from utils.app_utils import AppUtils
from bson import ObjectId


class StrgyUtils():

    async def getStrikePrice(db, levelKey, stock, firstCandle, premium, timeFrame):
        try:
            dbOption = AppDatabase.getName().model_option

            levelData = RedisDB.getJson(key=levelKey)
            # print(f"levelData : {levelData}")
            optionList = []
            findSymbol = stock['symbol'].replace("50", "")
            async for option in db[dbOption].find({'symbol': findSymbol}):
                optionList.append(option['strike_price'])

            # ###############################################################
            # Find nearest strike price from candle close price
            # ###############################################################
            if optionList is not None:
                ATM = min(optionList, key=lambda x: abs(
                    x-firstCandle[0][4]))
                OTM = int(ATM + premium)
                ITM = int(ATM - premium)

                expiry_date = await AppUtils.getExpiryDate()

                if stock['symbol'] == "NIFTY":
                    premiumPrice = premium / 2
                else:
                    premiumPrice = premium

                # ##########################
                # Take set of OTM & ITM
                # ##########################

                OTMPremimums = [
                    OTM + (premiumPrice*1),
                    OTM,
                    OTM - (premiumPrice*1),
                ]

                ITMPremimums = [
                    ITM + (premiumPrice*1),
                    ITM,
                    ITM - (premiumPrice*1),
                ]

                stocks = []

                for sPrice in OTMPremimums:
                    async for OTMStock in db[dbOption].find({'expiry_date': expiry_date, 'strike_price': sPrice, 'option_type': "PE"}):
                        TMSymbol = f"{OTMStock['exchange']}:{OTMStock['stock_name']}"
                        OTMStock['is_upper_band_break'] = False
                        OTMStock['is_lower_band_break'] = False
                        OTMStock['previous_candle'] = None
                        OTMStock['confirmation_candle'] = None
                        OTMStock['band_timing'] = None
                        OTMStock['pair_candle'] = []

                        stocks.append(OTMStock)

                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                            exchangeCode=OTMStock['exchange_code'],  present=False)
                        time.sleep(1)

                for sPrice in ITMPremimums:
                    async for ITMStock in db[dbOption].find({'expiry_date': expiry_date, 'strike_price': sPrice, 'option_type': "CE"}):
                        TMSymbol = f"{ITMStock['exchange']}:{ITMStock['stock_name']}"
                        ITMStock['is_upper_band_break'] = False
                        ITMStock['is_lower_band_break'] = False
                        ITMStock['previous_candle'] = None
                        ITMStock['confirmation_candle'] = None
                        ITMStock['band_timing'] = None
                        ITMStock['pair_candle'] = []

                        stocks.append(ITMStock)

                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                            exchangeCode=ITMStock['exchange_code'],  present=False)
                        time.sleep(1)

                strikeData = {
                    "OTM": int(OTM),
                    "ATM": int(ATM),
                    "ITM": int(ITM),
                    "high_level": max(levelData[-2:][0][2], levelData[-2:][1][2]),
                    "low_level": min(levelData[-2:][0][3], levelData[-2:][1][3]),
                    "stocks": stocks,
                    "trade_status": True,
                    "is_high_low_break": False,
                    "is_take_entry": False,
                    "strgy_in_progress": False,
                    "is_close_entry": False,
                    "status": None,
                }
                return strikeData
            else:
                return None
        except Exception as ex:
            AppConstants.log.error(f"Get strike price: {ex}")

    async def checkConditionToStartTrade(strikeKey, strikeData, currentCandle):
        try:
            #########################################################################################################################################
            # Condition : IF CANDLE BREAKS HIGH OR LOW TAKE ENTRY
            #########################################################################################################################################
            if currentCandle[2] >= strikeData['high_level'] and currentCandle[3] >= strikeData['high_level']:
                # print(f">> Hign Break | {currentCandle}")
                strikeData['is_high_low_break'] = True
                if strikeData['strgy_in_progress'] == False:
                    strikeData['is_take_entry'] = True
                strikeData['is_close_entry'] = False
                strikeData['status'] = "CE"
                print(f"high break >> {strikeData['status']}")
                RedisDB.setJson(
                    key=strikeKey, data=strikeData)

            elif currentCandle[2] <= strikeData['low_level'] and currentCandle[3] <= strikeData['low_level']:
                # print(f">> Low Break | {currentCandle}")
                strikeData['is_high_low_break'] = True
                if strikeData['strgy_in_progress'] == False:
                    strikeData['is_take_entry'] = True
                strikeData['is_close_entry'] = False
                strikeData['status'] = "PE"
                print(f"low break >> {strikeData['status']}")
                RedisDB.setJson(
                    key=strikeKey, data=strikeData)

            elif currentCandle[2] >= strikeData['high_level'] and currentCandle[4] <= strikeData['high_level']:
                strikeData['is_high_low_break'] = True
                if strikeData['strgy_in_progress'] == False:
                    strikeData['is_take_entry'] = True
                strikeData['is_close_entry'] = False
                strikeData['status'] = "PE"
                print(f"low break >> {strikeData['status']}")
                RedisDB.setJson(
                    key=strikeKey, data=strikeData)

            elif currentCandle[2] >= strikeData['low_level'] and currentCandle[4] >= strikeData['low_level']:
                strikeData['is_high_low_break'] = True
                if strikeData['strgy_in_progress'] == False:
                    strikeData['is_take_entry'] = True
                strikeData['is_close_entry'] = False
                strikeData['status'] = "CE"
                print(f"high break >> {strikeData['status']}")
                RedisDB.setJson(
                    key=strikeKey, data=strikeData)
        except Exception as ex:
            AppConstants.log.error(f"Check condition: {ex}")

    async def calculateEntry(setting, strikeKey, stock, time, high, targetPoint, low=None, upperBand=None, entry=None, sl=None, target=None, is_international=False):
        try:
            if entry is not None:
                entry = entry
            else:
                entry = high + 1.2
            if sl is not None:
                sl = sl
            else:
                sl = (high * 0.9) - 1.2
            if target is not None:
                target = target
                newTarget = None
            else:
                target = high * targetPoint
                newTargetPoint = (25000 * 0.026) / float(stock['lot_size'])
                newTarget = AppUtils.round2(entry + newTargetPoint)

            result = {
                "strategy_setting_id": setting['_id'],
                "strategy_name": setting['strategy_name'],
                "strike_key": strikeKey,
                "stock_id": stock['_id'],
                "segment": stock['segment'],
                "exchange": stock['exchange'],
                "stock_name": stock['stock_name'],
                "symbol": stock['symbol'],
                "option_type": stock['option_type'],
                "angel_stock_name": stock['angel_stock_name'],
                "flat_stock_name": stock['flat_stock_name'],
                "fyers_stock_name": stock['fyers_stock_name'],
                "instrument_token": stock['instrument_token'],
                "exchange_code": stock['exchange_code'],
                "fyToken": stock['fyToken'],
                "order_type": "BUY",
                "lot_size": stock['lot_size'],
                "quantity": stock['lot_size'],
                "high": str(high),
                "low": str(low),
                "is_upper_band": upperBand,
                "entry": AppUtils.round2(entry),
                "target": AppUtils.round2(target),
                "new_target": newTarget,
                "sl": AppUtils.round2(sl),
                "tsl": AppUtils.round2(sl),
                "previous_candle": None,
                "profit_loss": 0,
                "is_entry": False,
                "is_new_target": False,
                "is_exit": False,
                "is_tsl": False,
                "is_international": is_international,
                "entry_price": None,
                "entry_at": None,
                "exit_at": None,
                "exit_price": None,
                "created_at": datetime.fromtimestamp(time),
                "status": 0,
            }
            return result
        except Exception as ex:
            AppConstants.log.error(f"Calculate entry:  {ex}")
            return None

    async def updateStrikePrice(db, strategyName, strikeKey, strikeData, stock, currentCandle):
        try:
            dbOption = AppDatabase.getName().model_option
            dbSetting = AppDatabase.getName().strategy_setting

            premium = 0
            timeFrame = 2
            changeStrikePrice = False

            setting = await db[dbSetting].find_one({'strategy_name': strategyName})
            if setting is not None:
                timeFrame = int(setting['time_frame'].replace("M", ""))
                premium = int(setting['premium'])

            if stock['symbol'] == "BANKNIFTY":
                minPrice = 150
                maxPrice = 500
            else:
                minPrice = 125
                maxPrice = 300

            if currentCandle[2] < minPrice:
                changeStrikePrice = True
                print(
                    f"update strike: {datetime.fromtimestamp(currentCandle[0])} | {currentCandle}")
                if strikeData['status'] == "CE":
                    print(f"sk: Before CE {strikeData['ITM']}")
                    strikeData['ITM'] = strikeData['ITM'] - premium
                    print(f"sk: After CE {strikeData['ITM']}")
                else:
                    print(f"sk: Before PE {strikeData['OTM']}")
                    strikeData['OTM'] = strikeData['OTM'] + premium
                    print(f"sk: After PE {strikeData['OTM']}")

            if currentCandle[2] > maxPrice:
                print(
                    f"update strike: {datetime.fromtimestamp(currentCandle[0])} | {currentCandle}")
                changeStrikePrice = True
                if strikeData['status'] == "CE":
                    print(f"sk: Before CE {strikeData['ITM']}")
                    strikeData['ITM'] = strikeData['ITM'] + premium
                    print(f"sk: After CE {strikeData['ITM']}")
                else:
                    print(f"sk: Before PE {strikeData['OTM']}")
                    strikeData['OTM'] = strikeData['OTM'] - premium
                    print(f"sk: After PE {strikeData['OTM']}")

            if changeStrikePrice:
                newStocks = []
                noOTMStock = False
                noITMStock = False

                for sData in strikeData['stocks']:
                    if sData['strike_price'] == strikeData['OTM']:
                        noOTMStock = True
                    if sData['strike_price'] == strikeData['ITM']:
                        noITMStock = True
                expiry_date = await AppUtils.getExpiryDate()
                if noOTMStock == False and strikeData['status'] == "PE":
                    stock = await db[dbOption].find_one(
                        {'strike_price': strikeData['OTM'], 'option_type': strikeData['status'], 'expiry_date': expiry_date})

                    if stock is not None:
                        newStocks.extend(strikeData['stocks'])
                        TMSymbol = f"{stock['exchange']}:{stock['stock_name']}"
                        stock['is_upper_band_break'] = False
                        stock['is_lower_band_break'] = False
                        stock['previous_candle'] = None
                        stock['confirmation_candle'] = None
                        stock['band_timing'] = None
                        stock['pair_candle'] = []
                        newStocks.append(stock)
                        strikeData['stocks'] = newStocks

                        stockData = RedisDB.getJson(key="ws_stocks")
                        isSubscribed = False
                        if stockData is not None:
                            for stockD in stockData:
                                if stockD['fyToken'] == stock['fyToken']:
                                    isSubscribed = True
                                    break
                        else:
                            stockData = []
                        if isSubscribed == False:
                            stockData.extend(stock)
                            await StrgyUtils.subscribeWs(AppConstants.websocket, stockData)

                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                            exchangeCode=stock['exchange_code'],  present=False)

                if noITMStock == False and strikeData['status'] == "CE":
                    stock = await db[dbOption].find_one(
                        {'strike_price': strikeData['ITM'], 'option_type': strikeData['status'], 'expiry_date': expiry_date})

                    if stock is not None:
                        newStocks.extend(strikeData['stocks'])
                        TMSymbol = f"{stock['exchange']}:{stock['stock_name']}"
                        stock['is_upper_band_break'] = False
                        stock['is_lower_band_break'] = False
                        stock['previous_candle'] = None
                        stock['confirmation_candle'] = None
                        stock['band_timing'] = None
                        stock['pair_candle'] = []
                        newStocks.append(stock)
                        strikeData['stocks'] = newStocks

                        stockData = RedisDB.getJson(key="ws_stocks")
                        isSubscribed = False
                        if stockData is not None:
                            for stockD in stockData:
                                if stockD['fyToken'] == stock['fyToken']:
                                    isSubscribed = True
                                    break
                        else:
                            stockData = []
                        if isSubscribed == False:
                            stockData.extend(stock)
                            await StrgyUtils.subscribeWs(AppConstants.websocket, stockData)

                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                            exchangeCode=stock['exchange_code'],  present=False)

                # save changes to redis
                RedisDB.setJson(key=strikeKey, data=strikeData)
        except Exception as ex:
            AppConstants.log.error(f"Update strike price:  {ex}")

    ################################################################################
    # SOF: Websocket Subscription
    ################################################################################

    async def subscribeWs(ws, stocks):
        unSubscribe = await StrgyUtils.UnSubscribeWSToken(stocks)
        subscribe = await StrgyUtils.SubscribeWSToken(stocks)
        print(f"SubWS: {subscribe}")
        if unSubscribe is not None:
            await ws.send(json.dumps(jsonable_encoder(unSubscribe)))
        if subscribe is not None:
            await ws.send(json.dumps(jsonable_encoder(subscribe)))

    async def SubscribeWSToken(stocks):
        subscribe = {
            "T": "SUB_L2", "L2LIST": [], "SUB_T": 1
        }
        symbols = []
        if stocks is not None:
            for stock in stocks:
                symbols.append(f"{stock['fyers_stock_name']}")

        subscribe['L2LIST'] = symbols
        return subscribe

    async def UnSubscribeWSToken(stocks):
        subscribe = {
            "T": "SUB_L2", "L2LIST": [], "SUB_T": 0
        }
        symbols = []
        if stocks is not None:
            for stock in stocks:
                symbols.append(f"{stock['exchange']}:{stock['stock_name']}")

        subscribe['L2LIST'] = symbols
        return subscribe

    async def createEntry(entry):
        try:
            db = await AppUtils.openDb(isAsync=True)
            dbStrategy = AppDatabase.getName().strategy
            sId = str(ObjectId())
            entry['_id'] = sId
            await db[dbStrategy].insert_one(jsonable_encoder(entry))
            return entry
        except Exception as ex:
            AppConstants.log.error(f"Create entry: {ex}")

    async def updateEntry(entry):
        try:
            db = await AppUtils.openDb(isAsync=True)
            dbStrategy = AppDatabase.getName().strategy
            await db[dbStrategy].update_one({'_id': entry['_id']}, {'$set': jsonable_encoder(entry)})
            return entry
        except Exception as ex:
            AppConstants.log.error(f"Update entry: {ex}")

    async def checkEntry(timeFrame, dayTarget, stockKey, stock, entryKey, entryData, currentStock):
        try:
            if entryData is not None:
                profitLoss = 0.0
                cIndex = []
                hasData = []
                for index, entry in enumerate(entryData):
                    if entry['symbol'] == stock['symbol']:
                        if entry['fyToken'] is not None and currentStock['fyToken'] is not None and int(entry['fyToken']) == int(currentStock['fyToken']) and entry['status'] == 0:
                            if len(cIndex) > 0 and index not in cIndex:
                                cIndex.append(index)
                            else:
                                cIndex.append(index)
                        elif entry['fyToken'] is not None and currentStock['fyToken'] is not None and int(entry['fyToken']) == int(currentStock['fyToken']) and entry['status'] != 0:
                            hasData.append(index)

                if len(cIndex) > 0:
                    for index in cIndex:
                        entry = entryData[index]
                        strikeKey = str(entry['strike_key'])
                        strikeData = RedisDB.getJson(key=strikeKey)

                        ################################################################################################################
                        # ACTION :  CONDITION MEET TAKE ENTRY
                        ################################################################################################################
                        if entry['is_entry'] == False and currentStock['ltp'] >= float(entry['entry']):
                            entry['is_entry'] = True
                            entry['entry_at'] = AppUtils.getCurrentDateTimeStamp()
                            entry['entry_price'] = currentStock['ltp']

                            # Create entry & save into DB
                            if "_id" not in entry:
                                entry = await StrgyUtils.createEntry(entry)
                                if entry is not None:
                                    # Save to redis
                                    RedisDB.setJson(
                                        key=entryKey, data=entryData)
                                    RedisDB.setJson(
                                        key=strikeKey, data=strikeData)
                                    # Place Order
                                    await StrgyUtils.placeOrder(entry, currentStock['ltp'])
                                    break

                        if entry is not None:
                            ################################################################################################################
                            # ACTION :  CHECK TARGET
                            ################################################################################################################
                            if entry['is_entry'] and entry['is_exit'] == False and currentStock['ltp'] >= float(entry['target']):
                                entry['status'] = 1
                                entry['is_exit'] = True
                                entry['exit_at'] = AppUtils.getCurrentDateTimeStamp()
                                entry['exit_price'] = currentStock['ltp']
                                strikeData['is_take_entry'] = True
                                strikeData['strgy_in_progress'] = False
                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)
                                RedisDB.setJson(key=strikeKey, data=strikeData)
                                await StrgyUtils.updateEntry(entry)
                                await StrgyUtils.exitOrder(entry, currentStock['ltp'])
                            ################################################################################################################
                            # ACTION :  CHECK NEW TARGET
                            ################################################################################################################
                            elif entry['is_new_target'] == False and entry['new_target'] is not None and currentStock['ltp'] >= float(entry['new_target']):
                                entry['new_target'] = str(currentStock['ltp'])
                                entry['is_new_target'] = True
                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)

                            elif entry['is_new_target'] and currentStock['ltp'] <= float(entry['new_target']):
                                entry['status'] = 2
                                entry['is_exit'] = True
                                entry['exit_at'] = AppUtils.getCurrentDateTimeStamp()
                                entry['exit_price'] = currentStock['ltp']
                                strikeData['is_take_entry'] = True
                                strikeData['strgy_in_progress'] = False
                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)
                                RedisDB.setJson(key=strikeKey, data=strikeData)

                                await StrgyUtils.updateEntry(entry)
                                await StrgyUtils.exitOrder(entry, currentStock['ltp'])

                            ################################################################################################################
                            # ACTION : CHECK TSL
                            ################################################################################################################
                            elif entry['is_entry'] and entry['is_exit'] == False and currentStock['ltp'] <= float(entry['tsl']):
                                if float(entry['tsl']) == float(entry['sl']):
                                    entry['status'] = 3
                                else:
                                    entry['status'] = 4
                                entry['is_exit'] = True
                                entry['exit_at'] = AppUtils.getCurrentDateTimeStamp()
                                entry['exit_price'] = currentStock['ltp']
                                strikeData['is_take_entry'] = True
                                strikeData['strgy_in_progress'] = False

                                noOfEntry = [
                                    x for x in entryData if x['symbol'] == stock['symbol']]
                                if noOfEntry is not None:
                                    if len(noOfEntry) >= 2:
                                        if (noOfEntry[-2:][0]['status'] == 3 or noOfEntry[-2:][0]['status'] == 4) and (noOfEntry[-2:][1]['status'] == 3 or noOfEntry[-2:][1]['status'] == 4):
                                            strikeData['is_take_entry'] == False

                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)
                                RedisDB.setJson(key=strikeKey, data=strikeData)

                                # Update entry in MongoDB
                                await StrgyUtils.updateEntry(entry)
                                await StrgyUtils.exitOrder(entry, currentStock['ltp'])
                            ################################################################################################################
                            # ACTION : CHECK SL
                            ################################################################################################################
                            elif entry['is_entry'] and entry['is_exit'] == False and currentStock['ltp'] <= float(entry['sl']):
                                entry['status'] = 3
                                entry['is_exit'] = True
                                entry['exit_at'] = AppUtils.getCurrentDateTimeStamp()
                                entry['exit_price'] = currentStock['ltp']
                                strikeData['is_take_entry'] = True
                                strikeData['strgy_in_progress'] = False

                                noOfEntry = [
                                    x for x in entryData if x['symbol'] == stock['symbol']]
                                if noOfEntry is not None and len(noOfEntry) >= 2:
                                    if (noOfEntry[-2:][0]['status'] == 3 or noOfEntry[-2:][0]['status'] == 4) and (noOfEntry[-2:][1]['status'] == 3 or noOfEntry[-2:][1]['status'] == 4):
                                        strikeData['is_take_entry'] == False

                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)
                                RedisDB.setJson(key=strikeKey, data=strikeData)

                                # Update entry in MongoDB
                                await StrgyUtils.updateEntry(entry)
                                await StrgyUtils.exitOrder(entry, currentStock['ltp'])

                            ################################################################################################################
                            # ACTION : IF NO ACTIVITY FOR 30 MIN THEN EXIT THE TRADE
                            ################################################################################################################
                            elif entry['is_entry'] and entry['is_exit'] == False:
                                entryDate = datetime.fromtimestamp(
                                    entry['entry_at'])
                                entryDate = int(
                                    (entryDate + timedelta(minutes=30)).timestamp())
                                if entryDate < AppUtils.getCurrentDateTimeStamp():
                                    entry['status'] = 6
                                    entry['is_exit'] = True
                                    entry['exit_at'] = AppUtils.getCurrentDateTimeStamp()
                                    entry['exit_price'] = currentStock['ltp']
                                    strikeData['is_take_entry'] = True
                                    strikeData['strgy_in_progress'] = False

                                    # Save to redis
                                    RedisDB.setJson(
                                        key=strikeKey, data=strikeData)
                                    RedisDB.setJson(
                                        key=entryKey, data=entryData)

                                    # Update entry in MongoDB
                                    await StrgyUtils.updateEntry(entry)
                                    await StrgyUtils.exitOrder(entry, currentStock['ltp'])

                            ################################################################################################################
                            # CONDITION : IF MARKET REACHES 3:14 CLOSE ALL THE OPENING TRADES
                            ################################################################################################################
                            if entry['is_entry'] and entry['is_exit'] == False:
                                marketEndTime = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "1511")
                                if AppUtils.getCurrentDateTimeStamp() > marketEndTime:
                                    entry['status'] = 5
                                    entry['is_exit'] = True
                                    entry['exit_at'] = AppUtils.getCurrentDateTimeStamp(
                                    )
                                    entry['exit_price'] = currentStock['ltp']
                                    strikeData['trade_status'] = False
                                    strikeData['is_take_entry'] = False
                                    strikeData['strgy_in_progress'] = False

                                    # Save to redis
                                    RedisDB.setJson(
                                        key=strikeKey, data=strikeData)
                                    RedisDB.setJson(
                                        key=entryKey, data=entryData)

                                    # Update entry in MongoDB
                                    await StrgyUtils.updateEntry(entry)
                                    await StrgyUtils.exitOrder(entry, currentStock['ltp'])

                            ################################################################################################################
                            # After 2 continues SL we wait for 30 min to take next trade
                            ################################################################################################################
                            if entry['is_entry'] and entry['is_exit']:
                                noOfEntry = [
                                    x for x in entryData if x['symbol'] == stock['symbol']]

                                if noOfEntry is not None:
                                    if len(noOfEntry) >= 2:
                                        sortedData = sorted(noOfEntry, key=lambda k:
                                                            k['created_at'], reverse=True)
                                        #####################################################################################
                                        # Condition : 2nd Trade - IF SL TRIGRRED THEN CONTINUE THE TRADE AFTER 30 MIN PAUSE
                                        #####################################################################################
                                        if sortedData[0]['exit_at'] is not None and (sortedData[0]['status'] == 3 or sortedData[0]['status'] == 4) and (sortedData[1]['status'] == 3 or sortedData[1]['status'] == 4):
                                            exitDate = datetime.fromtimestamp(
                                                sortedData[0]['exit_at'])
                                            exitDate = int(
                                                (exitDate + timedelta(minutes=30)).timestamp())
                                            if exitDate < AppUtils.getCurrentDateTimeStamp():
                                                strikeData['is_take_entry'] = True
                                            else:
                                                strikeData['is_take_entry'] = False
                                            # Save to redis
                                            RedisDB.setJson(
                                                key=strikeKey, data=strikeData)

                elif len(hasData) > 0:
                    ################################################################################################################
                    # After 2 continues SL we wait for 30 min to take next trade
                    ################################################################################################################
                    entry = entryData[0]
                    strikeKey = str(entry['strike_key'])
                    strikeData = RedisDB.getJson(key=strikeKey)
                    if entry['is_entry'] and entry['is_exit']:
                        noOfEntry = [
                            x for x in entryData if x['symbol'] == stock['symbol']]

                        if noOfEntry is not None:
                            if len(noOfEntry) >= 2:
                                sortedData = sorted(noOfEntry, key=lambda k:
                                                    k['exit_at'], reverse=True)
                                if (sortedData[0]['status'] == 3 or sortedData[0]['status'] == 4) and (sortedData[1]['status'] == 3 or sortedData[1]['status'] == 4):
                                    exitDate = datetime.fromtimestamp(
                                        sortedData[0]['exit_at'])
                                    exitDate = int(
                                        (exitDate + timedelta(minutes=30)).timestamp())
                                    if exitDate < AppUtils.getCurrentDateTimeStamp():
                                        strikeData['is_take_entry'] = True
                                        # Save to redis
                                        RedisDB.setJson(
                                            key=strikeKey, data=strikeData)

                for index, entry in enumerate(entryData):
                    # #######################################################################
                    # NOTE: Use the below comment to get calculate P/L for individual stocks
                    # if entry['symbol'] == stock['symbol'] and entry['is_exit']:
                    # #######################################################################

                    if entry['is_exit']:
                        profitLoss += round(((float(entry['exit_price']) - float(
                            entry['entry_price'])) * int(entry['quantity'])), 2)

                    elif entry['is_entry'] and entry['is_exit'] == False:
                        currentLtp = RedisDB.getJson(
                            key=f"{AppConstants.stock}{entry['fyToken']}")
                        if currentLtp is not None:
                            profitLoss += round(((currentLtp['ltp'] - float(
                                entry['entry_price'])) * int(entry['quantity'])), 2)

                if float(profitLoss) >= float(dayTarget):
                    stockData = RedisDB.getJson(key=stockKey)
                    for script in stockData:
                        strikeKey = f"{AppConstants.strike}{script['exchange_code']}_{timeFrame}"
                        strikeData = RedisDB.getJson(key=strikeKey)
                        strikeData['trade_status'] = False
                        strikeData['is_take_entry'] = False
                        strikeData['strgy_in_progress'] = False
                        RedisDB.setJson(key=strikeKey, data=strikeData)

                    for index, entry in enumerate(entryData):
                        ################################################################################################################
                        # CONDITION : IF PROFIT REACHED STOP THE TRADE AND EXIT THE ORDER
                        ################################################################################################################
                        strikeKey = str(entry['strike_key'])
                        if entry['is_entry'] and entry['is_exit'] == False:
                            key = f"{AppConstants.stock}{entry['fyToken']}"
                            currentStock = RedisDB.getJson(key=key)
                            entry['status'] = 1
                            entry['is_exit'] = True
                            entry['exit_at'] = AppUtils.getCurrentDateTimeStamp()
                            entry['exit_price'] = currentStock['ltp']
                            # Update entry in MongoDB
                            await StrgyUtils.updateEntry(entry)
                            await StrgyUtils.exitOrder(entry, currentStock['ltp'])
                        else:
                            entryData.pop(index)

                    # Save to redis
                    RedisDB.setJson(key=entryKey, data=entryData)

        except Exception as ex:
            AppConstants.log.error(f"Check entry: {ex}")

    async def placeOrder(entry, ltp, isInternational=False):
        try:
            db = await AppUtils.openDb()
            dbUser = AppDatabase.getName().user
            dbAccount = AppDatabase.getName().account
            dbOrder = AppDatabase.getName().strategy_order
            dbMap = AppDatabase.getName().map_strategy

            fcmTokens = []
            async for user in db[dbUser].find({'is_live': True, 'is_subscribed': True}):
                isMapped = await db[dbMap].find_one({'strategy_id': entry['strategy_setting_id'], 'user_id': user['_id']})
                if isMapped:
                    async for account in db[dbAccount].find({'user_id': user['_id']}):
                        if account['trade_status'] or account['paper_trade']:
                            # print('------------------------')
                            # print('---Order Data coming ---')
                            # print('------------------------')
                            quantity = math.floor(account['margin'] / 25000)

                            orderId = "Xybyiyiaq7814"
                            orderLog = f"{entry['stock_name']} - {entry['order_type']} Order placed @{ltp}"
                            orderQnty = (entry['lot_size'] * quantity)
                            isOrderPlace = True
                            paperTrade = True
                            symbol = entry['stock_name']
                            if quantity > 0:

                                isUser = True
                                if entry['strategy_setting_id'] != "642ceed4ff3572e347d0d675":
                                    isUser = user['_id'] != "63eda0b616a2a764c446cc8e"

                                if account['trade_status'] and isUser and account['broker'] == AppUtils.getTradingPlatform().flatTrade:
                                    symbol = entry['flat_stock_name']
                                    jData = {
                                        "uid": account['client_id'],
                                        "actid": account['client_id'],
                                        "exch": "NFO",
                                        "tsym": symbol,
                                        "qty": str(orderQnty),
                                        "prc": "0.0",
                                        "prd": "M",
                                        "trantype": "B",
                                        "prctyp": "MKT",
                                        "ret": "DAY",
                                        "ordersource": "API"
                                    }
                                    payload = "jData=" + \
                                        json.dumps(jData) + \
                                        f"&jKey={account['access_token']}"

                                    response = requests.post(
                                        ApiTerminal.flatTradeApi['placeOrder'], data=payload)

                                    if response.status_code == 200:
                                        data = response.json()
                                        if data['stat'] == "Ok":
                                            orderId = data['norenordno']
                                            paperTrade = False
                                            orderLog = "Buy Order placed successfully"
                                        else:
                                            isOrderPlace = False
                                            orderLog = "Failed to placed buy order"
                                    else:
                                        orderLog = "Failed to placed buy order"
                                        isOrderPlace = False

                                elif account['trade_status'] and isUser and account['broker'] == AppUtils.getTradingPlatform().fyers:
                                    accessToken = f"{account['api_key']}:{account['access_token']}"
                                    header = {"Content-Type": "application/json",
                                              "Authorization": accessToken}
                                    symbol = entry['fyers_stock_name']
                                    jData = {
                                        "symbol": symbol,
                                        "qty": orderQnty,
                                        "type": 2,
                                        "side": 1,
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
                                            paperTrade = False
                                            orderLog = f"Buy Order placed successfully"
                                        else:
                                            isOrderPlace = False
                                            orderLog = "Failed to placed buy order"
                                    else:
                                        orderLog = "Failed to placed buy order"
                                        isOrderPlace = False

                                if isOrderPlace:
                                    order = {
                                        "_id": str(ObjectId()),
                                        "strategy_setting_id": entry['strategy_setting_id'],
                                        "user_id": user['_id'],
                                        "strategy_id": entry['_id'],
                                        "client_id": account['client_id'],
                                        "trading_platform": account['broker'],
                                        "stock_name": symbol,
                                        "fyToken": entry['fyToken'],
                                        "order_id": orderId,
                                        "order_type": entry['order_type'],
                                        "quantity": orderQnty,
                                        "entry_price": ltp,
                                        "entry_at": AppUtils.getCurrentDateTimeStamp(),
                                        "exit_price": None,
                                        'exit_at': None,
                                        "order_time": AppUtils.getCurrentDateTime(),
                                        "order_log": orderLog,
                                        "paper_trade": paperTrade,
                                        "status": entry['status'],
                                    }
                                    await db[dbOrder].insert_one(jsonable_encoder(order))

                                    # if user['f_token'] is not None:
                                    #     fcmTokens.append(user['f_token'])

            # if len(fcmTokens) > 0:
            #     # notificationMsg = orderLog
            #     notificationMsg = f"{entry['stock_name']} - {entry['order_type']} entry @{ltp}"
            #     return AppUtils.sendPushNotification(
            #         fcm_token=fcmTokens,  message_title=AppConstants.appName, message_body=notificationMsg)
        except Exception as ex:
            AppConstants.log.error(f"Place order: {ex}")

    async def exitOrder(entry, ltp):
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
                orderLog = f"{entry['stock_name']} - Sell Order placed @{ltp}"
                orderQnty = order['quantity']

                if order['paper_trade'] == False and account['broker'] == AppUtils.getTradingPlatform().flatTrade:
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
                    else:
                        orderLog = "Failed to placed sell order successfully"

                elif order['paper_trade'] == False and account['broker'] == AppUtils.getTradingPlatform().fyers:
                    accessToken = f"{account['api_key']}:{account['access_token']}"
                    header = {"Content-Type": "application/json",
                              "Authorization": accessToken}
                    jData = {
                        "symbol": entry['fyers_stock_name'],
                        "qty": orderQnty,
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
                            orderLog = "Sell Order placed successfully"
                        else:
                            orderLog = "Failed to placed sell order successfully"
                    else:
                        orderLog = "Failed to placed sell order successfully"

                updateQuery = {'status': entry['status'],
                               'exit_price': ltp,
                               'exit_at': AppUtils.getCurrentDateTimeStamp(),
                               'order_id': f"{order['order_id']} | {orderId}",
                               'order_log': f"{order['order_log']} | {orderLog}"}

                await db[dbOrder].update_one({'_id': order['_id']}, {'$set': updateQuery})

                # if user['f_token'] is not None:
                #     fcmTokens.append(user['f_token'])

            # if len(fcmTokens) > 0:
            #     if entry['status'] == 1:
            #         entryStatus = "TARGET Achieved"
            #     elif entry['status'] == 2:
            #         entryStatus = "NEW TARGET Achieved"
            #     elif entry['status'] == 3:
            #         entryStatus = "SL HIT Reached"
            #     elif entry['status'] == 4:
            #         entryStatus = "TSL HIT Reached"
            #     else:
            #         entryStatus = "LEVEL Reached"
            #     notificationMsg = f"{entry['stock_name']} - {entry['order_type']} {entryStatus} @{ltp}"
            #     return AppUtils.sendPushNotification(
            #         fcm_token=fcmTokens,  message_title=AppConstants.appName, message_body=notificationMsg)
        except Exception as ex:
            AppConstants.log.error(f"Exit order: {ex}")

    async def exitOrderSquareOff(exitOrder: ExitOrderModel, requestedUser: UserModel):
        try:
            db = await AppUtils.openDb()
            dbUser = AppDatabase.getName().user
            dbAccount = AppDatabase.getName().account
            dbOrder = AppDatabase.getName().strategy_order

            user = None
            ltp = None
            fcmTokens = []
            query = {
                'status': 0
            }

            if exitOrder.is_admin:
                user = await db[dbUser].find_one({'app_id': requestedUser})
                if user is not None and AppUtils.getRole().superAdmin == user['role']:
                    user = None
                    if exitOrder.order_id is not None:
                        query['order_id'] = exitOrder.order_id
                    if exitOrder.user_id is not None:
                        query['user_id'] = exitOrder.user_id
                    if exitOrder.strategy_id is not None:
                        query['strategy_setting_id'] = exitOrder.strategy_id
                else:
                    return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
            else:
                user = await db[dbUser].find_one({'app_id': requestedUser})
                query['user_id'] = user['_id']
                if exitOrder.order_id is not None:
                    query['order_id'] = exitOrder.order_id

            async for order in db[dbOrder].find(query).sort([('_id', -1)]):
                if user is None:
                    user = await db[dbUser].find_one({'_id': order['user_id']})
                account = await db[dbAccount].find_one({'client_id': order['client_id']})

                print(order)

                currentLtp = RedisDB.getJson(
                    key=f"{AppConstants.stock}{order['fyToken']}")
                if currentLtp is not None:
                    ltp = currentLtp['ltp']
                orderId = "Xybyiyiaq7814"
                orderLog = f"{order['stock_name']} - Sell Order placed @{ltp}"
                orderQnty = order['quantity']
                if order['paper_trade'] == False and account['broker'] == AppUtils.getTradingPlatform().flatTrade:
                    jData = {
                        "uid": account['client_id'],
                        "actid": account['client_id'],
                        "exch": "NFO",
                        "tsym": order['stock_name'],
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
                    else:
                        orderLog = "Failed to placed sell order successfully"

                elif order['paper_trade'] == False and account['broker'] == AppUtils.getTradingPlatform().fyers:
                    accessToken = f"{account['api_key']}:{account['access_token']}"
                    header = {"Content-Type": "application/json",
                              "Authorization": accessToken}
                    jData = {
                        "symbol": order['stock_name'],
                        "qty": orderQnty,
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
                            orderLog = "Sell Order placed successfully"
                        else:
                            orderLog = "Failed to placed sell order successfully"
                    else:
                        orderLog = "Failed to placed sell order successfully"

                updateQuery = {'status': 7,
                               'exit_price': ltp,
                               'exit_at': AppUtils.getCurrentDateTimeStamp(),
                               'order_id': f"{order['order_id']} | {orderId}",
                               'order_log': f"{order['order_log']} | {orderLog}"}

                await db[dbOrder].update_one({'_id': order['_id']}, {'$set': updateQuery})

                # if user['f_token'] is not None:
                #     fcmTokens.append(user['f_token'])

                # if len(fcmTokens) > 0:
                #     notificationMsg = f"{entry['stock_name']} - Manually Closed SELL @ {ltp}"
                #     return AppUtils.sendPushNotification(
                #         fcm_token=fcmTokens,  message_title=AppConstants.appName, message_body=notificationMsg)
            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Order processed")
        except Exception as ex:
            AppConstants.log.error(f"Exit order Manual: {ex}")

    # Back Test
    async def checkEntryBT(timeFrame, dayTarget, setting, stockKey, stock, entryKey, entryData, currentCandle):
        try:
            if entryData is not None:
                profitLoss = 0.0
                cIndex = []
                hasData = []
                for index, entry in enumerate(entryData):
                    if int(entry['exchange_code']) == int(stock['exchange_code']) and entry['status'] == 0:
                        cIndex.append(index)
                    elif int(entry['exchange_code']) == int(stock['exchange_code']) and entry['status'] != 0:
                        hasData.append(index)
                # print(f"Entry length : {len(cIndex)}")

                if len(cIndex) > 0:
                    for index in cIndex:
                        entry = entryData[index]
                        strikeKey = str(entry['strike_key'])
                        strikeData = RedisDB.getJson(key=strikeKey)

                        ################################################################################################################
                        # ACTION :  CONDITION MEET TAKE ENTRY
                        ################################################################################################################
                        if entry['is_entry'] == False and currentCandle[2] >= float(entry['entry']):
                            entry['is_entry'] = True
                            entry['entry_at'] = currentCandle[0]
                            entry['entry_price'] = float(entry['entry'])

                            # print('------------------------')
                            # print('--- New Entry ---')
                            # print('------------------------')

                            # Create entry & save into DB
                            entry = await StrgyUtils.createEntry(entry)
                            if entry is not None:
                                strikeData['is_take_entry'] = False
                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)
                                RedisDB.setJson(key=strikeKey, data=strikeData)

                                # Place Order
                                await StrgyUtils.placeOrder(entry, float(entry['entry']))
                                break

                        if entry is not None:
                            ################################################################################################################
                            # ACTION :  CHECK TARGET
                            ################################################################################################################
                            if entry['is_entry'] and entry['is_exit'] == False and currentCandle[2] >= float(entry['target']):
                                entry['status'] = 1
                                entry['is_exit'] = True
                                entry['exit_at'] = currentCandle[0]
                                entry['exit_price'] = float(entry['target'])
                                strikeData['is_take_entry'] = True
                                strikeData['strgy_in_progress'] = False
                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)
                                RedisDB.setJson(key=strikeKey, data=strikeData)
                                await StrgyUtils.updateEntry(entry)
                                await StrgyUtils.exitOrder(entry, float(entry['target']))

                            ################################################################################################################
                            # ACTION :  CHECK NEW TARGET
                            ################################################################################################################
                            elif entry['is_entry'] and entry['is_new_target'] == False and entry['new_target'] is not None and currentCandle[2] >= float(entry['new_target']):
                                entry['new_target'] = str(currentCandle[2])
                                entry['is_new_target'] = True
                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)

                            elif entry['is_entry'] and entry['is_new_target'] and currentCandle[2] <= float(entry['new_target']):
                                entry['status'] = 2
                                entry['is_exit'] = True
                                entry['exit_at'] = currentCandle[0]
                                entry['exit_price'] = float(
                                    entry['new_target'])
                                strikeData['is_take_entry'] = True
                                strikeData['strgy_in_progress'] = False
                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)
                                RedisDB.setJson(key=strikeKey, data=strikeData)

                                await StrgyUtils.updateEntry(entry)
                                await StrgyUtils.exitOrder(entry, float(entry['new_target']))

                            ################################################################################################################
                            # ACTION : CHECK TSL
                            ################################################################################################################
                            elif entry['is_entry'] and entry['is_exit'] == False and currentCandle[3] <= float(entry['tsl']):
                                if float(entry['tsl']) == float(entry['sl']):
                                    entry['status'] = 3
                                else:
                                    entry['status'] = 4
                                entry['is_exit'] = True
                                entry['exit_at'] = currentCandle[0]
                                entry['exit_price'] = float(entry['tsl'])
                                strikeData['is_take_entry'] = True
                                strikeData['strgy_in_progress'] = False

                                noOfEntry = [
                                    x for x in entryData if x['symbol'] == stock['symbol']]
                                if noOfEntry is not None:
                                    if len(noOfEntry) >= 2:
                                        if (noOfEntry[-2:][0]['status'] == 3 or noOfEntry[-2:][0]['status'] == 4) and (noOfEntry[-2:][1]['status'] == 3 or noOfEntry[-2:][1]['status'] == 4):
                                            strikeData['is_take_entry'] == False

                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)
                                RedisDB.setJson(key=strikeKey, data=strikeData)

                                # Update entry in MongoDB
                                await StrgyUtils.updateEntry(entry)
                                await StrgyUtils.exitOrder(entry, float(entry['tsl']))

                            ################################################################################################################
                            # ACTION : CHECK SL
                            ################################################################################################################
                            elif entry['is_entry'] and entry['is_exit'] == False and currentCandle[3] <= float(entry['sl']):
                                entry['status'] = 3
                                entry['is_exit'] = True
                                entry['exit_at'] = currentCandle[0]
                                entry['exit_price'] = float(entry['sl'])
                                strikeData['is_take_entry'] = True
                                strikeData['strgy_in_progress'] = False

                                noOfEntry = [
                                    x for x in entryData if x['symbol'] == stock['symbol']]
                                if noOfEntry is not None and len(noOfEntry) >= 2:
                                    if (noOfEntry[-2:][0]['status'] == 3 or noOfEntry[-2:][0]['status'] == 4) and (noOfEntry[-2:][1]['status'] == 3 or noOfEntry[-2:][1]['status'] == 4):
                                        strikeData['is_take_entry'] == False

                                # Save to redis
                                RedisDB.setJson(key=entryKey, data=entryData)
                                RedisDB.setJson(key=strikeKey, data=strikeData)

                                # Update entry in MongoDB
                                await StrgyUtils.updateEntry(entry)
                                await StrgyUtils.exitOrder(entry, float(entry['sl']))

                            ################################################################################################################
                            # ACTION : IF NO ACTIVITY FOR 30 MIN THEN EXIT THE TRADE
                            ################################################################################################################
                            elif entry['is_entry'] and entry['is_exit'] == False:
                                entryDate = datetime.fromtimestamp(
                                    entry['entry_at'])
                                entryDate = int(
                                    (entryDate + timedelta(minutes=30)).timestamp())
                                if entryDate < currentCandle[0]:
                                    entry['status'] = 6
                                    entry['is_exit'] = True
                                    entry['exit_at'] = currentCandle[0]
                                    entry['exit_price'] = currentCandle[2]
                                    strikeData['is_take_entry'] = True
                                    strikeData['strgy_in_progress'] = False

                                    # Save to redis
                                    RedisDB.setJson(
                                        key=strikeKey, data=strikeData)
                                    RedisDB.setJson(
                                        key=entryKey, data=entryData)

                                    # Update entry in MongoDB
                                    await StrgyUtils.updateEntry(entry)
                                    await StrgyUtils.exitOrder(entry, entry['exit_price'])

                            ################################################################################################################
                            # CONDITION : IF MARKET REACHES 3:11 CLOSE ALL THE OPENING TRADES
                            ################################################################################################################
                            if entry['is_entry'] and entry['is_exit'] == False:
                                marketEndTime = await AppUtils.combineDateTime(AppConstants.currentDayDate, "1511")
                                if currentCandle[0] > marketEndTime:
                                    tDiff = abs(
                                        currentCandle[2] - float(entry['target']))
                                    sDiff = abs(
                                        currentCandle[2] - float(entry['sl']))
                                    tslDiff = abs(
                                        currentCandle[2] - float(entry['tsl']))
                                    if tDiff < sDiff:
                                        entry['status'] = 1
                                    elif sDiff < tslDiff:
                                        entry['status'] = 3
                                    else:
                                        entry['status'] = 4

                                    entry['is_exit'] = True
                                    entry['exit_at'] = currentCandle[0]
                                    entry['exit_price'] = currentCandle[2]
                                    strikeData['is_take_entry'] = True
                                    strikeData['strgy_in_progress'] = False

                                    # Save to redis
                                    RedisDB.setJson(
                                        key=strikeKey, data=strikeData)
                                    RedisDB.setJson(
                                        key=entryKey, data=entryData)

                                    # Update entry in MongoDB
                                    await StrgyUtils.updateEntry(entry)
                                    await StrgyUtils.exitOrder(entry, entry['exit_price'])

                            ################################################################################################################
                            # After 2 continues SL we wait for 30 min to take next trade
                            ################################################################################################################
                            if entry['is_entry'] and entry['is_exit']:
                                noOfEntry = [
                                    x for x in entryData if x['symbol'] == stock['symbol']]

                                if noOfEntry is not None:
                                    if len(noOfEntry) >= 2:
                                        sortedData = sorted(noOfEntry, key=lambda k:
                                                            k['created_at'], reverse=True)
                                        if sortedData[0]['exit_at'] is not None and (sortedData[0]['status'] == 3 or sortedData[0]['status'] == 4) and (sortedData[1]['status'] == 3 or sortedData[1]['status'] == 4):
                                            exitDate = datetime.fromtimestamp(
                                                sortedData[0]['exit_at'])
                                            exitDate = int(
                                                (exitDate + timedelta(minutes=30)).timestamp())
                                            # print(
                                            #     f"check strike data : {exitDate} < {currentCandle[0]}")
                                            if exitDate < currentCandle[0]:
                                                strikeData['is_take_entry'] = True
                                            else:
                                                strikeData['is_take_entry'] = False
                                            # Save to redis
                                            RedisDB.setJson(
                                                key=strikeKey, data=strikeData)

                elif len(hasData) > 0:
                    ################################################################################################################
                    # After 2 continues SL we wait for 30 min to take next trade
                    ################################################################################################################
                    if entry['is_entry'] and entry['is_exit']:
                        noOfEntry = [
                            x for x in entryData if x['symbol'] == stock['symbol']]

                        if noOfEntry is not None:
                            if len(noOfEntry) >= 2:
                                sortedData = sorted(noOfEntry, key=lambda k:
                                                    k['created_at'], reverse=True)

                                if sortedData[0]['exit_at'] is not None and (sortedData[0]['status'] == 3 or sortedData[0]['status'] == 4) and (sortedData[1]['status'] == 3 or sortedData[1]['status'] == 4):
                                    strikeKey = str(
                                        sortedData[0]['strike_key'])
                                    strikeData = RedisDB.getJson(key=strikeKey)
                                    exitDate = datetime.fromtimestamp(
                                        sortedData[0]['exit_at'])
                                    exitDate = int(
                                        (exitDate + timedelta(minutes=30)).timestamp())
                                    # print(
                                    #     f"check strike data : {exitDate} < {currentCandle[0]}")
                                    if exitDate < currentCandle[0]:
                                        strikeData['is_take_entry'] = True
                                    else:
                                        strikeData['is_take_entry'] = False
                                    # Save to redis
                                    RedisDB.setJson(
                                        key=strikeKey, data=strikeData)

                for index, entry in enumerate(entryData):
                    # #######################################################################
                    # NOTE: Use the below comment to get calculate P/L for individual stocks
                    # if entry['symbol'] == stock['symbol'] and entry['is_exit']:
                    # #######################################################################

                    if entry['is_exit']:
                        # print(
                        #     f"EP : {entry['entry_price']} {entry['exit_price']}")
                        profitLoss += round(((float(entry['exit_price']) - float(
                            entry['entry_price'])) * int(entry['quantity'])), 2)

                    elif entry['is_entry'] and entry['is_exit'] == False:
                        key = f"{AppConstants.candle}{entry['exchange_code']}_{timeFrame}"
                        candleData = RedisDB.getJson(key=key)
                        if candleData is not None:
                            currentCandle = candleData[AppConstants.count:][0]
                            # print(f"currentCandle : {currentCandle}")
                            # print(
                            #     f"EEP : {entry['entry_price']}")
                            profitLoss += round(((currentCandle[2] - float(
                                entry['entry_price'])) * int(entry['quantity'])), 2)

                if float(profitLoss) >= float(dayTarget):
                    print(f"Target Achieved : {profitLoss}")
                    stockData = RedisDB.getJson(key=stockKey)
                    for script in stockData:
                        strikeKey = f"{AppConstants.strike}{script['exchange_code']}_{timeFrame}"
                        strikeData = RedisDB.getJson(key=strikeKey)
                        strikeData['trade_status'] = False
                        strikeData['is_take_entry'] = False
                        strikeData['strgy_in_progress'] = False
                        RedisDB.setJson(key=strikeKey, data=strikeData)

                    for index, entry in enumerate(entryData):
                        strikeKey = str(entry['strike_key'])
                        ################################################################################################################
                        # CONDITION : IF PROFIT REACHED STOP THE TRADE AND EXIT THE ORDER
                        ################################################################################################################
                        if entry['is_entry'] and entry['is_exit'] == False:
                            key = f"{AppConstants.candle}{entry['exchange_code']}_{timeFrame}"
                            candleData = RedisDB.getJson(key=key)
                            currentCandle = candleData[AppConstants.count:][0]
                            # currentCandle = candleData[-1:][0]

                            # print(f"currentCandle : {currentCandle}")

                            tDiff = abs(
                                float(entry['target']) - currentCandle[2])
                            sDiff = abs(
                                currentCandle[2] - float(entry['sl']))
                            tslDiff = abs(
                                currentCandle[2] - float(entry['tsl']))

                            if tDiff < sDiff:
                                entry['status'] = 1
                            elif sDiff < tslDiff:
                                entry['status'] = 3
                            else:
                                entry['status'] = 4

                            entry['is_exit'] = True
                            entry['exit_at'] = currentCandle[0]
                            entry['exit_price'] = currentCandle[2]
                            # Save to redis
                            RedisDB.setJson(key=entryKey, data=entryData)

                            # Update entry in MongoDB
                            await StrgyUtils.updateEntry(entry)
                            await StrgyUtils.exitOrder(entry, entry['exit_price'])
                else:
                    print(f"PL : {profitLoss} | dT: {dayTarget}")

        except Exception as ex:
            AppConstants.log.error(f"Check entry bt: {ex}")
