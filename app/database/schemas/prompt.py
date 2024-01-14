from mongoengine import (
    Document,
    StringField,
)


class Prompt(Document):
    title = StringField(required=True, unique=True)
    prompt_text = StringField(required=True)

    meta = {"collection": "prompts"}  # Specify the collection name
