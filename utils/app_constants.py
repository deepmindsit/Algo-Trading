from struct import Struct
import logging


from models.common_model import LogConfig


class AppConstants():

    # Database:
    DBPREF = "RestApi"

    # Connection
    dbClient = None
    websocket = None

    # Logger
    log = logging.getLogger('yaari_ws')

    # Websocket
    wsPlatform = ""
    appName = "Yaari"
    futureSegmentObj = None

    TickData = []
    # cron
    isAppscheduled = None
    GetHistoricalData = "40 8 * * *"
    StartWscron = "15 09 * * *"
    StartStrategy1cron = "18 09 * * *"
    StartStrategy2cron = "20 09 * * *"
    StartStrategy3cron = "20 09 * * *"
    StartLunchcron = "45 12 * * *"
    Every1Mincron = "* * * * *"
    Every2Mincron = "*/2 * * * *"
    Every3Mincron = "*/3 * * * *"
    Every5Mincron = "*/5 * * * *"
    Every10Mincron = "*/10 * * * *"
    Every15Mincron = "*/15 * * * *"
    Every30Mincron = "*/30 * * * *"
    Every60Mincron = "* 1 * * *"
    Every2Hrcron = "* 2 * * *"

    StockBackUpcron = "00 18 * * *"
    DBInsertioncron = "30 15 * * *"
    UpdateFutureContractcron = "00 23 * * *"
    resetTokencron = "00 6 * * *"
    FlushRediscron = "30 8 * * *"
    CheckHoliday = "35 6 * * *"
    SquareOff = "5 15 * * *"

    # Candles
    count = 0
    Candle_1 = ""
    Candle_3 = ""
    Candle_5 = ""
    Candle_10 = ""
    Candle_15 = ""
    Candle_30 = ""
    Candle_60 = ""

    # Redis
    # Pref.Keys
    strategy_1 = "strategy_1_"
    strategy_2 = "strategy_2_"
    strategy_3 = "strategy_3_"
    candle = "candle_"
    stock = "stock_"
    strike = "strike_"
    hisStock = "historical_stock_"

    # backtest dates
    currentDayDate = "16 Jun 23"
    previousDayDate = "15 Jun 23"

    # Websocket
    wsConnection = []

    ###############################################
    # Fyers Ws
    # constants for message conversions
    FY_P_ENDIAN = '> '
    FY_P_HEADER_FORMAT = Struct(FY_P_ENDIAN + "Q L H H H 6x")
    FY_P_COMMON_7208 = Struct(FY_P_ENDIAN + "10I Q")
    FY_P_EXTRA_7208 = Struct(FY_P_ENDIAN + "4I 2Q")
    FY_P_MARKET_PIC = Struct(FY_P_ENDIAN + "3I")
    FY_P_LENGTH = Struct(FY_P_ENDIAN + "H")

    # constants for packet length definitions
    FY_P_LEN_NUM_PACKET = 2
    FY_P_LEN_HEADER = 24
    FY_P_LEN_COMN_PAYLOAD = 48
    FY_P_LEN_EXTRA_7208 = 32
    FY_P_LEN_BID_ASK = 12
    FY_P_BID_ASK_CNT = 10
    FY_P_LEN_RES = 6
    ###############################################
