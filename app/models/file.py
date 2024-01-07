from typing import Literal

from pydantic import BaseModel


class GetFiles(BaseModel):
    file_type: Literal["letter", "note"]


class SearchFiles(BaseModel):
    search_param: str
    file_type: Literal["letter", "note"]


class SaveFile(BaseModel):
    file_text: str
    file_id: str
    file_type: Literal["letter", "note"]
