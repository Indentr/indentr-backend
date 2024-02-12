from mongoengine import Document, EmailField, StringField, URLField


class Practice(Document):
    practice_name = StringField(required=True)
    primary_email = EmailField(required=True, unique=True)
    website_url = URLField()
    address = StringField()
    phone = StringField()
    triage_email = EmailField(required=False, unique=False)

    meta = {"collection": "dental_practices"}  # Specify the collection name
