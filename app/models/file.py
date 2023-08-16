from pydantic import BaseModel


class saveTreatmentPlan(BaseModel):
    treatmentPlan: str
    letterId: str

