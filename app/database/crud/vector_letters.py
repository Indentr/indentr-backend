# Vector letters CRUD file
# -- Files must start with either create, retrieve, update, delete

from typing import List

from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.example_consent_letters import VectorExampleLetter


def create_new_vector_letter(consent_letter: str, title: str, plot_embedding: List[float]):
    try:
        letter = VectorExampleLetter(consent_letter=consent_letter, title=title, plot_embedding=plot_embedding)
        letter.save()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


def retrieve_vector_letters(pipeline):
    try:
        result = VectorExampleLetter.objects.aggregate(*pipeline)
        return list(result)

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Error retrieving alphabet_status") from None
