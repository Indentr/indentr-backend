from typing import Literal

from pydantic import BaseModel


class getFiles(BaseModel):
    file_type: Literal["letters", "notes"]


class saveFile(BaseModel):
    file_text: str
    file_id: str
    file_type: Literal["letter", "note"]
