import asyncio
import json
import math
from threading import Thread
import time
from fastapi import status
from fastapi.encoders import jsonable_encoder
from config.redis_db import RedisDB
from models.user_model import UserModel
from repository.strategy_repo import getCandelData
from utils.api_terminal import ApiTerminal
from utils.app_constants import AppConstants
from utils.app_database import AppDatabase
from utils.app_utils import AppUtils

import pandas as pd
import numpy as np
import requests
from bson import ObjectId
from datetime import datetime, timedelta


async def strategy_3():
    try:
        db = await AppUtils.openDb()
        dbFuture = AppDatabase.getName().model_future
        dbOption = AppDatabase.getName().model_option
        dbSetting = AppDatabase.getName().strategy_setting

        timeFrame = 0
        premium = 200
        setting = await db[dbSetting].find_one({'strategy_name': "strategy_3"})
        if setting['is_live']:
            timeFrame = int(setting['time_frame'].replace("M", ""))
            premium = int(setting['premium'])

            # entryKey = f"{AppConstants.strategy_3}entry_{timeFrame}"
            # entryData = RedisDB.getJson(key=entryKey)
            # #print('---------------------------------------------------------------------')
            # #print(entryData)
            # #print('---------------------------------------------------------------------')

            ###############################################################################
            # SOF: Get First (5 Min) candel

            startTime = "915"

            marketOpenTime = await AppUtils.combineDateTime(
                (datetime.now()).strftime("%d %b %y"), startTime)

            stocks = []
            selectedStocks = []

            async for stock in db[dbFuture].find({'is_subscribed': True}):
                stock['setting'] = setting
                stockKey = f"{AppConstants.strategy_3}stock"
                stockData = RedisDB.getJson(key=stockKey)
                stocks.append(stock)
                if stockData is not None:
                    stockData.append(stock)
                else:
                    stockData = []
                    stockData.append(stock)
                RedisDB.setJson(key=stockKey, data=stockData)

            hasStockData = False
            beforeTime = AppUtils.getCurrentDateTimeStamp()
            for stock in stocks:
                symbol = f"{stock['exchange']}:{stock['stock_name']}"

                time.sleep(1)

                await getCandelData(symbol=symbol, timeFrame=timeFrame,
                                    exchangeCode=stock['exchange_code'], endTime="917", present=True)

                key = f"{AppConstants.candle}{stock['exchange_code']}_{timeFrame}"
                candleData = RedisDB.getJson(key=key)

                if candleData is not None:
                    firstCandle = [
                        x for x in candleData if x[0] == marketOpenTime]
                    ################################################################################
                    # NOTE:
                    # candle format
                    #  [0, 1, 2, 3, 4, 5]
                    #  [epoch_time, open, high, low, close, volume]
                    #  [1674618600,18159.4,18159.4,18143.4,18151.6,185500]
                    ################################################################################

                    # EOF: Get First timeFrame candel
                    ################################################################################
                    if firstCandle is not None and len(firstCandle) > 0:
                        ################################################################################
                        # SOF: Find nearest strike price to get OTM | ATM | ITM
                        strikeKey = f"{AppConstants.strike}{stock['exchange_code']}_{timeFrame}"
                        strikeData = RedisDB.getJson(key=strikeKey)

                        levelKey = f"{AppConstants.candle}level_{stock['exchange_code']}_15"
                        levelData = RedisDB.getJson(key=levelKey)

                        if strikeData is None:
                            optionList = []
                            findSymbol = stock['symbol'].replace("50", "")
                            async for option in db[dbOption].find({'symbol': findSymbol}):
                                optionList.append(option['strike_price'])

                            if optionList is not None:
                                # print(f"premium: {premium}")
                                ATM = min(optionList, key=lambda x: abs(
                                    x-firstCandle[0][4]))
                                OTM = ATM + premium
                                ITM = ATM - premium

                                # print(f">> OTM : {OTM} | ATM : {ATM} | ITM : {ITM}")

                                expiry_date = await AppUtils.getExpiryDate()

                                if stock['symbol'] == "NIFTY50":
                                    premiumPrice = premium / 2
                                else:
                                    premiumPrice = premium

                                OTMPremimums = [
                                    OTM + (premiumPrice*3),
                                    OTM + (premiumPrice*2),
                                    OTM + (premiumPrice*1),
                                    OTM,
                                    OTM - (premiumPrice*1),
                                    OTM - (premiumPrice*2),
                                    OTM - (premiumPrice*3),
                                ]

                                ITMPremimums = [
                                    ITM + (premiumPrice*3),
                                    ITM + (premiumPrice*2),
                                    ITM + (premiumPrice*1),
                                    ITM,
                                    ITM - (premiumPrice*1),
                                    ITM - (premiumPrice*2),
                                    ITM - (premiumPrice*3),
                                ]

                                if stock['symbol'] == "BANKNIFTY":
                                    minPrice = 200
                                    maxPrice = 300
                                else:
                                    minPrice = 150
                                    maxPrice = 200

                                stocks = []
                                currentOTM = None
                                currentOTMStock = None
                                currentITM = None
                                currentITMStock = None

                                for sPrice in OTMPremimums:
                                    async for OTMStock in db[dbOption].find({'expiry_date': expiry_date, 'strike_price': sPrice, 'option_type': "PE"}):
                                        TMSymbol = f"{OTMStock['exchange']}:{OTMStock['stock_name']}"
                                        OTMStock['is_upper_band_break'] = False
                                        OTMStock['is_lower_band_break'] = False
                                        OTMStock['previous_candle'] = None
                                        OTMStock['confirmation_candle'] = None
                                        OTMStock['band_timing'] = None

                                        stocks.append(OTMStock)
                                        selectedStocks.extend(OTMStock)

                                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                            exchangeCode=OTMStock['exchange_code'],  present=False)

                                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                            exchangeCode=OTMStock['exchange_code'],  present=True)

                                        key = f"{AppConstants.candle}{OTMStock['exchange_code']}_{timeFrame}"
                                        candleData = RedisDB.getJson(key=key)

                                        if candleData is not None:
                                            firstCandle = [
                                                x for x in candleData if x[0] == marketOpenTime]

                                            if firstCandle is not None:
                                                firstCandle = firstCandle[0]

                                                if currentOTMStock is not None:
                                                    if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                        if firstCandle[2] < currentOTMStock[2]:
                                                            currentOTM = sPrice
                                                            currentOTMStock = firstCandle
                                                else:
                                                    if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                        currentOTM = sPrice
                                                        currentOTMStock = firstCandle

                                for sPrice in ITMPremimums:
                                    async for ITMStock in db[dbOption].find({'expiry_date': expiry_date, 'strike_price': sPrice, 'option_type': "CE"}):
                                        TMSymbol = f"{ITMStock['exchange']}:{ITMStock['stock_name']}"
                                        ITMStock['is_upper_band_break'] = False
                                        ITMStock['is_lower_band_break'] = False
                                        ITMStock['previous_candle'] = None
                                        ITMStock['confirmation_candle'] = None
                                        ITMStock['band_timing'] = None

                                        stocks.append(ITMStock)
                                        selectedStocks.extend(ITMStock)

                                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                            exchangeCode=ITMStock['exchange_code'],  present=False)

                                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                            exchangeCode=ITMStock['exchange_code'],  present=True)

                                        key = f"{AppConstants.candle}{ITMStock['exchange_code']}_{timeFrame}"
                                        candleData = RedisDB.getJson(key=key)

                                        if candleData is not None:
                                            firstCandle = [
                                                x for x in candleData if x[0] == marketOpenTime]

                                            if firstCandle is not None:
                                                firstCandle = firstCandle[0]

                                                if currentITMStock is not None:
                                                    if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                        if firstCandle[2] < currentITMStock[2]:
                                                            currentITM = sPrice
                                                            currentITMStock = firstCandle
                                                else:
                                                    if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                        currentITM = sPrice
                                                        currentITMStock = firstCandle

                                if currentOTM is None:
                                    currentOTM = OTM

                                if currentITM is None:
                                    currentITM = ITM

                                strikeData = {
                                    "OTM": int(currentOTM),
                                    "ATM": int(ATM),
                                    "ITM": int(currentITM),
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

                                RedisDB.setJson(key=strikeKey, data=strikeData)
                                hasStockData = True
                            # EOF: Find nearest strike price to get OTM | ATM | ITM
                            ################################################################################
                        else:
                            hasStockData = True

            if len(selectedStocks) > 0:
                RedisDB.setJson(key="ws_stocks", data=selectedStocks)

            if hasStockData:
                afterTime = AppUtils.getCurrentDateTimeStamp()
                timeDiff = abs(afterTime-beforeTime)
                sleepTime = ((timeFrame*60) - timeDiff)

                # Start the strategy to take entries based on time frame
                thread = Thread(target=asyncio.run, args=(startStrategy3(setting, timeFrame, startTime, True, sleepTime),),
                                daemon=True, name='strategy_3')
                thread.daemon = True
                thread.start()

        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy is turned off.")
    except Exception as ex:
        # print(f"Error: {ex}")
        # log.error(f"{ex}")
        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, str(ex))


