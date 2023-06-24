

from fastapi import status, BackgroundTasks
from models.user_model import UserModel
from repository.account_repo import resetToken
from repository.strategy_1_repo import strategy_1
from repository.strategy_2_repo import strategy_2
from repository.strategy_repo import getHistoricalData
from utils.app_constants import AppConstants
from utils.app_database import AppDatabase
from utils.app_utils import ApiCalls, AppUtils, Requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from repository.websocket_repo import start_websocket, checkWsIsRunning


async def start_service(requestedUser: UserModel):
    try:
        db = await AppUtils.openDb()
        dbUser = AppDatabase.getName().user

        user = await db[dbUser].find_one({'app_id': requestedUser})
        if user is not None:
            if AppUtils.getRole().admin in user['role']:
                asyncScheduler = AsyncIOScheduler()
                asyncScheduler.start()

                # /////////////////////////////////////////////////////////////////////////////////////////////
                #  To start websocket
                # /////////////////////////////////////////////////////////////////////////////////////////////
                asyncScheduler.add_job(start_websocket, trigger=CronTrigger.from_crontab(
                    AppConstants.StartWscron), args=[requestedUser])

                asyncScheduler.add_job(strategy_1, trigger=CronTrigger.from_crontab(
                    AppConstants.StartStrategy1cron))

                asyncScheduler.add_job(strategy_2, trigger=CronTrigger.from_crontab(
                    AppConstants.StartStrategy2cron))

                asyncScheduler.add_job(getHistoricalData, trigger=CronTrigger.from_crontab(
                    AppConstants.GetHistoricalData))

                # asyncScheduler.add_job(updateFutureContract, trigger=CronTrigger.from_crontab(
                #     AppConstants.UpdateFutureContractcron), args=[requestedUser])

                asyncScheduler.add_job(resetToken, trigger=CronTrigger.from_crontab(
                    AppConstants.resetTokencron), args=[requestedUser])

                asyncScheduler.add_job(checkWsIsRunning, trigger=CronTrigger.from_crontab(
                    AppConstants.Every1Mincron), args=[requestedUser])

                return AppUtils.responseWithoutData(True, status.HTTP_200_OK, "Done")
            else:
                return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "Permission Denied")
        else:
            return AppUtils.responseWithoutData(False, status.HTTP_200_OK, "User not found")

    except Exception as ex:
        print(f"Error: {ex}")
        return AppUtils.responseWithoutData(False, status.HTTP_200_OK, str(ex))
