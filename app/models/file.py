from typing import Literal

from pydantic import BaseModel


class FileType(BaseModel):
    file_type: Literal["letter", "note", "patient"]


class SearchFiles(BaseModel):
    search_param: str
    file_type: Literal["letter", "note", "patient"]


class SaveFile(BaseModel):
    file_text: str
    file_id: str
    file_type: Literal["letter", "note", "patient"]


class SelectChar(BaseModel):
    file_type: Literal["letter", "note", "patient"]
    char: str


class DeleteFile(BaseModel):
    file_type: Literal["letter", "note", "patient"]
    file_id: str
