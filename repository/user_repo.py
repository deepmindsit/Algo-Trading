import os
import base64
import datetime
import logging
import random
import uuid
import json
from config.auth import AuthHandler
from fastapi import Request, status, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi_mail import FastMail, MessageSchema
from templates import AppTemplates
from bson import ObjectId
from utils.app_constants import AppConstants
from utils.app_database import AppDatabase
from utils.hashing import Hash
from user_agents import parse
from utils.app_utils import AppUtils, Role
from models.user_model import *
from models.stocks_model import *
from schemas.user_schema import *


async def isUserExists(db, dbName: str, requestBody: LoginModel):
    if requestBody.email_id is not None and len(requestBody.email_id) > 0 and requestBody.mobile_no is not None and len(requestBody.mobile_no) > 0:
        return await db[dbName].find_one({'$or': [{'email_id': requestBody.email_id}, {'mobile_no': requestBody.mobile_no}]})
    elif requestBody.email_id is not None and len(requestBody.email_id) > 0:
        return await db[dbName].find_one({'email_id': requestBody.email_id})
    elif requestBody.mobile_no is not None and len(requestBody.mobile_no) > 0:
        return await db[dbName].find_one({'mobile_no': requestBody.mobile_no})


async def checkUserExists(requestBody: LoginModel):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().user

        user = await isUserExists(db=db, dbName=dbName, requestBody=requestBody)

        if user is not None:
            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "User exists.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Please register with us to continue.")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def login(requestBody: LoginModel, background_tasks: BackgroundTasks):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().user

        user = await isUserExists(db=db, dbName=dbName, requestBody=requestBody)

        if user is not None:
            if requestBody.email_id is not None:

                otp = random.randrange(000000, 999999, 6)

                bodyMessage = {
                    "userName": user['name'] + " ( " + user['app_id'] + " )",
                    "otp": otp,
                }

                message = MessageSchema(
                    subject="Reg: Verification mail",
                    recipients=[user['email_id']],
                    subtype='html',
                    template_body=json.loads(json.dumps(bodyMessage)),
                )

                updateValue = {'otp': otp,
                               'otp_time': AppUtils.getCurrentDateTime()}

                await db[dbName].update_one({'_id': user['_id']}, {'$set': updateValue})

                background_tasks.add_task(
                    AppUtils.sendEmail, message, "otp.html")

                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "OTP sent to the given email.")

            else:
                auth_handler = AuthHandler()
                login_token = uuid.uuid4()
                user['login_token'] = login_token
                user['referral_link'] = AppUtils.encodeValue(user['app_id'])
                user['token'] = auth_handler.encode_token(user['app_id'])

                updateValue = {'login_token': str(login_token),
                               'last_login': AppUtils.getCurrentDateTime()}

                await db[dbName].update_one({'_id': user['_id']}, {'$set': updateValue})

                return AppUtils.responseWithData(True, status.HTTP_200_OK, "User fetched successfully.", userModelLoginRes(user))
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Please register with us to continue.")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def register(requestBody: UserModel, background_tasks: BackgroundTasks):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().user

        auth_handler = AuthHandler()
        user = await isUserExists(db=db, dbName=dbName, requestBody=requestBody)
        if user is not None:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "You are already registred with us, Please login to continue.")
        else:
            # Create New User
            count = await db[dbName].count_documents({})
            if count is not None:
                count += 1
            else:
                count = 1
            requestBody.app_id = f"SV{count}"
            isIdExists = await db[dbName].find_one({'app_id': requestBody.app_id}) is not None
            if isIdExists:
                count += 1
                requestBody.app_id = f"SV{count}"
            requestBody.login_token = uuid.uuid4()
            if requestBody.country_name.lower() != "india":
                requestBody.is_international = True
            else:
                requestBody.is_international = False

            user = jsonable_encoder(requestBody)
            new_user = await db[dbName].insert_one(user)
            created_user = await db[dbName].find_one({'_id': new_user.inserted_id})
            created_user['referral_link'] = AppUtils.encodeValue(
                created_user['app_id'])
            created_user['token'] = auth_handler.encode_token(user['app_id'])

            if AppUtils.getSettings().ENVIRONMENT == AppUtils.getEnvironment().dev:
                BASEURL = AppUtils.getSettings().BASEURL_DEV
            elif AppUtils.getSettings().ENVIRONMENT == AppUtils.getEnvironment().uat:
                BASEURL = AppUtils.getSettings().BASEURL_UAT
            else:
                BASEURL = AppUtils.getSettings().BASEURL_PROD

            value = f"{user['app_id'],user['email_id'],AppUtils.getCurrentDateTime()}"
            vToken = AppUtils.encodeData(value)

            bodyMessage = {
                "userName": user['name'] + " ( " + user['app_id'] + " )",
                "link": f"{BASEURL}/verify?email={user['email_id']}&verify_token={vToken}",
            }

            message = MessageSchema(
                subject="Reg: Welcome mail",
                recipients=[user['email_id']],
                subtype='html',
                template_body=json.loads(json.dumps(bodyMessage)),
            )

            background_tasks.add_task(
                AppUtils.sendEmail, message, "send_verification_mail.html")

        return AppUtils.responseWithData(True, status.HTTP_200_OK, "Welcome to Yaari.", userModelLoginRes(created_user))

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def verifyEmail(requestBody: VerifyEmailModel):
    try:

        if requestBody.token is not None:
            vToken = AppUtils.decodeData(requestBody.token)
            email = vToken.split(",")[1].replace("'", "").strip()
            if requestBody.email_id == email:
                db = await AppUtils.openDb()
                dbName = AppDatabase.getName().user
                user = await db[dbName].find_one({'email_id': email})
                if user['email_verified']:
                    return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Email already verified.")
                else:
                    await db[dbName].update_one({'_id': user['_id']}, {'$set': {'email_verified': True}})
                    return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Email verified successfully.")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Email verificaiton failed.")
        else:
            db = await AppUtils.openDb()
            dbName = AppDatabase.getName().user
            user = await db[dbName].find_one({'email_id': requestBody.email_id})
            if user['otp'] is not None and int(user['otp']) == int(requestBody.otp):
                auth_handler = AuthHandler()
                login_token = uuid.uuid4()
                user['login_token'] = login_token
                user['referral_link'] = AppUtils.encodeValue(user['app_id'])
                user['token'] = auth_handler.encode_token(user['app_id'])

                updateValue = {
                    'otp': None,
                    'otp_time': None,
                    'login_token': str(login_token),
                    'last_login': AppUtils.getCurrentDateTime()}

                await db[dbName].update_one({'_id': user['_id']}, {'$set': jsonable_encoder(updateValue)})
                return AppUtils.responseWithData(True, status.HTTP_200_OK, "User fetched successfully.", userModelLoginRes(user))
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Incorrect OTP.")
    except Exception as ex:
        print(f"Error: {ex}")
        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Invalid link")


