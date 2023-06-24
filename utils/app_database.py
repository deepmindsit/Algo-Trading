from enum import Enum
from utils.app_constants import AppConstants

from utils.app_utils import AppUtils


class name(str, Enum):
    user = f"{AppConstants.DBPREF}_user"
    referral = f"{AppConstants.DBPREF}_referral"
    plan = f"{AppConstants.DBPREF}_plan"
    account = f"{AppConstants.DBPREF}_account"
    subscription = f"{AppConstants.DBPREF}_subscription"
    admin_payment_gw = f"{AppConstants.DBPREF}_admin_payment_gw"
    admin_rp_orders = f"{AppConstants.DBPREF}_admin_rp_orders"
    websocket = f"{AppConstants.DBPREF}_websocket"
    holiday = f"{AppConstants.DBPREF}_holiday"
    model_cash = f"{AppConstants.DBPREF}_model_cash"
    model_future = f"{AppConstants.DBPREF}_model_future"
    model_option = f"{AppConstants.DBPREF}_model_option"
    strategy = f"{AppConstants.DBPREF}_strategy"
    strategy_setting = f"{AppConstants.DBPREF}_strategy_setting"
    map_strategy = f"{AppConstants.DBPREF}_map_strategy"
    strategy_order = f"{AppConstants.DBPREF}_strategy_order"
    archive_strategy = f"{AppConstants.DBPREF}_archive_strategy"
    archive_strategy_order = f"{AppConstants.DBPREF}_archive_strategy_order"


class AppDatabase():
    def getName() -> name:
        return name
