import asyncio
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
from utils.candle_utils import CandleUtils

from utils.strategy_utils import StrgyUtils


async def strategy_1():
    try:
        db = await AppUtils.openDb()
        dbFuture = AppDatabase.getName().model_future
        dbSetting = AppDatabase.getName().strategy_setting

        timeFrame = 0
        premium = 200
        beforeTime = AppUtils.getCurrentDateTimeStamp()

        setting = await db[dbSetting].find_one({'strategy_name': "SVSA"})
        if setting['is_live']:
            stocks = []
            selectedStocks = []

            timeFrame = int(setting['time_frame'].replace("M", ""))
            premium = int(setting['premium'])

            async for stock in db[dbFuture].find({'is_subscribed': True}):
                stock['setting'] = setting
                stockKey = f"{AppConstants.strategy_1}stock"
                stockData = RedisDB.getJson(key=stockKey)
                stocks.append(stock)
                if stockData is not None:
                    stockData.append(stock)
                else:
                    stockData = []
                    stockData.append(stock)
                RedisDB.setJson(key=stockKey, data=stockData)

            for stock in stocks:

                # symbol = f"{stock['exchange']}:{stock['stock_name']}"

                # await getCandelData(symbol=symbol, timeFrame=timeFrame,
                #                     exchangeCode=stock['exchange_code'], present=True)

                # key = f"{AppConstants.candle}{stock['exchange_code']}_{timeFrame}"
                # candleData = RedisDB.getJson(key=key)

                candleData = CandleUtils.getCandleData(
                    timeFrame, stock['exchange_code'], stock['fyToken'])

                if candleData is not None:
                    firstCandle = candleData[-1:]
                    ################################################################################
                    # NOTE:
                    # candle format
                    #  [0, 1, 2, 3, 4, 5]
                    #  [epoch_time, open, high, low, close, volume]
                    #  [1674618600,18159.4,18159.4,18143.4,18151.6,185500]
                    ################################################################################
                    print(f"firstCandle : {firstCandle}")

                    if firstCandle is not None and len(firstCandle) > 0:
                        ################################################################################
                        # SOF: Find nearest strike price to get OTM | ATM | ITM
                        strikeKey = f"{AppConstants.strike}{stock['exchange_code']}_{timeFrame}"
                        strikeData = RedisDB.getJson(key=strikeKey)

                        if strikeData is None:
                            levelKey = f"{AppConstants.candle}level_{stock['exchange_code']}_15"
                            strikeData = await StrgyUtils.getStrikePrice(
                                db, levelKey, stock, firstCandle, premium, timeFrame)
                            RedisDB.setJson(key=strikeKey, data=strikeData)

                        selectedStocks.extend(strikeData['stocks'])
                        # EOF: Find nearest strike price to get OTM | ATM | ITM
                        ################################################################################

            if len(selectedStocks) > 0:
                if AppConstants.websocket is not None:
                    stockData = RedisDB.getJson(key="ws_stocks")
                    if stockData is not None:
                        for stock in selectedStocks:
                            isSubscribed = False
                            for stockD in stockData:
                                if stockD['fyToken'] == stock['fyToken']:
                                    isSubscribed = True
                                    break
                            if isSubscribed == False:
                                stockData.append(stock)
                    else:
                        stockData = []
                        stockData.extend(selectedStocks)

                    await StrgyUtils.subscribeWs(AppConstants.websocket, stockData)
                    RedisDB.setJson(key="ws_stocks", data=stockData)
                else:
                    RedisDB.setJson(key="ws_stocks", data=selectedStocks)
                afterTime = AppUtils.getCurrentDateTimeStamp()
                timeDiff = abs(afterTime-beforeTime)
                sleepTime = abs((timeFrame*60) - timeDiff)
                ##########################################################
                # Start the strategy to take entries based on time frame
                ##########################################################
                thread = Thread(target=asyncio.run, args=(startStrategy1(setting, timeFrame, True, sleepTime),),
                                daemon=True, name='strategy_1')
                thread.daemon = True
                thread.start()

        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy is turned off.")
    except Exception as ex:
        AppConstants.log.error(f"s1: {ex}")
        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, str(ex))


