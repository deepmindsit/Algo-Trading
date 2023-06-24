import gzip
import json
import redis
from utils.app_utils import AppUtils


# if AppUtils.getSettings().ENVIRONMENT != AppUtils.getEnvironment().dev:
#     rds = redis.StrictRedis(port=AppUtils.getSettings(
#     ).REDIS_PORT, db=0, password=AppUtils.getSettings().REDIS_PASS)
# else:
rds = redis.StrictRedis(port=AppUtils.getSettings().REDIS_PORT, db=0)


class RedisDB():
    def setJson(key, data):
        data = json.dumps(data, default=str)
        rds.set(key, data)
        return True

    def getJson(key):
        cache_data = rds.get(key)
        if cache_data is None:
            return None
        cache_data = json.loads(cache_data)
        return cache_data

    async def setJsonNew(key, data):
        data = json.dumps(data, default=str)
        rds.set(key, data)
        return True

    async def getJsonNew(key):
        cache_data = rds.get(key)
        if cache_data is None:
            return None
        cache_data = json.loads(cache_data)
        return cache_data

    def compressJson(jsonValue):
        jsonString = json.dumps(jsonValue)
        jsonEncode = jsonString.encode('utf-8')
        # print(jsonEncode)
        return gzip.compress(jsonEncode)

    def delData(key):
        rds.delete(key)
        return True
