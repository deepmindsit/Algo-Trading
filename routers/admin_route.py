from typing import Any
from config.auth import AuthHandler
from fastapi import APIRouter, Body, Depends, Request, BackgroundTasks
from models.admin_model import UserFilterModel
from models.user_model import *
from repository import admin_repo
from utils.app_utils import AppUtils

router = APIRouter(
    prefix=f"/{AppUtils.getSettings().APIVERSION}/api/admin",
    tags=['Admin']
)

auth_handler = AuthHandler()


@router.post('/create')
async def create(background_tasks: BackgroundTasks, requestBody: UserModel = Body(...), requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await admin_repo.create(background_tasks, requestBody, requestedUser)


@router.put('/details/{userId}')
async def updateUser(userId: str, request: UpdateUserModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await admin_repo.updateUser(userId, request, requestedUser)


@router.get('/dashboard')
async def dashboard(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await admin_repo.dashboard(requestedUser)


@ router.post('/')
async def userList(request: UserFilterModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await admin_repo.userList(request, requestedUser)
