from typing import Any
from config.auth import AuthHandler
from fastapi import APIRouter, Body, Depends, Request, BackgroundTasks
from models.user_model import *
from repository import user_repo
from utils.app_utils import AppUtils

router = APIRouter(
    prefix=f"/{AppUtils.getSettings().APIVERSION}/api/user",
    tags=['User']
)

auth_handler = AuthHandler()


@router.post('/exists')
async def checkUserExists(requestBody: LoginModel = Body(...)):
    return await user_repo.checkUserExists(requestBody=requestBody)


@router.post('/login')
async def login(background_tasks: BackgroundTasks, requestBody: LoginModel = Body(...)):
    return await user_repo.login(requestBody=requestBody, background_tasks=background_tasks)


@router.post('/register')
async def register(background_tasks: BackgroundTasks, requestBody: UserModel = Body(...)):
    return await user_repo.register(requestBody=requestBody, background_tasks=background_tasks)


@router.post('/verify')
async def verifyEmail(requestBody: VerifyEmailModel = Body(...)):
    return await user_repo.verifyEmail(requestBody=requestBody)


@router.post('/login-session')
async def loginSession(request: UpdateFCMModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await user_repo.loginSession(request, requestedUser)


@router.put('/details')
async def updateUser(request: UpdateUserModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await user_repo.updateUser(request, requestedUser)
