import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette_context.middleware import RawContextMiddleware

from app.constants import ALLOWED_ORIGINS, DB_URI
from app.database.db import connect_to_mongoengine
from app.routes import auth, create, files, profile, triage, vector_letter

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGINS],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def startup_event():
    # When server starts up establish connection with mongodb
    connect_to_mongoengine(DB_URI)


@app.get("/")
def get_health():
    return {"message": "Welcome to Indentr!"}


app.add_event_handler("startup", startup_event)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(files.router)
app.include_router(create.router)
app.include_router(triage.router)
app.include_router(vector_letter.router)
