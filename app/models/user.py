from pydantic import BaseModel


class UserDetails(BaseModel):
    email: str
    phone: str
    address: str


class DeleteUser(BaseModel):
    member_id: str
    practice_id: str


class UserRegistration(BaseModel):
    name: str
    email: str
    password: str
    practice_id: str
