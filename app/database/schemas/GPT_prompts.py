
from mongoengine import (
    Document,
    StringField,
)


class GPTPrompts(Document):
    title = StringField(required=True, unique=True)
    prompt_text = StringField(required=True)

    meta = {"collection": "GPT_prompts"}  # Specify the collection name
