from typing import Literal

from pydantic import BaseModel


class EditUserField(BaseModel):
    text: str
    record: Literal["name", "email", "password"]


class EditPracticeField(BaseModel):
    text: str
    record: Literal["name", "email", "address", "website"]


class DeleteUser(BaseModel):
    member_id: str
    practice_id: str


class UserRegistration(BaseModel):
    name: str
    email: str
    password: str
    practice_id: str