async def startStrategy3(setting, timeFrame, startTime, fromCron, fromTime):
    try:
        while True:
            # print(f">> Executing Time : {datetime.now()}")
            beforeTime = AppUtils.getCurrentDateTimeStamp()
            await checkAndStartTrade(setting, timeFrame, startTime)
            if fromCron:
                fromCron = False
                sleepTime = fromTime - 60
            else:
                afterTime = AppUtils.getCurrentDateTimeStamp()
                timeDiff = abs(afterTime-beforeTime)
                sleepTime = ((timeFrame*60) - timeDiff)
                # print("------------------------------------------------------------")
                # print(f"{sleepTime} | {timeDiff} = {beforeTime} - {afterTime}")
                # print("------------------------------------------------------------")
            time.sleep(sleepTime)
    except Exception as ex:
        print(f"Error Start: {ex}")


async def checkAndStartTrade(setting, timeFrame, startTime):
    try:
        # print(">> start new connection")
        # print(f">> Executing Time : {datetime.now()}")
        db = await AppUtils.openDb(isAsync=True)
        dbFuture = AppDatabase.getName().model_future
        # print("-----------------------------------------------------------------------")
        # print("CHECK AND HIGH LOW BREAKS")
        # print("-----------------------------------------------------------------------")
        async for script in db[dbFuture].find({'is_subscribed': True}):
            strikeKey = f"{AppConstants.strike}{script['exchange_code']}_{timeFrame}"
            strikeData = RedisDB.getJson(key=strikeKey)

            if strikeData['trade_status']:
                if strikeData['is_high_low_break'] == False:
                    ##################################################################################
                    # Get Candle Data from Api and store it on Redis
                    symbol = f"{script['exchange']}:{script['stock_name']}"
                    await getCandelData(symbol=symbol, timeFrame=timeFrame,
                                        exchangeCode=script['exchange_code'], present=True)

                    key = f"{AppConstants.candle}{script['exchange_code']}_{timeFrame}"
                    candleData = RedisDB.getJson(key=key)

                    if candleData is not None:
                        currentCandle = candleData[-1:][0]
                        print(
                            f"checking : {currentCandle[2]} >= {strikeData['high_level']} || {currentCandle[3]}<= {strikeData['low_level']}")

                        #########################################################################################################################################
                        # Condition : IF CANDLE BREAKS HIGH OR LOW TAKE ENTRY
                        #########################################################################################################################################
                        if currentCandle[2] >= strikeData['high_level'] and currentCandle[3] >= strikeData['high_level']:
                            # print(f">> Hign Break | {currentCandle}")
                            strikeData['is_high_low_break'] = True
                            if strikeData['strgy_in_progress'] == False:
                                strikeData['is_take_entry'] = True
                            strikeData['is_close_entry'] = False
                            strikeData['status'] = "PE"
                            print(f"high break >> {strikeData['status']}")
                            RedisDB.setJson(
                                key=strikeKey, data=strikeData)

                        elif currentCandle[2] <= strikeData['low_level'] and currentCandle[3] <= strikeData['low_level']:
                            # print(f">> Low Break | {currentCandle}")
                            strikeData['is_high_low_break'] = True
                            if strikeData['strgy_in_progress'] == False:
                                strikeData['is_take_entry'] = True
                            strikeData['is_close_entry'] = False
                            strikeData['status'] = "CE"
                            print(f"low break >> {strikeData['status']}")
                            RedisDB.setJson(
                                key=strikeKey, data=strikeData)

                        elif currentCandle[2] >= strikeData['high_level'] and currentCandle[3] <= strikeData['high_level'] and currentCandle[4] <= strikeData['high_level']:
                            strikeData['is_high_low_break'] = True
                            if strikeData['strgy_in_progress'] == False:
                                strikeData['is_take_entry'] = True
                            strikeData['is_close_entry'] = False
                            strikeData['status'] = "CE"
                            print(f"low break >> {strikeData['status']}")
                            RedisDB.setJson(
                                key=strikeKey, data=strikeData)

                        elif currentCandle[2] >= strikeData['low_level'] and currentCandle[3] <= strikeData['low_level'] and currentCandle[4] >= strikeData['low_level']:
                            strikeData['is_high_low_break'] = True
                            if strikeData['strgy_in_progress'] == False:
                                strikeData['is_take_entry'] = True
                            strikeData['is_close_entry'] = False
                            strikeData['status'] = "PE"
                            print(f"high break >> {strikeData['status']}")
                            RedisDB.setJson(
                                key=strikeKey, data=strikeData)

                for index, stock in enumerate(strikeData['stocks']):
                    ##################################################################################
                    # Get Candle Data from Api
                    # print(f">> stock: {stock['stock_name']}")

                    symbol = f"{stock['exchange']}:{stock['stock_name']}"
                    await getCandelData(symbol=symbol, timeFrame=timeFrame,
                                        exchangeCode=stock['exchange_code'], present=True)

                    # Get Candle Data from Redis
                    key = f"{AppConstants.candle}{stock['exchange_code']}_{timeFrame}"
                    candleData = RedisDB.getJson(key=key)
                    ##################################################################################

                    if candleData is not None:
                        currentCandle = candleData[-1:][0]
                        # print(f"Candle: {currentCandle}")

                        ################################################################################
                        # Get Historical Data From Redis
                        historyKey = f"{AppConstants.candle}historical_{stock['exchange_code']}_{timeFrame}"
                        previousDayData: list = RedisDB.getJson(
                            key=historyKey)
                        if previousDayData is None:
                            previousDayData = []
                        previousDayData.extend(candleData)
                        ################################################################################
                        df = pd.DataFrame(previousDayData[-20:])
                        bbData = pd.DataFrame(previousDayData[-12:])

                        ################################################################################
                        # Calculate EMA
                        ema = calculate_ema(df[4][-20:], 3)
                        cEMA = round(ema[(len(ema)-3)], 2)
                        # print(f">> : {stock['stock_name']} : EMA {cEMA}")
                        ################################################################################
                        if strikeData['OTM'] == int(stock['strike_price']) or strikeData['ITM'] == int(stock['strike_price']):
                            await checkEntries(db, currentCandle, stock, setting, cEMA)
                            strikeData = RedisDB.getJson(key=strikeKey)
                        await checkConditionAndGetEntry(
                            timeFrame, stock, setting, strikeKey, strikeData, currentCandle, bbData, cEMA)

                        if strikeData['is_take_entry']:
                            await updateStrikePrice(db, stock, candleData)

    except Exception as ex:
        print(f"Error live start: {ex}")


