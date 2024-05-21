from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.custom_prompt import CustomPrompt


def create_custom_prompt(user_id: str, practice_id: str, prompt_title: str, prompt_text: str, example: str = ""):
    try:
        custom_prompt = CustomPrompt(user_id=user_id, practice_id=practice_id, title=prompt_title, text=prompt_text, example=example)
        custom_prompt.save()
        return custom_prompt

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


def retrieve_all_users_prompts(practice_id: str):
    try:
        prompts = CustomPrompt.objects(practice_id=practice_id).only("title", "text", "example").select_related()

    except DoesNotExist as e:
        raise e

    # Transform the MongoEngine documents to a list of dictionaries
    prompts_list = []
    for prompt in prompts:
        prompt_dict = prompt.to_mongo().to_dict()
        prompt_dict["_id"] = str(prompt_dict["_id"])
        prompts_list.append(prompt_dict)

    return prompts_list


def retrieve_prompt_with_prompt_id(practice_id: str, prompt_id: str):
    prompt = CustomPrompt.objects(practice_id=practice_id, id=prompt_id).first().select_related()

    if not prompt:
        # Handle case where the note doesn't exist or doesn't belong to the user
        raise HTTPException(status_code=400, detail="No prompt found")

    prompt_dict = prompt.to_mongo().to_dict()

    return prompt_dict


def update_custom_prompt(practice_id: str, prompt_id: str, title: str = None, text: str = None, example: str = None):
    try:
        prompt = CustomPrompt.objects(practice_id=practice_id, id=prompt_id).first().select_related()

        if not prompt:
            # Handle case where the note doesn't exist or doesn't belong to the user
            raise HTTPException(status_code=404, detail="No prompt found")

        if title:
            prompt.title = title

        if text:
            prompt.text = text

        if example:
            prompt.example = example

        prompt.save()

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


def delete_custom_prompt(practice_id: str, prompt_id: str):
    try:
        prompt = CustomPrompt.objects(practice_id=practice_id, id=prompt_id).first()

        if prompt is None:
            raise HTTPException(status_code=404, detail="Prompt not found") from None

        prompt.delete()

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
