from pydantic import BaseModel


class userDetails(BaseModel):
    email: str
    phone: str
    address: str