async def checkChangeFromCallPut(index, strikeKey, strikeData, currentCandle, df, cEMA):
    bb = bollinger_bands(df)
    bb = bb.iloc[-1].tolist()
    upperBand = bb[7]
    lowerBand = bb[8]
    stock = strikeData['stocks'][index]

    if currentCandle[2] > upperBand:
        stock['is_lower_band_break'] = False
        if stock['is_upper_band_break'] == False:
            stock['is_upper_band_break'] = True
            stock['band_timing'] = currentCandle[0]

    if currentCandle[3] < lowerBand:
        stock['is_upper_band_break'] = False
        if stock['is_lower_band_break'] == False:
            stock['is_lower_band_break'] = True
            stock['band_timing'] = currentCandle[0]

    #####################################################################################################
    # SOF: CHANGE OF STRIKE PRICE SAY CE TO PE OR PE TO CE
    #####################################################################################################
    # Condition 3: AND THEN BREAKS THE CONFIRMATION CANDLE LOW
    #####################################################################################################
    if stock['is_lower_band_break'] == False and stock['confirmation_candle'] is not None:
        if (strikeData['OTM'] == int(stock['strike_price']) or strikeData['ITM'] == int(stock['strike_price'])) and strikeData['status'] == stock['option_type'] and currentCandle[3] < stock['confirmation_candle'][3]:
            stock['is_upper_band_break'] = False
            stock['is_lower_band_break'] = False
            stock['confirmation_candle'] = None
            print('-----------Confirmation Candle--------------')
            if strikeData['status'] == "CE":
                strikeData['status'] = "PE"
                print('-----------CE -- PE Change -----')
            else:
                strikeData['status'] = "CE"
                print('-----------PE -- CE Change -----')
            print('---------------------------')

    #####################################################################################################
    # Condition 1 : IF MARKET BREAKS UPPER BAND AND CLOSE BELOW THE EMA 3 (BASE CANDLE )
    #####################################################################################################
    if (currentCandle[2] > upperBand or stock['is_upper_band_break']) and currentCandle[4] < cEMA:
        if stock['previous_candle'] is not None:
            #####################################################################################################
            # Condition 2: AND FOLLOWED BY THE CONFIRMATION CANLDE (IT HAS TO CLOSE BELOW THE LOW OF BASE CANDLE )
            #####################################################################################################
            if currentCandle[4] < stock['previous_candle'][3]:
                stock['confirmation_candle'] = currentCandle
        stock['previous_candle'] = currentCandle

    RedisDB.setJson(key=strikeKey, data=strikeData)
    return strikeData
    # EOF: CHANGE OF STRIKE PRICE SAY CE TO PE OR PE TO CE
    #####################################################################################################


async def checkConditionAndGetEntry(timeFrame, stock, setting, strikeKey, strikeData, currentCandle, bbData, cEMA):
    bb = bollinger_bands(bbData)
    bb = bb.iloc[-1].tolist()
    upperBand = bb[7]
    lowerBand = bb[8]

    sKey = f"{AppConstants.strategy_3}status_{stock['exchange_code']}_{timeFrame}"
    status = RedisDB.getJson(key=sKey)

    ################################################################################
    # SOF: Conditions to get entry
    ################################################################################
    # Condition : PRICE HAS TO BREAK THE LOWER BAND
    ################################################################################
    if currentCandle[2] < lowerBand or currentCandle[3] < lowerBand:
        if status is None:
            status = {
                "status": "Below LB",
                "previous_ema": None,
                "previous_candle": None,
            }
        else:
            status['status'] = "Below LB"

        RedisDB.setJson(key=sKey, data=status)

    ################################################################################
    # Condition : PRICE HAS TO BREAK THE UPPER BAND
    ################################################################################
    elif currentCandle[2] > upperBand or currentCandle[3] > upperBand:
        if status is None:
            status = {
                "status": "Above UB",
                "previous_ema": None,
                "previous_candle": None,
            }
        else:
            status['status'] = "Above UB"

        RedisDB.setJson(key=sKey, data=status)

    if status is not None and (strikeData['OTM'] == int(stock['strike_price']) or strikeData['ITM'] == int(stock['strike_price'])) and strikeData['status'] == stock['option_type']:
        if stock['symbol'] == "BANKNIFTY":
            range = 30
        else:
            range = 20

        if status['status'] == "Below LB":
            #################################################################################################################################
            # Condition : IF PRICE TOUCH THE LOWER BAND AND CLOSE INSIDE THE BAND AND DOES NOT TOUCH THE EMA THEN PLACE ORDER FOR CALL
            #################################################################################################################################
            if currentCandle[3] > lowerBand and currentCandle[2] < cEMA:
                ################################################################################
                # Condition : WHOSE RANGE MUST BE LESS THAN 20 / 30 POINTS
                ################################################################################
                if abs(currentCandle[2] - currentCandle[3]) <= range and strikeData['is_take_entry']:
                    getEntry = False
                    marketEndTime = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "1500")
                    # marketEndTime = await AppUtils.combineDateTime("06 Apr 23", "1500")
                    entryKey = f"{AppConstants.strategy_3}entry_{timeFrame}"
                    entryData = RedisDB.getJson(key=entryKey)

                    if stock['symbol'] == "BANKNIFTY":
                        getEntry = currentCandle[2] >= 150 and currentCandle[2] <= 500
                    else:
                        getEntry = currentCandle[2] >= 125 and currentCandle[2] <= 300

                    if currentCandle[0] < marketEndTime and getEntry:
                        entry = await calculateEntry(setting, strikeKey, stock, currentCandle[0], currentCandle[2], currentCandle[3], False)
                        if entryData is not None:
                            entryData.append(entry)
                        else:
                            entryData = []
                            entryData.append(entry)

                        strikeData['is_take_entry'] = False
                        strikeData['strgy_in_progress'] = True
                        print('--------------------------------------')
                        print(f">> entry LB : {entry}")
                        print('--------------------------------------')
                        RedisDB.setJson(key=strikeKey, data=strikeData)
                        RedisDB.setJson(key=entryKey, data=entryData)

        elif status['status'] == "Above UB":
            #############################################################################################################################
            # Condition : IF PRICE TOUCH THE UPPER BAND AND CLOSE INSIDE THE BAND AND DOES NOT TOUCH THE EMA THEN PLACE ORDER FOR PUT
            #############################################################################################################################
            if currentCandle[2] < upperBand and currentCandle[3] > cEMA:
                ##############################################################################################
                # Condition : WHOSE RANGE MUST BE LESS THAN 20 / 30 POINTS
                ##############################################################################################
                if abs(currentCandle[2] - currentCandle[3]) <= range and strikeData['is_take_entry']:
                    getEntry = False
                    marketEndTime = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "1500")
                    # marketEndTime = await AppUtils.combineDateTime("06 Apr 23", "1500")
                    entryKey = f"{AppConstants.strategy_3}entry_{timeFrame}"
                    entryData = RedisDB.getJson(key=entryKey)

                    if stock['symbol'] == "BANKNIFTY":
                        getEntry = currentCandle[2] >= 150 and currentCandle[2] <= 500
                    else:
                        getEntry = currentCandle[2] >= 125 and currentCandle[2] <= 300

                    if currentCandle[0] < marketEndTime and getEntry:
                        entry = await calculateEntry(setting, strikeKey, stock, currentCandle[0], currentCandle[2], currentCandle[3], True)
                        if entryData is not None:
                            entryData.append(entry)
                        else:
                            entryData = []
                            entryData.append(entry)

                        strikeData['is_take_entry'] = False
                        strikeData['strgy_in_progress'] = True
                        print('----------------------------------')
                        print(f">> entry UB : {entry}")
                        print('----------------------------------')
                        RedisDB.setJson(key=strikeKey, data=strikeData)
                        RedisDB.setJson(key=entryKey, data=entryData)

    # EOF: Conditions to get entry
    ################################################################################


def rsi_me(df, period):
    print(f"--- df length : {len(df)} | {period}")
    # 4: close | 1: open
    # Step 1: Calculate EWA
    df['gain'] = (df[4] - df[1]).apply(lambda x: x if x > 0 else 0)
    df['loss'] = (df[4] - df[1]).apply(lambda x: -x if x < 0 else 0)

    # Step 2: Calculate EMA
    df['ema_gain'] = df['gain'].ewm(span=period, min_periods=period).mean()
    df['ema_loss'] = df['loss'].ewm(span=period, min_periods=period).mean()

    # Step 3: Calculate RS
    df['rs'] = df['ema_gain']/df['ema_loss']

    # Step 4: Calculate RSI
    df['rsi'] = 100 - (100 / (df['rs'] + 1))

    # print(df)

    return round(df.iloc[-1]['rsi'], 2)


def rsi_1(df: pd.DataFrame, period: int = 14, round_rsi: bool = True):
    delta = df[4].diff()

    up = delta.copy()
    up[up < 0] = 0
    up = pd.Series.ewm(up, alpha=1/period).mean()

    down = delta.copy()
    down[down > 0] = 0
    down *= -1
    down = pd.Series.ewm(down, alpha=1/period).mean()

    rsi = np.where(up == 0, 0, np.where(
        down == 0, 100, 100 - (100 / (1 + up / down))))

    return np.round(rsi, 2) if round_rsi else rsi