async def startStrategy1(setting, timeFrame, fromCron, fromTime):
    try:
        while True:
            # print(f">> Executing Time : {datetime.now()}")
            beforeTime = AppUtils.getCurrentDateTimeStamp()
            await checkAndStartTrade(setting, timeFrame)
            if fromCron:
                fromCron = False
                sleepTime = abs(fromTime - 60)
            else:
                afterTime = AppUtils.getCurrentDateTimeStamp()
                timeDiff = abs(afterTime-beforeTime)
                sleepTime = abs((timeFrame*60) - timeDiff)
                # print("------------------------------------------------------------")
                # print(f"{sleepTime} | {timeDiff} = {beforeTime} - {afterTime}")
                # print("------------------------------------------------------------")
            time.sleep(sleepTime)
    except Exception as ex:
        AppConstants.log.error(f"s1: check | {ex}")


async def checkAndStartTrade(setting, timeFrame):
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
                if strikeData['status'] is None:
                    ##################################################################################
                    # Get Candle Data from Api and store it on Redis
                    # symbol = f"{script['exchange']}:{script['stock_name']}"
                    # await getCandelData(symbol=symbol, timeFrame=timeFrame,
                    #                     exchangeCode=script['exchange_code'], present=True)

                    # key = f"{AppConstants.candle}{script['exchange_code']}_{timeFrame}"
                    # candleData = RedisDB.getJson(key=key)

                    currentCandle = CandleUtils.getCurrentCandle(
                        timeFrame, script['fyToken'])
                    if currentCandle is not None and len(currentCandle) > 0:
                        # currentCandle = candleData[-1:][0]
                        # print(
                        #     f"checking : {currentCandle[2]} >= {strikeData['high_level']} || {currentCandle[3]}<= {strikeData['low_level']}")
                        await StrgyUtils.checkConditionToStartTrade(strikeKey, strikeData, currentCandle)

                for index, stock in enumerate(strikeData['stocks']):
                    ##################################################################################
                    # Get Candle Data from Api
                    # print(f">> stock: {stock['stock_name']}")

                    # symbol = f"{stock['exchange']}:{stock['stock_name']}"
                    # await getCandelData(symbol=symbol, timeFrame=timeFrame,
                    #                     exchangeCode=stock['exchange_code'], present=True)

                    # # Get Candle Data from Redis
                    # key = f"{AppConstants.candle}{stock['exchange_code']}_{timeFrame}"
                    # candleData = RedisDB.getJson(key=key)
                    currentCandle = CandleUtils.getCurrentCandle(
                        timeFrame, stock['fyToken'])
                    ##################################################################################

                    if currentCandle is not None and len(currentCandle) > 0:
                        # currentCandle = candleData[-1:][0]
                        # print(f"Candle: {currentCandle}")
                        candleData = CandleUtils.getCandleData(
                            timeFrame, stock['exchange_code'], stock['fyToken'])
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
                        if strikeData['is_high_low_break'] == False:
                            bb = bollinger_bands(df)
                            bb = bb.iloc[-1].tolist()
                            upperBand = bb[7]
                            lowerBand = bb[8]
                            if currentCandle[2] > upperBand:
                                strikeData['stocks'][index]['is_upper_band_break'] = True
                                strikeData['stocks'][index]['is_lower_band_break'] = False
                            if currentCandle[3] < lowerBand:
                                strikeData['stocks'][index]['is_upper_band_break'] = False
                                strikeData['stocks'][index]['is_lower_band_break'] = True

                            RedisDB.setJson(key=strikeKey, data=strikeData)
                            ################################################################################
                            # Calculate EMA
                            ema = calculate_ema(df[4][-20:], 3)
                            cEMA = round(ema[(len(ema)-3)], 2)
                            if strikeData['OTM'] == int(stock['strike_price']) or strikeData['ITM'] == int(stock['strike_price']):
                                await checkEntries(currentCandle, stock, setting, cEMA)
                        else:
                            ################################################################################
                            # Calculate EMA
                            ema = calculate_ema(df[4][-20:], 3)
                            cEMA = round(ema[(len(ema)-3)], 2)
                            # print(f">> : {stock['stock_name']} : EMA {cEMA}")
                            ################################################################################
                            if strikeData['OTM'] == int(stock['strike_price']) or strikeData['ITM'] == int(stock['strike_price']):
                                await checkEntries(currentCandle, stock, setting, cEMA)
                                strikeData = RedisDB.getJson(key=strikeKey)
                                strikeData = await checkChangeFromCallPut(index, strikeKey, strikeData, currentCandle, df, cEMA)
                                await checkConditionAndGetEntry(
                                    timeFrame, stock, setting, strikeKey, strikeData, currentCandle, df, cEMA)
                                strikeData = RedisDB.getJson(key=strikeKey)
                            if strikeData['is_take_entry'] and ((stock['option_type'] == "CE" and stock['strike_price'] == strikeData['ITM']) or (stock['option_type'] == "PE" and stock['strike_price'] == strikeData['OTM'])):
                                await StrgyUtils.updateStrikePrice(db, "SVSA", strikeKey, strikeData, stock, currentCandle)

            # time.sleep(1)
    except Exception as ex:
        AppConstants.log.error(f"s1: start | {ex}")


