# config CRUD file
# -- Files must start with either create, retrieve, update, delete

from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.prompt import Prompt


def create_new_prompt(title: str, prompt_text: str):
    # Create a Prompt document
    new_prompt = Prompt(title=title, prompt_text=prompt_text)
    new_prompt.save()


def retrieve_prompt_by_title(title: str):
    try:
        prompt = Prompt.objects.get(title=title)
        return prompt.prompt_text

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Prompt not found") from None
