from mongoengine import Document, EmailField, ReferenceField, StringField

from app.database.schemas.practice import Practice


class User(Document):
    ROLES = ("Owner", "Member")

    name = StringField()
    email = EmailField()
    password = StringField()
    practice_id = ReferenceField(Practice)
    role = StringField(choices=ROLES)

    meta = {"collection": "users"}  # Specify the collection name