async def calculateEntry(setting, strikeKey, stock, time, high, low, upperBand):
    entry = high + 1.2
    sl = (high * 0.9) - 1.2
    target = high * 1.11

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
        "new_target": None,
        "sl": AppUtils.round2(sl),
        "tsl": AppUtils.round2(sl),
        "previous_candle": None,
        "profit_loss": 0,
        "is_entry": False,
        "is_exit": False,
        "is_tsl": False,
        "entry_price": None,
        "entry_at": None,
        "exit_at": None,
        "exit_price": None,
        "created_at": datetime.fromtimestamp(time),
        "status": 0,
    }

    return result

# EOF: Strategy 1
################################################################################


async def checkEntries(db, currentCandle, stock, setting, ema):
    try:
        timeFrame = int(setting['time_frame'].replace("M", ""))
        entryKey = f"{AppConstants.strategy_3}entry_{timeFrame}"
        entryData = RedisDB.getJson(key=entryKey)

        if entryData is not None:
            # profitLoss = 0.0
            cIndex = []

            for index, entry in enumerate(entryData):
                if int(entry['exchange_code']) == int(stock['exchange_code']) and entry['status'] == 0:
                    cIndex.append(index)

            if len(cIndex) > 0:
                for index in cIndex:
                    entry = entryData[index]
                    strikeKey = str(entry['strike_key'])
                    strikeData = RedisDB.getJson(key=strikeKey)

                    # ################################################################################################################
                    # # Condition : Confirmation Candel close below the Base Candel Low => Confirmation Candel Low = Trailing StopLoss.
                    # ################################################################################################################
                    # if entry['is_entry'] and entry['is_exit'] == False:
                    #     diff = float(entry['target']) - currentCandle[2]
                    #     if diff <= 5:
                    #         targetPoint = (25000 * 0.026) / \
                    #             float(entry['lot_size'])
                    #         entry['new_target'] = float(
                    #             entry['entry']) + targetPoint
                    # ################################################################################################################
                    # # ACTION :  CONDITION MEET TAKE ENTRY
                    # ################################################################################################################
                    # if entry['is_entry'] == False and entry['is_upper_band'] == False and currentCandle[2] >= float(entry['entry']):
                    #     entry['is_entry'] = True
                    #     entry['entry_at'] = currentCandle[0]
                    #     entry['entry_price'] = float(entry['entry'])
                    #     entry = await createEntry(db, entry)
                    #     await placeOrder(db, entry, setting, currentCandle[2])
                    ################################################################################################################
                    # ACTION :  REMOVE ENTRY IF CONDITION NOT MEET
                    ################################################################################################################
                    if entry['is_entry'] == False and entry['is_exit'] == False and strikeData['is_take_entry'] == False:
                        removeData = False
                        if entry['is_upper_band'] and float(entry['low']) < currentCandle[3]:
                            removeData = True
                            print('--------------------------')
                            if strikeData['status'] == "CE":
                                strikeData['status'] = "PE"
                                print(f"switch Over >> from CE -> PE")
                            else:
                                strikeData['status'] = "CE"
                                print(f"switch Over >> from PE -> CE")
                            print('--------------------------')
                        elif entry['is_upper_band'] == False and float(entry['high']) > currentCandle[2]:
                            removeData = True
                        if removeData:
                            entryData.pop(index)
                            strikeData['is_take_entry'] = True
                            strikeData['strgy_in_progress'] = False
                            removeKey = f"{AppConstants.strategy_3}removed_{timeFrame}"
                            removedData = RedisDB.getJson(key=removeKey)
                            if removedData is None:
                                removedData = []
                            removedData.append(entry)
                            RedisDB.setJson(key=removeKey, data=removedData)
                            RedisDB.setJson(key=strikeKey, data=strikeData)
                    # ################################################################################################################
                    # # ACTION :  CHECK TARGET
                    # ################################################################################################################
                    # elif entry['is_entry'] and entry['is_exit'] == False and currentCandle[2] >= float(entry['target']):
                    #     entry['status'] = 1
                    #     entry['is_exit'] = True
                    #     entry['exit_at'] = currentCandle[0]
                    #     entry['exit_price'] = float(entry['target'])
                    #     strikeData['is_take_entry'] = True
                    #     strikeData['strgy_in_progress'] = False
                    #     RedisDB.setJson(key=strikeKey, data=strikeData)

                    #     await updateEntry(db, entry)
                    #     await exitOrder(db, entry, currentCandle[2])
                    # ################################################################################################################
                    # # ACTION :  CHECK NEW TARGET
                    # ################################################################################################################
                    # elif entry['is_entry'] and entry['is_exit'] == False and entry['new_target'] is not None and currentCandle[2] < float(entry['new_target']):
                    #     entry['status'] = 2
                    #     entry['is_exit'] = True
                    #     entry['exit_at'] = currentCandle[0]
                    #     entry['exit_price'] = entry['new_target']
                    #     strikeData['is_take_entry'] = True
                    #     strikeData['strgy_in_progress'] = False
                    #     RedisDB.setJson(key=strikeKey, data=strikeData)

                    #     await updateEntry(db, entry)
                    #     await exitOrder(db, entry, currentCandle[2])
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
                        strikeData['strgy_in_progress'] = False

                        noOfEntry = [
                            x for x in entryData if x['symbol'] == stock['symbol']]

                        if noOfEntry is not None:
                            if len(noOfEntry) >= 2:
                                sortedData = sorted(noOfEntry, key=lambda k:
                                                    k['created_at'], reverse=True)
                                if (noOfEntry[-2:][0]['status'] == 3 or noOfEntry[-2:][0]['status'] == 4) and (noOfEntry[-2:][1]['status'] == 3 or noOfEntry[-2:][1]['status'] == 4):
                                    print('------------ TSL HIT  ----------')
                                    print(noOfEntry[-2:])
                                    print('------------ TSL HIT  ----------')
                                    strikeData['is_take_entry'] == False
                                else:
                                    strikeData['is_take_entry'] = True
                            else:
                                strikeData['is_take_entry'] = True

                        RedisDB.setJson(key=strikeKey, data=strikeData)

                        # Update entry in MongoDB
                        await updateEntry(db, entry)
                        await exitOrder(db, entry, currentCandle[2])
                    ################################################################################################################
                    # ACTION : CHECK SL
                    ################################################################################################################
                    elif entry['is_entry'] and entry['is_exit'] == False and currentCandle[3] <= float(entry['sl']):
                        entry['status'] = 3
                        entry['is_exit'] = True
                        entry['exit_at'] = currentCandle[0]
                        entry['exit_price'] = float(entry['sl'])
                        strikeData['strgy_in_progress'] = False
                        noOfEntry = [
                            x for x in entryData if x['symbol'] == stock['symbol']]

                        if noOfEntry is not None and len(noOfEntry) >= 2:
                            sortedData = sorted(noOfEntry, key=lambda k:
                                                k['created_at'], reverse=True)
                            if (noOfEntry[-2:][0]['status'] == 3 or noOfEntry[-2:][0]['status'] == 4) and (noOfEntry[-2:][1]['status'] == 3 or noOfEntry[-2:][1]['status'] == 4):
                                print('------------ SL HIT  ----------')
                                print(noOfEntry[-2:])
                                print('------------ SL HIT  ----------')
                                strikeData['is_take_entry'] == False
                            else:
                                strikeData['is_take_entry'] = True
                        else:
                            strikeData['is_take_entry'] = True

                        RedisDB.setJson(key=strikeKey, data=strikeData)

                        # Update entry in MongoDB
                        await updateEntry(db, entry)
                        await exitOrder(db, entry, currentCandle[2])

                    # ################################################################################################################
                    # # CONDITION : IF MARKET REACHES 3:14 CLOSE ALL THE OPENING TRADES
                    # ################################################################################################################
                    # elif entry['is_entry'] and entry['is_exit'] == False:
                    #     marketEndTime = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "1511")
                    #     # marketEndTime = await AppUtils.combineDateTime("06 Apr 23", "1514")
                    #     if currentCandle[0] > marketEndTime:
                    #         entryDate = datetime.fromtimestamp(entry['entry_at'])
                    #         eData = int(
                    #             (entryDate + timedelta(minutes=30)).timestamp())
                    #         if eData < AppUtils.getCurrentDateTimeStamp():
                    #             tDiff = abs(
                    #                 float(entry['target']) - currentCandle[2])
                    #             sDiff = abs(
                    #                 currentCandle[2] - float(entry['sl']))
                    #             tslDiff = abs(
                    #                 currentCandle[2] - float(entry['tsl']))
                    #             if tDiff < sDiff:
                    #                 entry['status'] = 1
                    #             elif sDiff < tslDiff:
                    #                 entry['status'] = 3
                    #             else:
                    #                 entry['status'] = 4
                    #             entry['is_exit'] = True
                    #             entry['exit_at'] = AppUtils.getCurrentDateTimeStamp()
                    #             entry['exit_price'] = currentCandle[2]
                    #             strikeData['is_take_entry'] = True
                    #             strikeData['strgy_in_progress'] = False
                    #             RedisDB.setJson(key=strikeKey, data=strikeData)

                    #             # Update entry in MongoDB
                    #             await updateEntry(db, entry)
                    #             await exitOrder(db, entry, currentCandle[2])
                    ################################################################################################################
                    # ACTION : CHECK AND GET TRAILING SL
                    ################################################################################################################
                    if entry['status'] == 0:
                        ################################################################################################################
                        # Condition For TSL 2: close below Low [ Base Candle ] : [ Confirmation Candle ]
                        ################################################################################################################
                        if entry['previous_candle'] is not None:
                            if currentCandle[4] < entry['previous_candle'][3]:
                                entry['tsl'] = str(currentCandle[3])
                        ################################################################################################################
                        # Condition For TSL 1: close below ema [ Base Candle ]
                        ################################################################################################################
                        if currentCandle[4] < ema:
                            entry['previous_candle'] = currentCandle
                        else:
                            entry['previous_candle'] = None

                    RedisDB.setJson(key=entryKey, data=entryData)

            #####################################################################################
            # After 2 continues SL we wait for 30 min to take next trade
            ####################################################################################
            noOfEntry = [
                x for x in entryData if x['symbol'] == stock['symbol']]

            if noOfEntry is not None and len(noOfEntry) >= 2:
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
                    if exitDate < currentCandle[0]:
                        print('-----------After  30 MIN -------------')
                        print(sortedData[0])
                        print('----------After  30 MIN --------------')
                        strikeKey = sortedData[0]['strike_key']
                        strikeData = RedisDB.getJson(key=strikeKey)
                        strikeData['is_take_entry'] = True
                        RedisDB.setJson(key=strikeKey, data=strikeData)

            # strikeKeys = []

            # for index, entry in enumerate(entryData):
            #     # if entry['symbol'] == stock['symbol'] and entry['is_exit']:
            #     if entry['strike_key'] is not strikeKeys:
            #         strikeKeys.append(entry['strike_key'])

            #     if entry['exit_price'] is not None:
            #         key = f"{AppConstants.candle}{entry['exchange_code']}_{timeFrame}"
            #         candleData = RedisDB.getJson(key=key)
            #         # currentCandle = candleData[AppConstants.count:][0]
            #         currentCandle = candleData[-1:][0]
            #         if entry['is_exit'] == False and entry['exchange_code'] == stock['exchange_code']:
            #             profitLoss += round(((currentCandle[2] -
            #                                 float(entry['entry_price'])) * int(entry['quantity'])), 2)
            #         elif entry['is_exit']:
            #             profitLoss += round(((float(entry['exit_price']) - float(
            #                 entry['entry_price'])) * int(entry['quantity'])), 2)

            # if profitLoss >= 900:
            #     stockKey = f"{AppConstants.strategy_3}stock"
            #     stockData = RedisDB.getJson(key=stockKey)
            #     for script in stockData:
            #         strikeKey = f"{AppConstants.strike}{script['exchange_code']}_{timeFrame}"
            #         strikeData = RedisDB.getJson(key=strikeKey)
            #         strikeData['trade_status'] = False
            #         RedisDB.setJson(key=strikeKey, data=strikeData)

            #     for index, entry in enumerate(entryData):
            #         ################################################################################################################
            #         # CONDITION : IF PROFIT REACHED STOP THE TRADE AND EXIT THE ORDER
            #         ################################################################################################################
            #         if entry['is_entry'] and entry['is_exit'] == False:
            #             key = f"{AppConstants.candle}{entry['exchange_code']}_{timeFrame}"
            #             candleData = RedisDB.getJson(key=key)
            #             # currentCandle = candleData[AppConstants.count:][0]
            #             currentCandle = candleData[-1:][0]

            #             tDiff = abs(
            #                 float(entry['target']) - currentCandle[2])
            #             sDiff = abs(
            #                 currentCandle[2] - float(entry['sl']))
            #             tslDiff = abs(
            #                 currentCandle[2] - float(entry['tsl']))

            #             if tDiff < sDiff:
            #                 entry['status'] = 1
            #             elif sDiff < tslDiff:
            #                 entry['status'] = 3
            #             else:
            #                 entry['status'] = 4

            #             entry['is_exit'] = True
            #             entry['exit_at'] = currentCandle[0]
            #             entry['exit_price'] = currentCandle[2]
            #             strikeData['is_take_entry'] = False
            #             strikeData['strgy_in_progress'] = False
            #             RedisDB.setJson(key=strikeKey, data=strikeData)

            #             # Update entry in MongoDB
            #             await updateEntry(db, entry)
            #             await exitOrder(db, entry, currentCandle[2])

    except Exception as ex:
        print(f"Error Check Entries: {ex}")


