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
    symptomDetails: str


class DentistNotes(BaseModel):
    dentistNotes: str


class treatmentPlanData(BaseModel):
    patientDetails: str
    symptomDetails: str


class createTreatmentPlan(BaseModel):
    treatmentPlan: str
    patientDetails: str
