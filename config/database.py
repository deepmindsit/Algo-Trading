import motor.motor_asyncio
from utils.app_utils import AppUtils

# Mongo Connections
if AppUtils.getSettings().ENVIRONMENT == AppUtils.getEnvironment().dev:
    MONGODB_DATABASE_URL = AppUtils.getSettings().MONGO_DEV
elif AppUtils.getSettings().ENVIRONMENT == AppUtils.getEnvironment().uat:
    MONGODB_DATABASE_URL = AppUtils.getSettings().MONGO_UAT
else:
    MONGODB_DATABASE_URL = AppUtils.getSettings().MONGO_PROD

MONGODB_DB_URL = AppUtils.getSettings().MONGO_PROD
# PyMongo
# db = MongoClient(MONGODB_DATABASE_URL)
# dbCollection = db.tradebot_fastapi

# Motor
db_client: motor.motor_asyncio.AsyncIOMotorClient = None


async def get_db_client():
    """Return database client instance."""
    db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_DATABASE_URL)
    return db_client


async def get_prod_db_client():
    """Return database client instance."""
    db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_DB_URL)
    return db_client


async def connect_db():
    """Create database connection."""
    db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_DATABASE_URL)


async def close_db():
    """Close database connection."""
    db_client.close()

# client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_DATABASE_URL)
# db = client.tradebot_fastapi
