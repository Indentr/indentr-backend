from mongoengine import Document, EmailField, StringField, URLField


class Practice(Document):
    practice_name = StringField(required=True)
    primary_email = EmailField(required=True)
    website_url = URLField()
    address = StringField()
    phone = StringField()

    meta = {"collection": "dental_practices"}  # Specify the collection name
