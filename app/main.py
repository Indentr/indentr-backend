import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette_context.middleware import RawContextMiddleware

from app.constants import config
from app.db import connect_to_mongodb
from app.routes import login, profile, files, verifyJWT

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
    allow_origins=config["PROD"]["ALLOWED_ORIGINS"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_mongo_db():
    return connect_to_mongodb(config["PROD"]["DB_URI"])


@app.on_event("startup")
async def startup_event():
    # When server starts up create a mongodb instance and save to apps state
    app.state.db = get_mongo_db()


@app.get("/")
def get_health():
    return {"message": "Welcome to Indentr!"}


app.include_router(login.router)
app.include_router(profile.router)
app.include_router(files.router)
app.include_router(verifyJWT.router)
