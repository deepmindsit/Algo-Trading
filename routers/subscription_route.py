from typing import Any
from config.auth import AuthHandler
from fastapi import APIRouter, Body, Depends, Request, BackgroundTasks
from models.admin_model import UserFilterModel
from models.subscription_model import PlanFilterModel, PlanModel, SubscriptionFilterModel, SubscriptionModel, UpdatePlanModel
from models.user_model import UserModel
from repository import subscription_repo
from utils.app_utils import AppUtils

router = APIRouter(
    prefix=f"/{AppUtils.getSettings().APIVERSION}/api/subscription",
    tags=['Subscription']
)

auth_handler = AuthHandler()


@router.post('/plan/create')
async def createPlan(requestBody: PlanModel = Body(...), requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await subscription_repo.createPlan(requestBody, requestedUser)


@router.put('/plan/{id}')
async def updatePlan(id: str, request: UpdatePlanModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await subscription_repo.updatePlan(id, request, requestedUser)


@ router.delete('/plan/{id}')
async def deletePlan(id: str, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await subscription_repo.deletePlan(id, requestedUser)


@ router.post('/plan')
async def planList(request: PlanFilterModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await subscription_repo.planList(request, requestedUser)


@ router.post('/add')
async def addSub(request: SubscriptionModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await subscription_repo.addSub(request)


@ router.delete('/delete/{id}')
async def deleteSub(id: str, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await subscription_repo.deleteSub(id)


@ router.post('/')
async def listSub(request: SubscriptionFilterModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await subscription_repo.listSub(request, requestedUser)