async def createEntry(db, entry):
    try:
        dbStrategy = AppDatabase.getName().strategy
        sId = str(ObjectId())
        entry['_id'] = sId
        await db[dbStrategy].insert_one(jsonable_encoder(entry))
        return entry
    except Exception as ex:
        print(f"Error Create Entry: {ex}")


async def updateEntry(db, entry):
    try:
        dbStrategy = AppDatabase.getName().strategy
        await db[dbStrategy].update_one({'_id': entry['_id']}, {'$set': jsonable_encoder(entry)})
        return entry
    except Exception as ex:
        print(f"Error Update Entry: {ex}")


async def placeOrder(db, entry, setting, ltp):
    try:
        dbUser = AppDatabase.getName().user
        dbAccount = AppDatabase.getName().account
        dbOrder = AppDatabase.getName().strategy_order

        fcmTokens = []
        async for user in db[dbUser].find({'is_live': True, 'is_subscribed': True}):
            async for account in db[dbAccount].find({'user_id': user['_id'], 'trade_status': True}):
                quantity = math.floor(account['margin'] / 25000)
                if quantity > 0:
                    orderId = "Xybyiyiaq7814"
                    orderLog = "Demo Order"
                    orderQnty = (entry['lot_size'] * quantity)
                    if account['client_id'] == "MADUA10-1":
                        jData = {
                            "uid": "MADUA10",
                            "actid": "",
                            "exch": "NSE",
                            "tsym": entry['stock_name'],
                            "qty": orderQnty,
                            "prc": ltp,
                            "prd": "M - NRML",
                            "trantype": "B",
                            "prctyp": "MKT",
                            "ret": "DAY"
                        }
                        params = f"jKey={account['access_token']}&jData={jData}"
                        response = requests.post(
                            ApiTerminal.flatTradeApi['placeOrder'], params=params)

                        if response.status_code == 200:
                            data = response.json()
                            if data['stat'] == "Ok":
                                orderId = data['result']
                                orderLog = "Order placed successfully"
                            else:
                                orderLog = "Failed to placed order successfully"

                    order = {
                        "_id": str(ObjectId()),
                        "strategy_setting_id": setting['_id'],
                        "user_id": user['_id'],
                        "strategy_id": entry['_id'],
                        "client_id": account['client_id'],
                        "trading_platform": account['broker'],
                        "order_id": orderId,
                        "order_type": entry['order_type'],
                        "quantity": orderQnty,
                        "price": ltp,
                        "order_time": AppUtils.getCurrentDateTime(),
                        "order_log": orderLog,
                        "status": entry['status'], }
                    await db[dbOrder].insert_one(jsonable_encoder(order))

                    if user['f_token'] is not None:
                        fcmTokens.append(user['f_token'])

        # if len(fcmTokens) > 0:
        #     notificationMsg = f"{entry['stock_name']} - {entry['order_type']} Order placed @{entry['entry']}"
        #     return AppUtils.sendPushNotification(
        #         fcm_token=fcmTokens,  message_title=AppConstants.appName, message_body=notificationMsg)
    except Exception as ex:
        print(f"Error Place Order: {ex}")


