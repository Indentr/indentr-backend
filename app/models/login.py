from pydantic import BaseModel


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserRegisterRequest(BaseModel):
    name: str 
    email: str 
    password: str 
