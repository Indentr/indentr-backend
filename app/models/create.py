from datetime import date

from pydantic import BaseModel


class PatientDetails(BaseModel):
    forename: str
    surname: str
    dob: date
    gender: str
    address: str
    numSymptoms: int


class SymptomData(BaseModel):
    patientDetails: str
    symptomDetails: str

