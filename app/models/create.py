from datetime import date

from pydantic import BaseModel, Field, constr
from typing import Dict, List


# Request model
class PatientDetails(BaseModel):
    forename: str
    surname: str
    dob: date
    gender: str
    address: str
    numSymptoms: int





# Request model
class SymptomData(BaseModel):
    symptomDetails: Dict[str, str] = Field(..., example={"symptom1": "description1", "symptom2": "description2"})

# Response model
class SymptomResponse(BaseModel):
    symptom: str
    q1: str
    q2: str
    q3: str

# Response model
class SymptomsResponse(BaseModel):
    items: List[SymptomResponse]





# Request model
class PatientDetails(BaseModel):
    dob: str
    forename: str
    surname: str
    address: str

# Request model
class SymptomDetails(BaseModel):
    class Config:
        extra = "allow"  # Allows any additional fields
    

# Request model
class TreatmentPlanData(BaseModel):
    patientDetails: PatientDetails
    symptomDetails: SymptomDetails = Field(..., example = {"symptom1": "description1","symptom2": "description2"})


# Response model
class TreatmentPlanResponse(BaseModel):
    html_content: str = Field(..., example = '<p>123 Main St,</p><p>City,</p><p>Country,</p><p></p><p>Dear John Doe,</p><p></p><p>[HTML-formatted treatment plan]</p>')








# Request model
class SaveTreatmentPlan(BaseModel):
    treatmentPlan: str = Field(..., example = '<p>123 Main St,</p><p>City,</p><p>Country,</p><p></p><p>Dear John Doe,</p><p></p><p>[HTML-formatted treatment plan]</p>')
    patientDetails: PatientDetails


# Response model
class SaveTreatmentPlanResponse(BaseModel):
    message: str = Field(..., example = 'Letter saved successfully')
    letter_id: str = Field(..., example = 'Letter saved successfully')

