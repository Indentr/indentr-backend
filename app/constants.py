import os

from dotenv import load_dotenv

load_dotenv()

DB_URI = os.getenv("DB_URI")
TEST_DB_URI = os.getenv("TEST_DB_URI")
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = os.getenv("MAIL_PORT")
MAIL_USE_SSL = os.getenv("MAIL_USE_SSL")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
TRIAGE_MAIL = os.getenv("TRIAGE_MAIL")
TRIAGE_MAIL_PASSWORD = os.getenv("TRIAGE_MAIL_PASSWORD")
