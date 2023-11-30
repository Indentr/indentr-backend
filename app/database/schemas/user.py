from mongoengine import Document, EmailField, IntField, ReferenceField, StringField

from app.database.schemas.practice import Practice


class User(Document):
    ROLES = ("Owner", "Member")

    name = StringField()
    email = EmailField()
    password = StringField()
    practice_id = ReferenceField(Practice)
    role = StringField(choices=ROLES)
    tokens_consumed = IntField(default=0)

    meta = {"collection": "users"}  # Specify the collection name