async def checkChangeFromCallPut(index, strikeKey, strikeData, currentCandle, df, cEMA):
    try:
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
            if (stock['option_type'] == "CE" and stock['strike_price'] == strikeData['ITM']) or (stock['option_type'] == "PE" and stock['strike_price'] == strikeData['OTM']) and currentCandle[3] < stock['confirmation_candle'][3]:
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
    except Exception as ex:
        AppConstants.log.error(f"s1: CE<->PE | {ex}")


async def checkConditionAndGetEntry(timeFrame, stock, setting, strikeKey, strikeData, currentCandle, df, cEMA):
    try:
        bb = bollinger_bands(df)
        bb = bb.iloc[-1].tolist()
        upperBand = bb[7]
        lowerBand = bb[8]

        sKey = f"{AppConstants.strategy_1}status_{timeFrame}"
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

        if status is not None:
            # print(f"status : {status}")
            previousCandle = status['previous_candle']
            previousEma = status['previous_ema']
            if stock['symbol'] == "BANKNIFTY":
                range = 30
            else:
                range = 20

            if status['status'] == "Below LB":
                ####################################################################################
                # Condition : COMES INSIDE THE LOWER BAND AND CLOSE ABOVE THE EMA3
                ####################################################################################
                # print(
                #     f">> Low -- {currentCandle[2]} > lb -- {lowerBand} and close -- {currentCandle[4]} > ema -- {cEMA}")
                if currentCandle[2] > lowerBand and currentCandle[4] > cEMA:
                    ################################################################################
                    # Condition : WHOSE RANGE MUST BE LESS THAN 30 POINTS
                    ################################################################################
                    # print(
                    #     f"IsEntry: {abs(currentCandle[2] - currentCandle[3]) < range} - {strikeData['is_take_entry']}")
                    if abs(currentCandle[2] - currentCandle[3]) <= range and strikeData['is_take_entry']:
                        getEntry = False
                        # marketEndTime = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "1500")
                        marketEndTime = await AppUtils.combineDateTime(AppConstants.currentDayDate, "1500")
                        entryKey = f"{AppConstants.strategy_1}entry_{timeFrame}"
                        entryData = RedisDB.getJson(key=entryKey)

                        if stock['symbol'] == "BANKNIFTY":
                            # print(
                            #     f"Bank Nifty: {currentCandle[2]} | 200 | 500")
                            getEntry = currentCandle[2] >= 200 and currentCandle[2] <= 500
                        else:
                            # print(f"Nifty: {currentCandle[2]} | 150 | 300")
                            getEntry = currentCandle[2] >= 150 and currentCandle[2] <= 300

                        # Take Entry
                        if currentCandle[0] < marketEndTime and getEntry and strikeData['status'] == stock['option_type']:
                            entry = await StrgyUtils.calculateEntry(setting, strikeKey, stock, currentCandle[0], currentCandle[2], 1.11)
                            if entryData is not None:
                                entryData.append(entry)
                            else:
                                entryData = []
                                entryData.append(entry)

                            strikeData['is_take_entry'] = False
                            strikeData['strgy_in_progress'] = True
                            # Save to redis
                            RedisDB.setJson(key=strikeKey, data=strikeData)
                            RedisDB.setJson(key=entryKey, data=entryData)
                            print('----------------------------------')
                            print(f">> entry LB : {entry}")
                            print('----------------------------------')

            elif status['status'] == "Above UB" and previousCandle is not None:
                ##################################################################################################
                # Condition : COMES INSIDE THE UPPER BAND AND CLOSE BELOW THE EMA AND THEN CLOSE ABOVE THE EMA3
                ##################################################################################################
                # print(
                #     f">> High previous -- {currentCandle[3]} > Up -- {upperBand} and p.close -- {previousCandle[3]} previousEma {previousEma} < c.close -- {currentCandle[4]} > ema -- {cEMA}")
                if (currentCandle[3] < upperBand and previousCandle[3] < previousEma and currentCandle[4] > cEMA) or (currentCandle[3] < upperBand and currentCandle[3] < cEMA and currentCandle[4] > cEMA):
                    ##############################################################################################
                    # Condition : WHOSE RANGE MUST BE LESS THAN 30 POINTS
                    ##############################################################################################
                    # print(
                    #     f"IsEntry: {abs((currentCandle[2] - currentCandle[3]) < range)} - {strikeData['is_take_entry']}")
                    if abs(currentCandle[2] - currentCandle[3]) <= range and strikeData['is_take_entry']:
                        getEntry = False
                        # marketEndTime = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "1529")
                        marketEndTime = await AppUtils.combineDateTime(AppConstants.currentDayDate, "1500")
                        entryKey = f"{AppConstants.strategy_1}entry_{timeFrame}"
                        entryData = RedisDB.getJson(key=entryKey)

                        if stock['symbol'] == "BANKNIFTY":
                            # print(
                            #     f"Bank Nifty: {currentCandle[2]} | 200 | 500")
                            getEntry = currentCandle[2] >= 200 and currentCandle[2] <= 500
                        else:
                            # print(f"Nifty: {currentCandle[2]} | 150 | 300")
                            getEntry = currentCandle[2] >= 150 and currentCandle[2] <= 300

                        # Take Entry
                        if currentCandle[0] < marketEndTime and getEntry and strikeData['status'] == stock['option_type']:
                            entry = await StrgyUtils.calculateEntry(setting, strikeKey, stock, currentCandle[0], currentCandle[2], 1.11)
                            if entryData is not None:
                                entryData.append(entry)
                            else:
                                entryData = []
                                entryData.append(entry)

                            strikeData['is_take_entry'] = False
                            strikeData['strgy_in_progress'] = True
                            RedisDB.setJson(key=strikeKey, data=strikeData)
                            RedisDB.setJson(key=entryKey, data=entryData)
                            print('--------------------------------------')
                            print(f">> entry UB : {entry}")
                            print('--------------------------------------')

            elif status['status'] == "Above UB" and previousCandle is None:
                # print(
                #     f">> High -- {currentCandle[3]} < {upperBand} and {currentCandle[3]} < {cEMA} and {currentCandle[4]} > {cEMA}")
                if currentCandle[3] < upperBand and currentCandle[3] < cEMA and currentCandle[4] > cEMA:
                    ##############################################################################################
                    # Condition : WHOSE RANGE MUST BE LESS THAN 30 POINTS
                    ##############################################################################################
                    # print(f"IsEntry: {abs((currentCandle[2] - currentCandle[3]) < range)} - {strikeData['is_take_entry']}")
                    if abs(currentCandle[2] - currentCandle[3]) <= range and strikeData['is_take_entry']:
                        getEntry = False
                        # marketEndTime = await AppUtils.combineDateTime(datetime.now().strftime("%d %b %y"), "1500")
                        marketEndTime = await AppUtils.combineDateTime(AppConstants.currentDayDate, "1500")
                        entryKey = f"{AppConstants.strategy_1}entry_{timeFrame}"
                        entryData = RedisDB.getJson(key=entryKey)

                        if stock['symbol'] == "BANKNIFTY":
                            # print(
                            #     f"Bank Nifty: {currentCandle[2]} | 200 | 500")
                            getEntry = currentCandle[2] >= 200 and currentCandle[2] <= 500
                        else:
                            # print(f"Nifty: {currentCandle[2]} | 150 | 300")
                            getEntry = currentCandle[2] >= 150 and currentCandle[2] <= 300

                        # Take Entry
                        if currentCandle[0] < marketEndTime and getEntry and strikeData['status'] == stock['option_type']:
                            entry = await StrgyUtils.calculateEntry(setting, strikeKey, stock, currentCandle[0], currentCandle[2], 1.11)
                            if entryData is not None:
                                entryData.append(entry)
                            else:
                                entryData = []
                                entryData.append(entry)

                            strikeData['is_take_entry'] = False
                            strikeData['strgy_in_progress'] = True
                            RedisDB.setJson(key=strikeKey, data=strikeData)
                            RedisDB.setJson(key=entryKey, data=entryData)
                            print('--------------------------------')
                            print(f">> entry UB : {entry}")
                            print('--------------------------------')

        if status is not None and currentCandle[3] < cEMA:
            status['previous_candle'] = currentCandle
            status['previous_ema'] = cEMA
            RedisDB.setJson(key=sKey, data=status)

    except Exception as ex:
        AppConstants.log.error(f"s1: check condition | {ex}")
    # EOF: Conditions to get entry
    ################################################################################


