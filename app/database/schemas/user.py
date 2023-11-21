from mongoengine import Document, fields

from app.database.schemas.practice import Practice


class User(Document):
    name = fields.StringField()
    email = fields.EmailField()
    password = fields.StringField()
    practice_id = fields.ReferenceField(Practice)
    img = fields.BinaryField()
    address = fields.StringField()
    phone = fields.StringField()

    meta = {"collection": "users"}  # Specify the collection name
