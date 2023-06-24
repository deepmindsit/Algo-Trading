
from datetime import date, datetime, timedelta
import uuid
import json
from fastapi import Request, status, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi_mail import FastMail, MessageSchema
from models.subscription_model import PlanFilterModel, PlanModel, SubscriptionFilterModel, SubscriptionModel, UpdatePlanModel
from schemas.subscription_schema import PlanModelList, PlanModelShow, SubscriptionModelList
from utils.app_database import AppDatabase
from user_agents import parse
from utils.app_utils import AppUtils
from models.user_model import UserModel


async def createPlan(requestBody: PlanModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbPlan = AppDatabase.getName().plan

        adminUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role']:
            plan = await db[dbPlan].find_one({'plan_name': requestBody.plan_name})
            if plan is not None:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, f"{requestBody.plan_name} is already addded")
            else:
                # Create New Plan
                plan = jsonable_encoder(requestBody)
                await db[dbPlan].insert_one(plan)
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Plan created successfully.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def updatePlan(id: str, requestBody: UpdatePlanModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbPlan = AppDatabase.getName().plan
        adminUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role']:
            plan = await db[dbPlan].find_one({'_id': id})

            if plan is not None:
                updateValue = {}
                responseMsg = "Plan updated successfully."
                if requestBody.plan_name is not None:
                    updateValue['plan_name'] = requestBody.plan_name
                if requestBody.price is not None:
                    updateValue['price'] = requestBody.price
                if requestBody.period_in_days is not None:
                    updateValue['period_in_days'] = requestBody.period_in_days
                if requestBody.offer is not None:
                    updateValue['offer'] = requestBody.offer
                if requestBody.offer_start_date is not None:
                    updateValue['offer_start_date'] = requestBody.offer_start_date
                if requestBody.offer_end_date is not None:
                    updateValue['offer_end_date'] = requestBody.offer_end_date
                if requestBody.description is not None:
                    updateValue['description'] = requestBody.description
                if requestBody.status is not None:
                    if requestBody.status == 1:
                        responseMsg = "Plan deactivated successfully"
                    else:
                        responseMsg = "Plan activated successfully"
                    updateValue['status'] = requestBody.status
                await db[dbPlan].update_one({'_id': id}, {'$set': jsonable_encoder(updateValue)})
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, responseMsg)
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Plan not found")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission denied")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def deletePlan(id: str, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbPlan = AppDatabase.getName().plan
        adminUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role']:
            plan = await db[dbPlan].find_one({'_id': id})
            if plan is not None:
                responseMsg = f"{plan['plan_name']} deleted successfully."
                await db[dbPlan].update_one({'_id': id}, {'$set': {'status': 1}})
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, responseMsg)
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Plan not found")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission denied")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def planList(request: PlanFilterModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbPlan = AppDatabase.getName().plan

        adminUser = await db[dbUser].find_one({'app_id': requestedUser})

        if adminUser is not None and AppUtils.getRole().admin in adminUser['role']:

            planQuery = {
                'status': 0
            }

            if request.period_in_days is not None:
                planQuery['period_in_days'] = request.period_in_days

            if request.offer_start_date is not None:
                planQuery['offer_start_date'] = {
                    '$gte': request.offer_start_date.strftime('%Y-%m-%d'),
                }

            if request.offer_end_date is not None:
                planQuery['offer_end_date'] = {
                    '$lte': request.offer_end_date.strftime('%Y-%m-%d'),
                }

            if request.status is not None:
                planQuery['status'] = request.status

            planList = []

            async for plan in db[dbPlan].find(planQuery):
                planList.append(plan)

            if len(planList) > 0:
                return AppUtils.responseWithData(True, status.HTTP_200_OK, "Plans fetched successsfully", PlanModelList(planList))
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "No data found")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def addSub(requestBody: SubscriptionModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbPlan = AppDatabase.getName().plan
        dbSubscription = AppDatabase.getName().subscription

        user = await db[dbUser].find_one({'_id': requestBody.user_id})
        if user is not None:
            plan = await db[dbPlan].find_one({'_id': requestBody.plan_id})
            if plan is None:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, f"Plan not found")
            else:
                today_date = date.today()
                requestBody.from_date = today_date
                requestBody.to_date = (today_date +
                                       timedelta(days=int(plan['period_in_days']))).strftime('%Y-%m-%d')

                subscription = jsonable_encoder(requestBody)
                await db[dbSubscription].insert_one(subscription)
                await db[dbUser].update_one({'_id': requestBody.user_id}, {'$set': {'is_subscribed': True}})
                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"{plan['plan_name']} subscribed successfully.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def deleteSub(id: str):
    try:
        db = await AppUtils.openDb()
        dbSubscription = AppDatabase.getName().subscription

        sub = await db[dbSubscription].find_one({'_id': id})
        if sub is not None:
            await db[dbSubscription].delete_one({'_id': id})
            return AppUtils.responseWithoutData(True, status.HTTP_200_OK, f"Subscription deleted successfully.")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Subscription not found.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)


async def listSub(request: SubscriptionFilterModel, requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user
        dbPlan = AppDatabase.getName().plan
        dbSubscription = AppDatabase.getName().subscription

        if request.user_id is not None:
            user = await db[dbUser].find_one({'_id': request.user_id})
        else:
            user = await db[dbUser].find_one({'app_id': requestedUser})

        if user is not None:

            subQuery = {}

            if AppUtils.getRole().admin not in user['role']:
                subQuery['user_id'] = user['_id']

            elif request.user_id is not None:
                subQuery['user_id'] = request.user_id

            if request.plan_id is not None:
                subQuery['plan_id'] = request.plan_id

            if request.from_date is not None:
                subQuery['from_date'] = {
                    '$gte': request.from_date.strftime('%Y-%m-%d'),
                }

            if request.to_date is not None:
                subQuery['to_date'] = {
                    '$lte': request.to_date.strftime('%Y-%m-%d'),
                }

            if request.status is not None:
                subQuery['status'] = request.status

            subscriptionList = []

            async for subscription in db[dbSubscription].find(subQuery):
                plan = await db[dbPlan].find_one({'_id': subscription['plan_id']})
                subscription['plan'] = PlanModelShow(plan)
                subscriptionList.append(subscription)

            if len(subscriptionList) > 0:
                return AppUtils.responseWithData(True, status.HTTP_200_OK, "Subscription fetched successsfully", SubscriptionModelList(subscriptionList))
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "No data found")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied.")
    except Exception as ex:
        print(f"Error: {ex}")
        if AppUtils.getEnvironment() != AppUtils.getEnvironment().prod:
            responseMsg = str(ex)
        else:
            responseMsg = "Bad Request"
        return AppUtils.responseWithoutData(False, status.HTTP_400_BAD_REQUEST, responseMsg)