def calculate_ema(close, days, smoothing=2):
    ema = [sum(close[:days]) / days]
    for price in close[days:]:
        ema.append((price * (smoothing / (1 + days))) +
                   ema[-1] * (1 - (smoothing / (1 + days))))
    return ema


def bollinger_bands(df, std=2.1):
    # takes one column from dataframe
    df['B_MA'] = df[4].mean()
    sigma = np.std(df[4])
    df['UB'] = round((df['B_MA'] + (sigma * std)), 2)
    df['LB'] = round((df['B_MA'] - (sigma * std)), 2)
    return df

# EOF: Strategy 1
################################################################################


async def checkEntries(currentCandle, stock, setting, ema):
    try:
        timeFrame = int(setting['time_frame'].replace("M", ""))
        entryKey = f"{AppConstants.strategy_1}entry_{timeFrame}"
        entryData = RedisDB.getJson(key=entryKey)
        stockKey = f"{AppConstants.strategy_1}stock"

        # print(f"Entry Data : {len(entryData)}")

        if entryData is not None:
            cIndex = []
            hasData = []
            for index, entry in enumerate(entryData):
                # print(
                #     f"{int(entry['exchange_code'])} || {int(stock['exchange_code'])}")
                if int(entry['exchange_code']) == int(stock['exchange_code']) and entry['status'] == 0:
                    cIndex.append(index)
                # #############################################################$
                # Uncomment for backtest
                # elif int(entry['exchange_code']) == int(stock['exchange_code']) and entry['status'] != 0:
                #     hasData.append(index)

            if len(cIndex) > 0:
                for index in cIndex:
                    entry = entryData[index]
                    strikeKey = str(entry['strike_key'])
                    strikeData = RedisDB.getJson(key=strikeKey)
                    # #############################################################$
                    # Uncomment for backtest
                    # await StrgyUtils.checkEntryBT(timeFrame, 700, setting, stockKey, stock, entryKey, entryData, currentCandle)
                    ################################################################################################################
                    # ACTION :  REMOVE ENTRY IF CONDITION NOT MEET
                    ################################################################################################################
                    if entry['is_entry'] == False and entry['is_exit'] == False and strikeData['is_take_entry'] == False:
                        entryData.pop(index)
                        strikeData['is_take_entry'] = True
                        strikeData['strgy_in_progress'] = False
                        removeKey = f"{AppConstants.strategy_1}removed_{timeFrame}"
                        removedData = RedisDB.getJson(key=removeKey)
                        if removedData is None:
                            removedData = []
                        removedData.append(entry)
                        RedisDB.setJson(key=removeKey, data=removedData)
                        RedisDB.setJson(key=strikeKey, data=strikeData)
                    ################################################################################################################
                    # ACTION : CHECK AND GET TRAILING SL
                    ################################################################################################################
                    if entry['status'] == 0:
                        ################################################################################################################
                        # Condition For TSL 2: close below Low [ Base Candle ] : [ Confirmation Candle ]
                        ################################################################################################################
                        entry['tsl'] = entry['sl']
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
            # #############################################################$
            # Uncomment for backtest
            # elif len(hasData) > 0:
            #     await StrgyUtils.checkEntryBT(timeFrame, 700, setting, stockKey, stock, entryKey, entryData, currentCandle)

    except Exception as ex:
        AppConstants.log.error(f"s1: check entery | {ex}")


