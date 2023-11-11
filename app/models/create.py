from pydantic import BaseModel, Field

# Request model
# class PatientDetails(BaseModel):
#     forename: str
#     surname: str
#     dob: date
#     gender: str
#     address: str
#     numSymptoms: int


# Request model
class SymptomData(BaseModel):
    symptomDetails: str = Field(..., example={"0": "description1", "1": "description2"})


# Response model
class SymptomResponse(BaseModel):
    symptom: str
    q1: str
    q2: str
    q3: str


# Request model
class TreatmentPlanData(BaseModel):
    patientDetails: str = Field(
        ..., example={"dob": "1111-11-11", "forename": "Ryan", "surname": "Reynolds", "address": "1 Hollywood, Los Angeles, United States"}
    )
    symptomDetails: str = Field(
        ...,
        example=[
            {
                "q1": {"chatGPTQuestion": "Has the patient experienced any sensitivity to hot or cold foods or beverages?", "dentistResponse": "No"},
                "q2": {"chatGPTQuestion": "Is the toothache constant or does it come and go?", "dentistResponse": "constant"},
                "q3": {
                    "chatGPTQuestion": "Has the patient noticed any swelling or redness around the affected tooth?",
                    "dentistResponse": "yes there is swelling",
                },
            }
        ],
    )


# Response model
class TreatmentPlanResponse(BaseModel):
    html_content: str = Field(
        ..., example="<p>123 Main St,</p><p>City,</p><p>Country,</p><p></p><p>Dear John Doe,</p><p></p><p>[HTML-formatted treatment plan]</p>"
    )


# Request model
class DentistNotes(BaseModel):
    dentistNotes: str


# Request model
class SaveTreatmentPlan(BaseModel):
    treatmentPlan: str = Field(
        ..., example="<p>123 Main St,</p><p>City,</p><p>Country,</p><p></p><p>Dear John Doe,</p><p></p><p>[HTML-formatted treatment plan]</p>"
    )
    patientDetails: str = Field(
        ..., example={"dob": "1111-11-11", "forename": "Ryan", "surname": "Reynolds", "address": "1 Hollywood, Los Angeles, United States"}
    )


# Response model
class SaveTreatmentPlanResponse(BaseModel):
    message: str = Field(..., example="Letter saved successfully")
    letter_id: str = Field(..., example="123456789")
