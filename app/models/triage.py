from typing import Literal

from pydantic import BaseModel


# Request model
class GenerateQuestions(BaseModel):
    patient_details: str
    practice_id: str
    existing_patient: bool

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "patientDetails": {
                        "forename": "Ryan",
                        "surname": "Reynolds",
                        "dob": "1111-11-11",
                        "gender": "Male",
                        "address": "1 Hollywood, Los Angeles, United States",
                        "email": "ryanreynolds1@gmail.com",
                        "symptom": "Tooth ache",
                    },
                    "practice_id": "6567b615374d9d2666baa475",
                    "existing_patient": True,
                }
            ]
        }
    }


class CreatePatientRequest(BaseModel):
    patient_details: str
    practice_id: str
    symptom_details: str


class ToggleTriageOpenedRequest(BaseModel):
    selected_requests: str
    opened: str


class ToggleTriageFolderRequest(BaseModel):
    selected_requests: str
    folder: Literal["ongoing", "completed"]


class SearchTriageRequests(BaseModel):
    search_param: str
    folder: Literal["all", "ongoing", "completed"]


class DeleteTriageRequests(BaseModel):
    selected_requests: str


class AddPatientToPractice(BaseModel):
    patient_id: str


# Request model
class CheckEmail(BaseModel):
    email: str
    practiceId: str