async def strategy_1_back_test():
    try:
        db = await AppUtils.openDb()
        dbFuture = AppDatabase.getName().model_future
        dbSetting = AppDatabase.getName().strategy_setting

        timeFrame = 0
        premium = 200
        setting = await db[dbSetting].find_one({'strategy_name': "SVSA"})
        if setting['is_live']:
            stocks = []
            selectedStocks = []
            startTime = "915"

            timeFrame = int(setting['time_frame'].replace("M", ""))
            premium = int(setting['premium'])

            marketOpenTime = await AppUtils.combineDateTime(AppConstants.currentDayDate, startTime)

            async for stock in db[dbFuture].find({'is_subscribed': True}):
                stock['setting'] = setting
                stockKey = f"{AppConstants.strategy_1}stock"
                stockData = RedisDB.getJson(key=stockKey)
                stocks.append(stock)
                if stockData is not None:
                    stockData.append(stock)
                else:
                    stockData = []
                    stockData.append(stock)
                RedisDB.setJson(key=stockKey, data=stockData)

            for stock in stocks:
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
                    if firstCandle is not None and len(firstCandle) > 0:
                        # print(f"FCandle: {firstCandle}")
                        ################################################################################
                        # SOF: Find nearest strike price to get OTM | ATM | ITM
                        strikeKey = f"{AppConstants.strike}{stock['exchange_code']}_{timeFrame}"
                        strikeData = RedisDB.getJson(key=strikeKey)

                        if strikeData is None:
                            levelKey = f"{AppConstants.candle}level_{stock['exchange_code']}_15"
                            strikeData = await StrgyUtils.getStrikePrice(
                                db, levelKey, stock, firstCandle, premium, timeFrame)
                            RedisDB.setJson(key=strikeKey, data=strikeData)

                        selectedStocks.extend(strikeData['stocks'])
                        # EOF: Find nearest strike price to get OTM | ATM | ITM
                        ################################################################################
            if len(selectedStocks) > 0:
                RedisDB.setJson(key="ws_stocks", data=selectedStocks)
                thread = Thread(target=asyncio.run, args=(startStrategy1BT(setting, timeFrame, startTime, False),),
                                daemon=True, name='strategy_1')
                thread.daemon = True
                thread.start()

        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Strategy is turned off.")
    except Exception as ex:
        # print(f"Error: {ex}")
        # log.error(f"{ex}")
        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, str(ex))