async def exitOrder(db, entry, ltp):
    try:
        dbUser = AppDatabase.getName().user
        dbAccount = AppDatabase.getName().account
        dbOrder = AppDatabase.getName().strategy_order

        fcmTokens = []
        async for order in db[dbOrder].find({'status': 0}):
            user = await db[dbUser].find_one({'_id': order['user_id']})
            account = await db[dbAccount].find_one({'user_id': order['user_id']})

            orderId = "Xybyiyiaq7814"
            orderLog = "Demo Order"
            orderQnty = order['quantity']

            if account['broker'] == AppUtils.getTradingPlatform().flatTrade:
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

       #  if len(fcmTokens) > 0:
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
        print(f"Error Exit Order: {ex}")


async def updateStrikePrice(db, stock, candleData):
    try:
        dbOption = AppDatabase.getName().model_option
        dbSetting = AppDatabase.getName().strategy_setting

        timeFrame = 0
        premium = 200

        setting = await db[dbSetting].find_one({'strategy_name': "strategy_3"})
        if setting['is_live']:
            timeFrame = int(setting['time_frame'].replace("M", ""))
            premium = int(setting['premium'])

            if candleData is not None:
                # currentCandle = candleData[AppConstants.count:][0]
                currentCandle = candleData[-1:][0]

                ################################################################################
                # NOTE:
                # candle format
                #  [0, 1, 2, 3, 4, 5]
                #  [epoch_time, open, high, low, close, volume]
                #  [1674618600,18159.4,18159.4,18143.4,18151.6,185500]
                ################################################################################

                # EOF: Get current candel
                ################################################################################
                # print(f"Strike Candle: {currentCandle}")
                ################################################################################
                # SOF: Find nearest strike price to get OTM | ATM | ITM

                if stock['symbol'] == "BANKNIFTY":
                    minPrice = 150
                    maxPrice = 500
                else:
                    minPrice = 125
                    maxPrice = 300

                if currentCandle[2] < minPrice or currentCandle[2] > maxPrice:
                    stockKey = f"{AppConstants.strategy_3}stock"
                    stockData = RedisDB.getJson(key=stockKey)

                    for script in stockData:
                        # print(f"{script['symbol'].replace('50','')} == {stock['symbol']}")
                        strikeKey = f"{AppConstants.strike}{script['exchange_code']}_{timeFrame}"
                        strikeData = RedisDB.getJson(key=strikeKey)

                        if strikeData['OTM'] == int(stock['strike_price']) or strikeData['ITM'] == int(stock['strike_price']):
                            print(
                                f"{strikeData['OTM']} or {strikeData['ITM']} == {int(stock['strike_price'])}")

                            print(f"update strike candle : {currentCandle}")

                            if stock['symbol'] == "BANKNIFTY":
                                minPrice = 150
                                maxPrice = 500
                            else:
                                minPrice = 125
                                maxPrice = 300

                            currentSKP = None
                            currentSKPStock = None

                            for sData in strikeData['stocks']:
                                if sData['option_type'] == stock['option_type']:
                                    key = f"{AppConstants.candle}{sData['exchange_code']}_{timeFrame}"
                                    skCandleData = RedisDB.getJson(key=key)
                                    if skCandleData is not None:
                                        # firstCandle = skCandleData[AppConstants.count:][0]
                                        firstCandle = skCandleData[-1:][0]
                                        if currentSKPStock is not None:
                                            if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                if firstCandle[2] < currentSKPStock[2]:
                                                    currentSKP = sData['strike_price']
                                                    currentSKPStock = firstCandle
                                        else:
                                            if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                currentSKP = sData['strike_price']
                                                currentSKPStock = firstCandle

                            print(f"{currentSKP} : {stock['option_type']}")
                            if currentSKP is not None:
                                if stock['option_type'] == "PE":
                                    strikeData['OTM'] = currentSKP
                                else:
                                    strikeData['ITM'] = currentSKP

                                RedisDB.setJson(
                                    key=strikeKey, data=strikeData)
                            else:
                                if script['symbol'].replace("50", "") == stock['symbol']:
                                    key = f"{AppConstants.candle}{script['exchange_code']}_{timeFrame}"
                                    candleData = RedisDB.getJson(key=key)

                                if candleData is not None:
                                    hasCandle = [
                                        x for x in candleData if x[0] == currentCandle[0]]

                                if hasCandle is None or len(hasCandle) <= 0:
                                    # print(f">> Update Strike Prive stock: {script['stock_name']}")

                                    symbol = f"{script['exchange']}:{script['stock_name']}"

                                    await getCandelData(symbol=symbol, timeFrame=timeFrame,
                                                        exchangeCode=script['exchange_code'], present=True)

                                    key = f"{AppConstants.candle}{script['exchange_code']}_{timeFrame}"
                                    candleData = RedisDB.getJson(key=key)

                                if candleData is not None:
                                    firstCandle = [
                                        x for x in candleData if x[0] == currentCandle[0]]

                                    # print(f"FCandle : {firstCandle}")

                                    if firstCandle is not None and len(firstCandle) > 0:
                                        optionList = []
                                        findSymbol = stock['symbol'].replace(
                                            "50", "")
                                        async for option in db[dbOption].find({'symbol': findSymbol}):
                                            optionList.append(
                                                option['strike_price'])

                                        if optionList is not None:
                                            # print(f"premium: {premium}")
                                            ATM = min(optionList, key=lambda x: abs(
                                                x-firstCandle[0][4]))
                                            OTM = ATM + premium
                                            ITM = ATM - premium

                                            # print(f">> OTM : {OTM} | ATM : {ATM} | ITM : {ITM}")

                                            # Get Previous day market data
                                            # Get Script Expiry Date
                                            expiry_date = await AppUtils.getExpiryDate()

                                            # ITMPutStock = await db[dbOption].find_one({'expiry_date': expiry_date, 'strike_price': OTM, 'option_type': "PE"})
                                            newStocks = []
                                            noOTMStock = False
                                            noITMStock = False
                                            for sData in strikeData['stocks']:
                                                if sData['strike_price'] == OTM:
                                                    noOTMStock = True
                                                if sData['strike_price'] == ITM:
                                                    noITMStock = True

                                            if noOTMStock == False and stock['option_type'] == "PE":
                                                newStocks.extend(
                                                    strikeData['stocks'])
                                                async for OTMStock in db[dbOption].find({'expiry_date': expiry_date, 'strike_price': OTM, 'option_type': "PE"}):
                                                    TMSymbol = f"{OTMStock['exchange']}:{OTMStock['stock_name']}"
                                                    OTMStock['is_upper_band_break'] = False
                                                    OTMStock['is_lower_band_break'] = False
                                                    OTMStock['previous_candle'] = None
                                                    OTMStock['confirmation_candle'] = None
                                                    OTMStock['band_timing'] = None

                                                    newStocks.append(OTMStock)
                                                    strikeData['OTM'] = OTM
                                                    strikeData['stocks'] = newStocks

                                                    await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                                        exchangeCode=OTMStock['exchange_code'],  present=False)

                                            if noITMStock == False and stock['option_type'] == "CE":
                                                newStocks.extend(
                                                    strikeData['stocks'])
                                                async for ITMStock in db[dbOption].find({'expiry_date': expiry_date, 'strike_price': ITM, 'option_type': "CE"}):
                                                    TMSymbol = f"{ITMStock['exchange']}:{ITMStock['stock_name']}"
                                                    ITMStock['is_upper_band_break'] = False
                                                    ITMStock['is_lower_band_break'] = False
                                                    ITMStock['previous_candle'] = None
                                                    ITMStock['confirmation_candle'] = None
                                                    ITMStock['band_timing'] = None

                                                    newStocks.append(ITMStock)
                                                    strikeData['ITM'] = ITM
                                                    strikeData['stocks'] = newStocks

                                                    await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                                        exchangeCode=ITMStock['exchange_code'],  present=False)

                                            RedisDB.setJson(
                                                key=strikeKey, data=strikeData)

                                        # EOF: Find nearest strike price to get OTM | ATM | ITM
                                        ################################################################################

        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy is turned off.")
    except Exception as ex:
        # print(f">> Error: {ex}")
        # log.error(f"{ex}")
        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, str(ex))


