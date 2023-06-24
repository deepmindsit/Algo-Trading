from typing import Any, List
from config.auth import AuthHandler
from fastapi import APIRouter, Body, Depends, Query
from models.strategy_model import *
from models.user_model import UserModel
from repository import strategy_1_repo, strategy_2_repo, strategy_3_repo, strategy_repo
from utils.app_utils import AppUtils
from utils.strategy_utils import StrgyUtils

router = APIRouter(
    prefix=f"/{AppUtils.getSettings().APIVERSION}/api/strategy",
    tags=['Strategy']
)

auth_handler = AuthHandler()

# Sof: Strategy Settings


@router.post('/setting/create')
async def createSettings(request: StrategySettingsModel = Body(...), requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.createSettings(request=request, requestedUser=requestedUser)


@router.get('/setting/mapped-user')
async def mappedUser(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.mappedUser(requestedUser)


@router.delete('/setting/{id}')
async def deleteSettings(id: str, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.deleteSettings(id, requestedUser)


@router.put('/setting/{id}')
async def updateSettings(id: str, request: StrategyUpdateSettingsModel = Body(...), requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.updateSettings(id, request, requestedUser)


@ router.get('/setting')
async def listSettings(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.listSettings(requestedUser)

# Eod: Strategy Setting
############################################################################################################################################################
# Sof: Map Strategy


@router.post('/map/create')
async def createMap(request: List[MapStrategyModel] = Body(...), requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.createMap(requestList=request, requestedUser=requestedUser)


@router.delete('/map/{id}')
async def deleteMap(id: str, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.deleteMap(id, requestedUser)


@ router.post('/map')
async def listMap(fiterBy: UpdateMapStrategyModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.listMap(fiterBy, requestedUser)

# Eod: Map Strategy
############################################################################################################################################################
# Sof: Strategy


@ router.post('/history')
async def listStrategyHistory(request: StrategyFilterModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.listStrategyHistory(request, requestedUser)


@router.get('/1')
async def strategy_1(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_1_repo.strategy_1()


@router.get('/1BT')
async def strategy_1(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_1_repo.strategy_1_back_test()


@router.get('/2BT')
async def strategy_1(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_2_repo.strategy_2_back_test()


@router.get('/3BT')
async def strategy_1(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_3_repo.strategy_3_back_test()


@router.get('/historical-data')
async def getHistoricalData(requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.getHistoricalData()


@ router.post('/exit-order')
async def listStrategy(exitOrder: ExitOrderModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await StrgyUtils.exitOrderSquareOff(exitOrder, requestedUser)


@ router.post('/')
async def listStrategy(filterBy: StrategyFilterModel, requestedUser: UserModel = Depends(auth_handler.auth_wrapper)):
    return await strategy_repo.listStrategy(filterBy, requestedUser)


# Eod: Strategy
############################################################################################################################################################
