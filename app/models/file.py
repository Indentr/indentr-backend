from pydantic import BaseModel


class getFiles(BaseModel):
    file_type: str


class saveTreatmentPlan(BaseModel):
    treatmentPlan: str
    letterId: str


