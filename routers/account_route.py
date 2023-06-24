from typing import Any, List
from config.auth import AuthHandler
from fastapi import APIRouter, Body, Depends, Query
from models.account_model import AccountModel, AuthCodeModel, UpdateAccountModel
from repository import account_repo
from models.user_model import UserModel
from utils.app_utils import AppUtils

router = APIRouter(
    prefix=f"/{AppUtils.getSettings().APIVERSION}/api/account",
    tags=['Account']
)

auth_handler = AuthHandler()


@router.post('/create')
async def create(request: AccountModel = Body(...), requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await account_repo.create(request=request, requestedUser=requestedUser)


@router.post('/authcode')
async def authCode(authCode: AuthCodeModel = Body(...), requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await account_repo.authCode(authCode, requestedUser)


@router.put('/update-status/{liveStatus}')
async def authCode(liveStatus: int, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await account_repo.updateStatus(liveStatus, requestedUser)


@router.delete('/{id}')
async def delete(id: str, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await account_repo.delete(id, requestedUser)


@router.put('/{id}')
async def update(id: str, request: UpdateAccountModel = Body(...), requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await account_repo.update(id, request, requestedUser)


@router.get('/')
async def list(user_id: str | None = Query(default=None), requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await account_repo.list(user_id, requestedUser)
