from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import user

from app.constants import config

import logging

from starlette_context import context, plugins
from starlette_context.middleware import RawContextMiddleware
from starlette.middleware import Middleware

from fastapi.staticfiles import StaticFiles
from app.db import connect_to_mongodb

middleware = [Middleware(RawContextMiddleware)]


app = FastAPI(middleware=middleware)


# initialize logging
log_level = logging.DEBUG
logging.basicConfig(
    level=log_level,
    filename="log.log",
    filemode="a",
    format="%(asctime)s.%(msecs)03d %(name)s %(levelname)s %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


logging.debug(f"Logging initialized at level {log_level}")


app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config['PROD']['ALLOWED_ORIGINS'],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_mongo_db():
    return connect_to_mongodb(config['PROD']['DB_URI'])


@app.on_event("startup")
async def startup_event():
    # When server starts up create a mongodb instance and save to apps state
    app.state.db = get_mongo_db()


@app.get("/")
def get_health():
    return {"message": "Welcome to Indentr!"}


app.include_router(user.router)
