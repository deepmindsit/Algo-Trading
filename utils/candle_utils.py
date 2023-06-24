import json
import logging
import pandas as pd
import requests
from config.redis_db import RedisDB
from utils.api_terminal import ApiTerminal
from utils.app_constants import AppConstants
from utils.app_utils import AppUtils


class CandleUtils():

    async def getCurrentCandle(timeFrame, fyToken):
        try:
            header = {"Content-Type": "application/json"}

            jData = {
                "timeframe": timeFrame,
                "fytoken": fyToken,
                "api_token": "VGlja0RhdGEjMTIzIQ=="
            }

            print(
                f"url: {ApiTerminal.tickDataApi['getCurrentCandleData']} | {json.dumps(jData)}")
            response = requests.post(
                ApiTerminal.tickDataApi['getCurrentCandleData'], data=json.dumps(jData), headers=header, timeout=3)
            # print(f"Response: --- {response.json()}")
            if response.status_code == 200:
                candles = response.json()['data']
                return candles
            else:
                print(f">> Error : ${response.json()}")
                return []
        except Exception as ex:
            print(f"Candle Formation Error: {ex}")
            return None

    async def getCandleData(timeFrame, exchangeCode, fyToken):
        try:
            header = {"Content-Type": "application/json"}

            jData = {
                "timeframe": timeFrame,
                "fytoken": fyToken,
                "api_token": "VGlja0RhdGEjMTIzIQ=="
            }

            print(
                f"url: {ApiTerminal.tickDataApi['getCandleData']} | {json.dumps(jData)}")
            response = requests.post(
                ApiTerminal.tickDataApi['getCandleData'], data=json.dumps(jData), headers=header, timeout=3)
            # print(f"Response: --- {response.json()}")
            if response.status_code == 200:
                candles = response.json()['data']
                key = f"{AppConstants.candle}{exchangeCode}_{timeFrame}"
                RedisDB.setJson(key=key, data=candles)
                return candles
            else:
                print(f">> Error : ${response.json()}")
                return []
        except Exception as ex:
            print(f"Candle Formation Error: {ex}")
            return None
