

from fastapi import APIRouter, BackgroundTasks, Depends
from config.auth import AuthHandler
from models.user_model import UserModel
from repository import service_repo
from utils.app_utils import AppUtils

auth_handler = AuthHandler()

router = APIRouter(
    prefix=f"/{AppUtils.getSettings().APIVERSION}/api/service",
    tags=['Service']
)


@router.get('/')
async def start_service(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await service_repo.start_service(requestedUser=requestedUser)