async def startStrategy1BT(setting, timeFrame, startTime, fromCron):
    try:
        while True:
            await checkAndStartTradeBT(setting, timeFrame, startTime)
            # time.sleep(2)
    except Exception as ex:
        print(f"Error: {ex}")


async def checkAndStartTradeBT(setting, timeFrame, startTime):
    try:
        # print(">> start new connection")
        # print(f">> Executing Time : {datetime.now()}")
        db = await AppUtils.openDb(isAsync=True)
        dbFuture = AppDatabase.getName().model_future
        # For testing
        AppConstants.count += 1
        # print("-----------------------------------------------------------------------")
        # print("CHECK AND HIGH LOW BREAKS")
        # print("-----------------------------------------------------------------------")
        async for script in db[dbFuture].find({'is_subscribed': True}):
            strikeKey = f"{AppConstants.strike}{script['exchange_code']}_{timeFrame}"
            strikeData = RedisDB.getJson(key=strikeKey)

            if strikeData['trade_status']:
                if strikeData['status'] is None:
                    ##################################################################################
                    # Get Candle Data from Api and store it on Redis
                    symbol = f"{script['exchange']}:{script['stock_name']}"
                    await getCandelData(symbol=symbol, timeFrame=timeFrame,
                                        exchangeCode=script['exchange_code'], present=True)

                    key = f"{AppConstants.candle}{script['exchange_code']}_{timeFrame}"
                    candleData = RedisDB.getJson(key=key)

                    if candleData is None:
                        symbol = f"{script['exchange']}:{script['stock_name']}"
                        await getCandelData(symbol=symbol, timeFrame=timeFrame,
                                            exchangeCode=script['exchange_code'], present=True)

                        # Get Candle Data from Redis
                        key = f"{AppConstants.candle}{script['exchange_code']}_{timeFrame}"
                        candleData = RedisDB.getJson(key=key)

                    if candleData is not None:
                        currentCandle = candleData[AppConstants.count:][0]
                        print(
                            f"checking : {currentCandle[2]} >= {strikeData['high_level']} || {currentCandle[3]}<= {strikeData['low_level']}")
                        await StrgyUtils.checkConditionToStartTrade(strikeKey, strikeData, currentCandle)

                for index, stock in enumerate(strikeData['stocks']):
                    strikeData = RedisDB.getJson(key=strikeKey)
                    ##################################################################################
                    # Get Candle Data from Api and store it on Redis
                    # print(f">> stock: {stock['stock_name']}")
                    # Check Candle Data from Redis as data
                    key = f"{AppConstants.candle}{stock['exchange_code']}_{timeFrame}"
                    candleData = RedisDB.getJson(key=key)

                    if candleData is None:
                        symbol = f"{stock['exchange']}:{stock['stock_name']}"
                        await getCandelData(symbol=symbol, timeFrame=timeFrame,
                                            exchangeCode=stock['exchange_code'], present=True)

                        # Get Candle Data from Redis
                        key = f"{AppConstants.candle}{stock['exchange_code']}_{timeFrame}"
                        candleData = RedisDB.getJson(key=key)

                    if candleData is not None:
                        currentCandle = candleData[AppConstants.count:][0]
                        # print(
                        #     f"Candle: {AppConstants.count} - {currentCandle}")

                        ################################################################################
                        # Get Historical Data From Redis
                        historyKey = f"{AppConstants.candle}historical_{stock['exchange_code']}_{timeFrame}"
                        previousDayData: list = RedisDB.getJson(
                            key=historyKey)
                        if previousDayData is None:
                            previousDayData = []
                        # previousDayData.extend(candleData)
                        ################################################################################
                        previousDayData.extend(
                            candleData[:(AppConstants.count+1)])

                        df = pd.DataFrame(previousDayData[-20:])

                        if strikeData['is_high_low_break'] == False:
                            bb = bollinger_bands(df)
                            bb = bb.iloc[-1].tolist()
                            upperBand = bb[7]
                            lowerBand = bb[8]
                            if currentCandle[2] > upperBand:
                                strikeData['stocks'][index]['is_upper_band_break'] = True
                                strikeData['stocks'][index]['is_lower_band_break'] = False
                            if currentCandle[3] < lowerBand:
                                strikeData['stocks'][index]['is_upper_band_break'] = False
                                strikeData['stocks'][index]['is_lower_band_break'] = True

                            RedisDB.setJson(key=strikeKey, data=strikeData)
                            ################################################################################
                            # Calculate EMA
                            ema = calculate_ema(df[4][-20:], 3)
                            # #print(df[4][-20:])
                            # #print(ema)
                            cEMA = round(ema[(len(ema)-3)], 2)
                            # print(f">> : {stock['stock_name']} : EMA {cEMA}")
                            if strikeData['OTM'] == int(stock['strike_price']) or strikeData['ITM'] == int(stock['strike_price']):
                                await checkEntries(currentCandle, stock, setting, cEMA)
                        else:
                            ################################################################################
                            # Calculate EMA
                            ema = calculate_ema(df[4][-20:], 3)
                            # #print(df[4][-20:])
                            # #print(ema)
                            cEMA = round(ema[(len(ema)-3)], 2)
                            # print(f">> : {stock['stock_name']} : EMA {cEMA}")
                            if strikeData['OTM'] == int(stock['strike_price']) or strikeData['ITM'] == int(stock['strike_price']):
                                await checkEntries(currentCandle, stock, setting, cEMA)
                                strikeData = RedisDB.getJson(key=strikeKey)
                                strikeData = await checkChangeFromCallPut(index, strikeKey, strikeData, currentCandle, df, cEMA)
                                await checkConditionAndGetEntry(
                                    timeFrame, stock, setting, strikeKey, strikeData, currentCandle, df, cEMA)
                                strikeData = RedisDB.getJson(key=strikeKey)
                            if strikeData['is_take_entry'] and ((stock['option_type'] == "CE" and stock['strike_price'] == strikeData['ITM']) or (stock['option_type'] == "PE" and stock['strike_price'] == strikeData['OTM'])):
                                await StrgyUtils.updateStrikePrice(db, "SVSA", strikeKey, strikeData, stock, currentCandle)

    except Exception as ex:
        print(f"Error: {ex}")


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
#  Above 900 stop trade. - completed
#  Websocket stop auto strat it. - completed
#

#  TODO: Check new traget issue - completed
