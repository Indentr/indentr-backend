from mongoengine import BooleanField, Document


class Config(Document):
    allow_registrations = BooleanField()

    meta = {"collection": "configs"}  # Specify the collection name

    def __str__(self):
        return f"Allow Registrations: {self.allow_registrations}"
