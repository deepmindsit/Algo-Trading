import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from logging.config import dictConfig
from models.common_model import LogConfig
from utils.app_constants import AppConstants
from utils.app_utils import AppUtils
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.handlers.local import local_handler
from routers import (account_route, user_route, admin_route, subscription_route, websocket_route,
                     stocks_route, strategy_route, service_route)


dictConfig(LogConfig().dict())

isDebug = False
if AppUtils.getSettings().ENVIRONMENT != AppUtils.getEnvironment().prod:
    isDebug = True

app = FastAPI(debug=isDebug)
origins = [
    "http://localhost",
    "http://localhost:81",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    EventHandlerASGIMiddleware,
    handlers=[local_handler],
)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/templates", StaticFiles(directory="templates"), name="templates")

# models.Base.metadata.create_all(engine)
app.include_router(account_route.router)
app.include_router(user_route.router)
app.include_router(admin_route.router)
app.include_router(subscription_route.router)
app.include_router(websocket_route.router)
app.include_router(stocks_route.router)
app.include_router(strategy_route.router)
app.include_router(service_route.router)
