from typing import Optional

from pydantic import BaseModel


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
    stripe_customer_id: str
    gratis_password: Optional[str] = None


class CheckEmail(BaseModel):
    email: str
