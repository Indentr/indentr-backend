from mongoengine import Document, EmailField, ReferenceField, StringField

from app.database.schemas.practice import Practice


class User(Document):
    ROLES = ("Owner", "Member")

    name = StringField(required=True)
    email = EmailField(required=True, unique=True)
    password = StringField(required=True)
    practice_id = ReferenceField(Practice)
    role = StringField(choices=ROLES, required=True)

    meta = {"collection": "users"}  # Specify the collection name
