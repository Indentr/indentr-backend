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
    practice_url: str
    address: str
    phone: str
    triage_email: str
    triage_email_password: str