async def loginSession(requestBody: UpdateFCMModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().user
        user = await db[dbName].find_one({'app_id': requestedUser})
        if user is not None:
            await db[dbName].update_one({'_id': user['_id']}, {'$set': jsonable_encoder(requestBody)})
            auth_handler = AuthHandler()
            login_token = uuid.uuid4()
            user['login_token'] = login_token
            user['referral_link'] = AppUtils.encodeValue(user['app_id'])
            user['token'] = auth_handler.encode_token(user['app_id'])

            return AppUtils.responseWithData(True, status.HTTP_200_OK, "Session updated successfully", userModelLoginRes(user))
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "User not found")

    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def updateUser(requestBody: UpdateUserModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().user
        user = await db[dbName].find_one({'app_id': requestedUser})

        if user is not None:
            updateValue = {}
            responseMsg = "User details updated successfully."
            if requestBody.name is not None:
                updateValue['name'] = requestBody.name
            if requestBody.email_id is not None:
                updateValue['email_id'] = requestBody.email_id
            if requestBody.mobile_no is not None:
                updateValue['mobile_no'] = requestBody.mobile_no
            if requestBody.is_live is not None:
                updateValue['is_live'] = requestBody.is_live
                responseMsg = "Trade status updated successfully"
            if requestBody.status is not None:
                updateValue['status'] = requestBody.status
            await db[dbName].update_one({'_id': user['_id']}, {'$set': jsonable_encoder(updateValue)})
            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, responseMsg)
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "User not found")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)
