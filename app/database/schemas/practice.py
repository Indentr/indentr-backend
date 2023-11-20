from mongoengine import Document, EmailField, StringField, URLField


class Practice(Document):
    practice_name = StringField(required=True)
    practice_code = StringField(required=True, unique=True)
    primary_email = EmailField(required=True)
    website_url = URLField()

    meta = {"collection": "dental_practices"}  # Specify the collection name
