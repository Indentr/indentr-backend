from typing import Optional

from fastapi import UploadFile
from pydantic import BaseModel


# Request model
class PatientSearch(BaseModel):
    search_param: str

    model_config = {"json_schema_extra": {"examples": [{"search_param": "janedoe@gmail.com"}]}}


# Request model
class SaveNote(BaseModel):
    updated_note: str
    note_id: str


# Request model
class PatientDetails(BaseModel):
    patientDetails: str

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
                    },
                }
            ]
        }
    }


# Request model
class SymptomData(BaseModel):
    symptomDetails: str

    model_config = {"json_schema_extra": {"examples": [{"symptomDetails": {"0": "description of symptom 1", "1": "description of symptom 2"}}]}}


# Response model
class SymptomResponse(BaseModel):
    symptom: str
    q1: str
    q2: str
    q3: str


# Request model
class LetterData(BaseModel):
    patientDetails: str
    symptomDetails: Optional[str] = None
    dentistNotes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "patientDetails": {
                        "dob": "1111-11-11",
                        "forename": "Ryan",
                        "surname": "Reynolds",
                        "address": "1 Hollywood, Los Angeles, United States",
                        "email": "ryanreynolds1@gmail.com",
                    },
                    "symptomDetails": [
                        {
                            "q1": {
                                "chatGPTQuestion": "Has the patient experienced any sensitivity to hot or cold foods or beverages?",
                                "dentistResponse": "No",
                            },
                            "q2": {
                                "chatGPTQuestion": "Is the toothache constant or does it come and go?",
                                "dentistResponse": "constant",
                            },
                            "q3": {
                                "chatGPTQuestion": "Has the patient noticed any swelling or redness around the affected tooth?",
                                "dentistResponse": "yes there is swelling",
                            },
                        }
                    ],
                    "dentistNotes": "Example dentist notes",
                }
            ]
        }
    }


# Response model
class LetterResponse(BaseModel):
    html_content: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "html_content": "<p>123 Main St,</p><p>City,</p><p>Country,</p><p></p><p>Dear John Doe,</p><p></p><p>[HTML-formatted treatment plan]</p>",
                    "input_tokens": 3201,
                    "output_tokens": 3002,
                    "cost": 0.015,
                    "model": "gpt-4-turbo-preview",
                }
            ]
        }
    }


# Request model
class SaveFile(BaseModel):
    treatment_plan: str
    patient_details: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "treatmentPlan": "<p>123 Main St,</p><p>City,</p><p>Country,</p><p></p><p>Dear John Doe,</p><p></p><p>[HTML-formatted treatment plan]</p>",
                    "patientDetails": {"email": "ryanreynolds1@gmail.com"},
                    "input_tokens": 3201,
                    "output_tokens": 3002,
                    "cost": 0.015,
                    "model": "gpt-4-turbo-preview",
                }
            ]
        }
    }


# Response model
class SaveFileResponse(BaseModel):
    message: str
    letter_id: str

    model_config = {"json_schema_extra": {"examples": [{"html_content": "Letter saved successfully", "letter_id": "123456789"}]}}


# Request model
class SaveAudioNotes(BaseModel):
    audioFile: UploadFile
    patientEmail: str


# Request model
class FormatTranscript(BaseModel):
    transcript: str
    prompt_id: str