async def strategy_3_back_test():
    try:
        db = await AppUtils.openDb()
        dbFuture = AppDatabase.getName().model_future
        dbOption = AppDatabase.getName().model_option
        dbSetting = AppDatabase.getName().strategy_setting

        timeFrame = 0
        premium = 200
        setting = await db[dbSetting].find_one({'strategy_name': "strategy_3"})
        if setting['is_live']:
            timeFrame = int(setting['time_frame'].replace("M", ""))
            premium = int(setting['premium'])

            # entryKey = f"{AppConstants.strategy_3}entry_{timeFrame}"
            # entryData = RedisDB.getJson(key=entryKey)
            # #print('---------------------------------------------------------------------')
            # #print(entryData)
            # #print('---------------------------------------------------------------------')

            ###############################################################################
            # SOF: Get First (5 Min) candel

            startTime = "915"

            marketOpenTime = await AppUtils.combineDateTime("13 Apr 23", startTime)

            stocks = []
            selectedStocks = []

            async for stock in db[dbFuture].find({'is_subscribed': True}):
                stock['setting'] = setting
                stockKey = f"{AppConstants.strategy_3}stock"
                stockData = RedisDB.getJson(key=stockKey)
                stocks.append(stock)
                if stockData is not None:
                    stockData.append(stock)
                else:
                    stockData = []
                    stockData.append(stock)
                RedisDB.setJson(key=stockKey, data=stockData)

            hasStockData = False
            for stock in stocks:
                # print(f">> stock: {stock['stock_name']}")

                symbol = f"{stock['exchange']}:{stock['stock_name']}"

                await getCandelData(symbol=symbol, timeFrame=timeFrame,
                                    exchangeCode=stock['exchange_code'], endTime="1530", present=True)

                key = f"{AppConstants.candle}{stock['exchange_code']}_{timeFrame}"
                candleData = RedisDB.getJson(key=key)

                if candleData is not None:
                    firstCandle = [
                        x for x in candleData if x[0] == marketOpenTime]
                    ################################################################################
                    # NOTE:
                    # candle format
                    #  [0, 1, 2, 3, 4, 5]
                    #  [epoch_time, open, high, low, close, volume]
                    #  [1674618600,18159.4,18159.4,18143.4,18151.6,185500]
                    ################################################################################

                    # EOF: Get First timeFrame candel
                    ################################################################################
                    if firstCandle is not None and len(firstCandle) > 0:
                        # print(f"FCandle: {firstCandle}")
                        ################################################################################
                        # SOF: Find nearest strike price to get OTM | ATM | ITM
                        strikeKey = f"{AppConstants.strike}{stock['exchange_code']}_{timeFrame}"
                        strikeData = RedisDB.getJson(key=strikeKey)

                        levelKey = f"{AppConstants.candle}level_{stock['exchange_code']}_15"
                        levelData = RedisDB.getJson(key=levelKey)

                        if strikeData is None:
                            optionList = []
                            findSymbol = stock['symbol'].replace("50", "")
                            async for option in db[dbOption].find({'symbol': findSymbol}):
                                optionList.append(option['strike_price'])

                            if optionList is not None:
                                # print(f"premium: {premium}")
                                # #print(f"premium: {optionList}")
                                ATM = min(optionList, key=lambda x: abs(
                                    x-firstCandle[0][4]))
                                OTM = int(ATM + premium)
                                ITM = int(ATM - premium)

                                # print(f">> OTM : {OTM} | ATM : {ATM} | ITM : {ITM}")

                                # Get Previous day market data
                                # Get Script Expiry Date
                                expiry_date = await AppUtils.getExpiryDate()

                                if stock['symbol'] == "NIFTY50":
                                    premiumPrice = premium / 2
                                else:
                                    premiumPrice = premium

                                OTMPremimums = [
                                    # OTM + (premiumPrice*3),
                                    # OTM + (premiumPrice*2),
                                    # OTM + (premiumPrice*1),
                                    OTM,
                                    # OTM - (premiumPrice*1),
                                    # OTM - (premiumPrice*2),
                                    # OTM - (premiumPrice*3),
                                ]

                                ITMPremimums = [
                                    # ITM + (premiumPrice*3),
                                    # ITM + (premiumPrice*2),
                                    # ITM + (premiumPrice*1),
                                    ITM,
                                    # ITM - (premiumPrice*1),
                                    # ITM - (premiumPrice*2),
                                    # ITM - (premiumPrice*3),
                                ]

                                if stock['symbol'] == "BANKNIFTY":
                                    minPrice = 200
                                    maxPrice = 300
                                else:
                                    minPrice = 150
                                    maxPrice = 200

                                stocks = []
                                currentOTM = None
                                currentOTMStock = None
                                currentITM = None
                                currentITMStock = None

                                for sPrice in OTMPremimums:
                                    async for OTMStock in db[dbOption].find({'expiry_date': expiry_date, 'strike_price': sPrice, 'option_type': "PE"}):
                                        TMSymbol = f"{OTMStock['exchange']}:{OTMStock['stock_name']}"
                                        OTMStock['is_upper_band_break'] = False
                                        OTMStock['is_lower_band_break'] = False
                                        OTMStock['previous_candle'] = None
                                        OTMStock['confirmation_candle'] = None
                                        OTMStock['band_timing'] = None

                                        stocks.append(OTMStock)
                                        selectedStocks.extend(OTMStock)

                                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                            exchangeCode=OTMStock['exchange_code'],  present=False)

                                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                            exchangeCode=OTMStock['exchange_code'],  present=True)

                                        key = f"{AppConstants.candle}{OTMStock['exchange_code']}_{timeFrame}"
                                        candleData = RedisDB.getJson(key=key)

                                        if candleData is not None:
                                            firstCandle = [
                                                x for x in candleData if x[0] == marketOpenTime]

                                            if firstCandle is not None:
                                                firstCandle = firstCandle[0]

                                                if currentOTMStock is not None:
                                                    if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                        if firstCandle[2] < currentOTMStock[2]:
                                                            currentOTM = sPrice
                                                            currentOTMStock = firstCandle
                                                else:
                                                    if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                        currentOTM = sPrice
                                                        currentOTMStock = firstCandle

                                for sPrice in ITMPremimums:
                                    async for ITMStock in db[dbOption].find({'expiry_date': expiry_date, 'strike_price': sPrice, 'option_type': "CE"}):
                                        TMSymbol = f"{ITMStock['exchange']}:{ITMStock['stock_name']}"
                                        ITMStock['is_upper_band_break'] = False
                                        ITMStock['is_lower_band_break'] = False
                                        ITMStock['previous_candle'] = None
                                        ITMStock['confirmation_candle'] = None
                                        ITMStock['band_timing'] = None

                                        stocks.append(ITMStock)
                                        selectedStocks.extend(ITMStock)

                                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                            exchangeCode=ITMStock['exchange_code'],  present=False)

                                        await getCandelData(symbol=TMSymbol, timeFrame=timeFrame,
                                                            exchangeCode=ITMStock['exchange_code'],  present=True)

                                        key = f"{AppConstants.candle}{ITMStock['exchange_code']}_{timeFrame}"
                                        candleData = RedisDB.getJson(key=key)

                                        if candleData is not None:
                                            firstCandle = [
                                                x for x in candleData if x[0] == marketOpenTime]

                                            if firstCandle is not None:
                                                firstCandle = firstCandle[0]

                                                if currentITMStock is not None:
                                                    if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                        if firstCandle[2] < currentITMStock[2]:
                                                            currentITM = sPrice
                                                            currentITMStock = firstCandle
                                                else:
                                                    if firstCandle[2] > minPrice and firstCandle[2] < maxPrice:
                                                        currentITM = sPrice
                                                        currentITMStock = firstCandle

                                if currentOTM is None:
                                    currentOTM = OTM

                                if currentITM is None:
                                    currentITM = ITM

                                strikeData = {
                                    "OTM": int(currentOTM),
                                    "ATM": int(ATM),
                                    "ITM": int(currentITM),
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

                                # print(strikeData)

                                RedisDB.setJson(key=strikeKey, data=strikeData)
                                hasStockData = True
                            # EOF: Find nearest strike price to get OTM | ATM | ITM
                            ################################################################################
                        else:
                            hasStockData = True

            if len(selectedStocks) > 0:
                RedisDB.setJson(key="ws_stocks", data=selectedStocks)

            if hasStockData:
                thread = Thread(target=asyncio.run, args=(startStrategy3BT(setting, timeFrame, startTime, False),),
                                daemon=True, name='strategy_3')
                thread.daemon = True
                thread.start()

        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy is turned off.")
    except Exception as ex:
        # print(f"Error: {ex}")
        # log.error(f"{ex}")
        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, str(ex))


