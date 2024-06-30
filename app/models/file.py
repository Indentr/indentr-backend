from typing import Literal

from pydantic import BaseModel


class GetFile(BaseModel):
    file_type: Literal["letter", "note", "patient", "transcript"]
    created_by: Literal["You", "Practice"]


class SearchFiles(BaseModel):
    search_param: str
    file_type: Literal["letter", "note", "patient", "transcript"]
    created_by: Literal["You", "Practice"]


class SaveFile(BaseModel):
    file_text: str
    file_id: str
    file_type: Literal["letter", "note", "patient", "transcript"]


class SelectChar(BaseModel):
    file_type: Literal["letter", "note", "patient", "transcript"]
    char: str
    created_by: Literal["You", "Practice"]


class DeleteFile(BaseModel):
    file_type: Literal["letter", "note", "patient", "transcript"]
    file_id: str
