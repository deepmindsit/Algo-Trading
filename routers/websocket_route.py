from typing import Any, List
from config.auth import AuthHandler
from fastapi import APIRouter, Body, Depends, WebSocket
from models.user_model import UserModel
from repository import websocket_repo
from utils.app_utils import AppUtils

router = APIRouter(
    prefix=f"/{AppUtils.getSettings().APIVERSION}/api/websocket",
    tags=['Websocket']
)

auth_handler = AuthHandler()


@router.get('/')
async def start_websocket(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await websocket_repo.start_websocket(requestedUser)


@router.websocket('/subscribe')
async def websocketEndpoint(websocket: WebSocket, token: str = None):
    await websocket_repo.connectWebsocket(websocket=websocket, token=token)