async def startStrategy3BT(setting, timeFrame, startTime, fromCron):
    try:
        # while True:
        await checkAndStartTradeBT(setting, timeFrame, startTime)
        # time.sleep(2)
    except Exception as ex:
        print(f"Error BT Start: {ex}")


async def checkAndStartTradeBT(setting, timeFrame, startTime):
    try:
        db = await AppUtils.openDb(isAsync=True)
        dbFuture = AppDatabase.getName().model_future
        # For testing
        AppConstants.count += 1

        async for script in db[dbFuture].find({'is_subscribed': True}):
            strikeKey = f"{AppConstants.strike}{script['exchange_code']}_{timeFrame}"
            strikeData = RedisDB.getJson(key=strikeKey)

            if strikeData['trade_status']:

                # if strikeData['is_high_low_break'] == False:
                #     ##################################################################################
                #     # Get Candle Data from Api and store it on Redis
                #     symbol = f"{script['exchange']}:{script['stock_name']}"
                #     await getCandelData(symbol=symbol, timeFrame=timeFrame,
                #                         exchangeCode=script['exchange_code'], present=True)

                #     key = f"{AppConstants.candle}{script['exchange_code']}_{timeFrame}"
                #     candleData = RedisDB.getJson(key=key)

                #     if candleData is None:
                #         symbol = f"{script['exchange']}:{script['stock_name']}"
                #         await getCandelData(symbol=symbol, timeFrame=timeFrame,
                #                             exchangeCode=script['exchange_code'], present=True)

                #         # Get Candle Data from Redis
                #         key = f"{AppConstants.candle}{script['exchange_code']}_{timeFrame}"
                #         candleData = RedisDB.getJson(key=key)

                #     if candleData is not None:
                #         currentCandle = candleData[AppConstants.count:][0]
                #         print(
                #             f"checking : {currentCandle[2]} >= {strikeData['high_level']} || {currentCandle[3]}<= {strikeData['low_level']}")
                #         #########################################################################################################################################
                #         # Condition : IF CANDLE BREAKS HIGH OR LOW TAKE ENTRY
                #         #########################################################################################################################################
                #         if currentCandle[2] >= strikeData['high_level'] and currentCandle[3] >= strikeData['high_level']:
                #             # print(f">> Hign Break | {currentCandle}")
                #             strikeData['is_high_low_break'] = True
                #             if strikeData['strgy_in_progress'] == False:
                #                 strikeData['is_take_entry'] = True
                #             strikeData['is_close_entry'] = False
                #             strikeData['status'] = "PE"
                #             print(f"high break >> {strikeData['status']}")
                #             RedisDB.setJson(
                #                 key=strikeKey, data=strikeData)

                #         elif currentCandle[2] <= strikeData['low_level'] and currentCandle[3] <= strikeData['low_level']:
                #             # print(f">> Low Break | {currentCandle}")
                #             strikeData['is_high_low_break'] = True
                #             if strikeData['strgy_in_progress'] == False:
                #                 strikeData['is_take_entry'] = True
                #             strikeData['is_close_entry'] = False
                #             strikeData['status'] = "CE"
                #             print(f"low break >> {strikeData['status']}")
                #             RedisDB.setJson(
                #                 key=strikeKey, data=strikeData)

                #         elif currentCandle[2] >= strikeData['high_level'] and currentCandle[3] <= strikeData['high_level']:
                #             strikeData['is_high_low_break'] = True
                #             if strikeData['strgy_in_progress'] == False:
                #                 strikeData['is_take_entry'] = True
                #             strikeData['is_close_entry'] = False
                #             strikeData['status'] = "CE"
                #             print(f"low break >> {strikeData['status']}")
                #             RedisDB.setJson(
                #                 key=strikeKey, data=strikeData)

                #         elif currentCandle[2] >= strikeData['low_level'] and currentCandle[3] <= strikeData['low_level']:
                #             strikeData['is_high_low_break'] = True
                #             if strikeData['strgy_in_progress'] == False:
                #                 strikeData['is_take_entry'] = True
                #             strikeData['is_close_entry'] = False
                #             strikeData['status'] = "PE"
                #             print(f"high break >> {strikeData['status']}")
                #             RedisDB.setJson(
                #                 key=strikeKey, data=strikeData)

                for index, stock in enumerate(strikeData['stocks']):
                    strikeData = RedisDB.getJson(key=strikeKey)
                    ##################################################################################
                    # Get Candle Data from Redis
                    key = f"{AppConstants.candle}{stock['exchange_code']}_{timeFrame}"
                    candleData = RedisDB.getJson(key=key)

                    if candleData is None:
                        # Get Candle Data from Api and store it on Redis
                        symbol = f"{stock['exchange']}:{stock['stock_name']}"
                        await getCandelData(symbol=symbol, timeFrame=timeFrame,
                                            exchangeCode=stock['exchange_code'], present=True)

                        # Get Candle Data from Redis
                        key = f"{AppConstants.candle}{stock['exchange_code']}_{timeFrame}"
                        candleData = RedisDB.getJson(key=key)

                    if candleData is not None:
                        currentCandle = candleData[AppConstants.count:][0]

                        ################################################################################
                        # Get Historical Data From Redis
                        historyKey = f"{AppConstants.candle}historical_{stock['exchange_code']}_{timeFrame}"
                        previousDayData: list = RedisDB.getJson(
                            key=historyKey)
                        if previousDayData is None:
                            previousDayData = []
                        previousDayData.extend(
                            candleData[:(AppConstants.count)])

                        print('------------------------------')
                        print(previousDayData[-1:])

                        df = pd.DataFrame(previousDayData[-15:])
                        rsi_14 = rsi_1(df, period=14)

                        df = pd.DataFrame(previousDayData[-51:])
                        rsi_50 = rsi_1(df, period=50)

                        print(f"{stock['stock_name']} : RSI 14 : {rsi_14}")
                        print(f"{stock['stock_name']} : RSI 50 : {rsi_50}")

                        # bb = bollinger_bands(bbData)
                        # bb = bb.iloc[-1].tolist()
                        # upperBand = bb[7]
                        # lowerBand = bb[8]
                        # print(upperBand)
                        # print(lowerBand)

                        ################################################################################
                        # print(f">> : {stock['stock_name']} : EMA {cEMA}")
                        # if strikeData['OTM'] == int(stock['strike_price']) or strikeData['ITM'] == int(stock['strike_price']):
                        #     await checkEntries(db, currentCandle, stock, setting, cEMA)
                        #     strikeData = RedisDB.getJson(key=strikeKey)
                        #     # strikeData = await checkChangeFromCallPut(index, strikeKey, strikeData, currentCandle, df, cEMA)
                        # await checkConditionAndGetEntry(
                        #     timeFrame, stock, setting, strikeKey, strikeData, currentCandle, bbData, cEMA)

                        # if strikeData['is_take_entry']:
                        #     await updateStrikePrice(db, stock, candleData)

    except Exception as ex:
        print(f"Error BT: {ex}")


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#  TODO:
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
#     margin 500000
    # utilze  40 % of margin
    # lot_size = 50 / 25
    #  no_of_lots = (utilze / entry_price) / lot_size
    #  round of no_of_lots if the decimal is above 80 pise round up to next value otherwise before the decimal value.
    #  quantity = lot_size * no_of_lots
#
#  Above 900 stop trade. - done
#  Websocket stop auto strat it.
#
