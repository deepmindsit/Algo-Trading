import uuid
import json
from fastapi import Request, status, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi_mail import FastMail, MessageSchema
from models.admin_model import UserFilterModel
from schemas.admin_schema import UserModelList
from utils.app_database import AppDatabase
from user_agents import parse
from utils.app_utils import AppUtils
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


async def create(background_tasks: BackgroundTasks, requestBody: UserModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbName = AppDatabase.getName().user

        adminUser = await db[dbName].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role']:
            if requestBody.client_id is not None:
                user = await db[dbName].find_one({'_id': requestBody.client_id})
                if user is not None:
                    updateValue = {
                        'role': requestBody.role
                    }
                    await db[dbName].update_one({'_id': requestBody.client_id}, {'$set': jsonable_encoder(updateValue)})
                    return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Admin added successfully.")
                else:
                    return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "User not found.")
            else:
                user = await isUserExists(db=db, dbName=dbName, requestBody=requestBody)
                if user is not None:
                    return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Either mobile number or email Id is already registered.")
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
                    await db[dbName].insert_one(user)

                    if AppUtils.getSettings().ENVIRONMENT == AppUtils.getEnvironment().dev:
                        BASEURL = AppUtils.getSettings().BASEURL_DEV
                    elif AppUtils.getSettings().ENVIRONMENT == AppUtils.getEnvironment().uat:
                        BASEURL = AppUtils.getSettings().BASEURL_UAT
                    else:
                        BASEURL = AppUtils.getSettings().BASEURL_PROD

                    bodyMessage = {
                        "userName": user['name'] + " ( " + user['app_id'] + " )",
                        "mobileNo": user['mobile_no'],
                        "emailId": user['email_id'],
                        "link": f"{BASEURL}",
                    }

                    message = MessageSchema(
                        subject="Reg: Welcome mail",
                        recipients=[user['email_id']],
                        subtype='html',
                        template_body=json.loads(json.dumps(bodyMessage)),
                    )

                    background_tasks.add_task(
                        AppUtils.sendEmail, message, "welcome_mail.html")

                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Admin added successfully.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def updateUser(userId: str, requestBody: UpdateUserModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        adminUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role'] and userId is not None:
            user = await db[dbUser].find_one({'_id': userId})

            if user is not None:
                updateValue = {}
                responseMsg = "User details updated successfully."
                if requestBody.name is not None:
                    updateValue['name'] = requestBody.name
                if requestBody.email_id is not None:
                    updateValue['email_id'] = requestBody.email_id
                if requestBody.mobile_no is not None:
                    updateValue['mobile_no'] = requestBody.mobile_no
                if requestBody.role is not None:
                    updateValue['role'] = requestBody.role
                if requestBody.referral_code is not None:
                    updateValue['referral_code'] = requestBody.referral_code
                if requestBody.country_name is not None:
                    updateValue['is_international'] = requestBody.country_name.lower(
                    ) != "india"
                    updateValue['country_name'] = requestBody.country_name
                if requestBody.is_live is not None:
                    updateValue['is_live'] = requestBody.is_live
                    responseMsg = "Trade status updated successfully"
                if requestBody.is_copy_trade is not None:
                    updateValue['is_copy_trade'] = requestBody.is_copy_trade
                    responseMsg = "Copy trade status updated successfully"
                if requestBody.status is not None:
                    if requestBody.status == 1:
                        responseMsg = "User blocked successfully"
                    else:
                        responseMsg = "User unblocked successfully"
                    updateValue['status'] = requestBody.status
                await db[dbUser].update_one({'_id': userId}, {'$set': jsonable_encoder(updateValue)})
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, responseMsg)
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "User not found")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission denied")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def userList(request: UserFilterModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user

        adminUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role']:

            userQuery = {}

            if request.role is not None:
                userQuery['role'] = request.role

            if request.is_live is not None:
                userQuery['is_live'] = request.is_live

            if request.is_subscribed is not None:
                userQuery['is_subscribed'] = request.is_subscribed

            if request.is_copy_trade is not None:
                userQuery['is_copy_trade'] = request.is_copy_trade

            if request.referral_code is not None:
                userQuery['referral_code'] = request.referral_code

            if request.status is not None:
                userQuery['status'] = request.status

            if request.from_date is not None:
                userQuery['created_date'] = {
                    '$gte': request.from_date.strftime('%Y-%m-%d'),
                }

            if request.to_date is not None:
                userQuery['created_date']['$lte'] = request.to_date.strftime(
                    '%Y-%m-%d')

            userList = []

            if request.offset is not None and request.limit is not None:
                async for user in db[dbUser].find(userQuery).limit(request.limit).skip(request.offset):
                    userList.append(user)
            else:
                print(f"Query ---> {userQuery}")
                async for user in db[dbUser].find(userQuery):
                    userList.append(user)

            if len(userList) > 0:
                return AppUtils.responseWithData(True, status.HTTP_200_OK, "Users fetched successsfully", UserModelList(userList))
            else:
                return AppUtils.responseWithData(False, status.HTTP_200_OK, "No users found", [])
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.", [])
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def dashboard(requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbAccount = AppDatabase.getName().account

        adminUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role']:
            userList = []
            adminList = []
            superAdminList = []
            subscribedList = []
            unsubscribedList = []
            paperTrade = []
            liveTrade = []
            copyTrade = []
            interNational = []

            async for user in db[dbUser].find():
                # Check user is subscribed or not
                if user['is_subscribed']:
                    subscribedList.append(user)
                else:
                    unsubscribedList.append(user)

                # Check user role
                if user['role'] == "SUPER ADMIN":
                    superAdminList.append(user)
                elif user['role'] == "ADMIN":
                    adminList.append(user)
                else:
                    userList.append(user)

                # Check trading account status
                if user['is_copy_trade']:
                    copyTrade.append(user)

                account = await db[dbAccount].find_one({'user_id': user['_id'], 'trade_status': True})
                if account is not None:
                    liveTrade.append(user)
                else:
                    paperTrade.append(user)

                if user['is_international']:
                    interNational.append(user)

            response = {
                'user_list': UserModelList(userList),
                'admin_list': UserModelList(adminList),
                'super_admin_list': UserModelList(superAdminList),
                'admin_list': UserModelList(adminList),
                'subscribed_list': UserModelList(subscribedList),
                'unsubscribed_list': UserModelList(unsubscribedList),
                'paper_trade': UserModelList(paperTrade),
                'live_trade': UserModelList(liveTrade),
                'copy_trade': UserModelList(copyTrade),
                'inter_national': UserModelList(interNational),
            }

            return AppUtils.responseWithData(True, status.HTTP_200_OK, "Data fetched successfully.", response)
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)
