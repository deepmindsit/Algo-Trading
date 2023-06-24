from typing import List, Text
from fastapi import HTTPException, status, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from models.account_model import AccountModel, AuthCodeModel, UpdateAccountModel, returnResponseModel
from models.user_model import UserModel
from schemas.account_schema import AccountModelList
from utils.app_database import AppDatabase
from utils.app_utils import ApiCalls, AppUtils, Requests
from datetime import date, datetime

import json
import requests
import hashlib


async def bulkInsert(request: List[AccountModel], user: UserModel):
    db = await AppUtils.openDb()
    dbName = AppDatabase.getName().account
    returnResponse = []
    for account in request:
        response = returnResponseModel(
            status=False,
            message=""
        )
        account.user_id = user['_id']
        if await db[dbName].find_one({'client_id': account.client_id}) is None:
            db[dbName].insert_one(jsonable_encoder(account))
            response.status = True
            response.message = f"{account.client_id} : added successfully"
            returnResponse.append(response)
        else:
            response.message = f"{account.client_id} : already added"
            returnResponse.append(response)

    return returnResponse


async def create(request: AccountModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbName = AppDatabase.getName().account
        if request.user_id is not None:
            query = {'_id': request.user_id}
        else:
            query = {'app_id': requestedUser}
        user = await db[dbUser].find_one(query)
        if user is not None:
            request.user_id = user['_id']
            if await db[dbName].find_one({'client_id': request.client_id, 'user_id': request.user_id}) is None:
                await db[dbName].insert_one(jsonable_encoder(request))
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"{request.client_id} : added successfully")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, f"{request.client_id} : already added")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "User not found.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def update(id: str, request: UpdateAccountModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().account

        account = await db[dbName].find_one({'_id': id})
        if account is not None:
            await db[dbName].update_one({'_id': id}, {'$set': jsonable_encoder(request)})
            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"{account['client_id']} updated successfully")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Account not found")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def delete(id: str, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().account

        if await db[dbName].find_one({'_id': id}) is not None:
            await db[dbName].delete_one({'_id': id})
            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Account deleted successfully")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Account not found")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def list(user_id: str, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().account
        dbUser = AppDatabase.getName().user

        if user_id is not None:
            query = {'user_id': user_id}
        else:
            user = await db[dbUser].find_one({'app_id': requestedUser})
            query = {'user_id': user['_id']}

        accounts = []
        async for account in db[dbName].find(query):
            accounts.append(account)
        if len(accounts) <= 0:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Accounts not exists")
        else:
            return AppUtils.responseWithData(True, status.HTTP_200_OK, "Acconts fetched successsfully", AccountModelList(accounts))

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def resetToken(requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().account
        dbUser = AppDatabase.getName().user

        adminUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role']:
            # async for account in db[dbName].find():
            updateData = {
                "access_token": None,
                "refresh_token": None,
                "token_generated_at": None,
            }

            # "trade_status": False, # Todo: Need to add this on final setup

            await db[dbName].update_many({}, {'$set': jsonable_encoder(updateData)})

            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Token resetted successsfully")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission denied")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def updateStatus(liveStatus: int, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbAccount = AppDatabase.getName().account
        dbUser = AppDatabase.getName().user

        adminUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role']:
            if liveStatus == 1:
                message = "Live trade enabled successfully"
                updateData = {
                    "trade_status": True,
                    "paper_trade": False,
                }
            else:
                message = "Paper trade enabled successfully"
                updateData = {
                    "trade_status": False,
                    "paper_trade": True,
                }

            await db[dbAccount].update_many({}, {'$set': jsonable_encoder(updateData)})

            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, message)
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission denied")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def authCode(authCode: AuthCodeModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbName = AppDatabase.getName().account

        if authCode.user_id is not None:
            user = await db[dbUser].find_one({'_id': authCode.user_id})
        else:
            user = await db[dbUser].find_one({'app_id': requestedUser})

        if user is not None:
            account = await db[dbName].find_one({'client_id': authCode.client_id, 'user_id': user['_id']})
            if account is not None:
                if account['broker'] == AppUtils.getTradingPlatform().fyers:
                    header = {"Content-Type": "application/json"}
                    url = "https://api.fyers.in/api/v2/validate-authcode"
                    apiKey = f"{account['api_key']}:{account['api_secret']}"
                    apiKeyHash = hashlib.sha256(
                        apiKey.encode('utf-8')).hexdigest()
                    data = {"grant_type": "authorization_code", "appIdHash": apiKeyHash,
                            "code": authCode.auth_code}

                    response = requests.post(
                        url, headers=header, data=json.dumps(data))

                    if response.status_code == 200:
                        accessToken = response.json()['access_token']
                        refreshToken = response.json()['refresh_token']

                        if accessToken is not None:
                            updateData = {
                                "access_token": accessToken,
                                "refresh_token": refreshToken,
                                "token_generated_at": date.today()
                            }

                            await db[dbName].update_one({'_id': account['_id']}, {'$set': jsonable_encoder(updateData)})

                            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"{authCode.client_id} is acivated")
                    else:
                        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, f"{authCode.client_id} not acivated")

                elif account['broker'] == AppUtils.getTradingPlatform().flatTrade:
                    header = {"Content-Type": "application/json"}
                    url = "https://authapi.flattrade.in/trade/apitoken"
                    apiKey = account['api_key']
                    apiSecret = account['api_secret']
                    hashSecret = f"{apiKey}{authCode.auth_code}{apiSecret}"
                    appIdHash = hashlib.sha256(
                        hashSecret.encode('utf-8')).hexdigest()

                    data = {"api_key": apiKey, "request_code": authCode.auth_code,
                            "api_secret": appIdHash}

                    response = requests.post(
                        url, headers=header, data=json.dumps(data))

                    if response.status_code == 200:
                        accessToken = response.json()['token']

                        if accessToken is not None:
                            updateData = {
                                "access_token": accessToken,
                                "token_generated_at": date.today()
                            }

                            await db[dbName].update_one({'_id': account['_id']}, {'$set': jsonable_encoder(updateData)})

                            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"{authCode.client_id} is acivated")
                    else:
                        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, f"{authCode.client_id} not acivated")

            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Account not found")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "User not found")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)
