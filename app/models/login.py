from pydantic import BaseModel
from typing import Optional


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    practice_name: str
    practice_email: str
    practice_url: Optional[str] = None
    address: str
    phone: str
    session_id: str
    subscription_id: str


class CheckEmail(BaseModel):
    email: str


