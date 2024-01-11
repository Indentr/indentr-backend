from pydantic import BaseModel


class PriceListItem(BaseModel):
    service: str
    price: str
