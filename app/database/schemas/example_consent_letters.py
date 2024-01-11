
from mongoengine import Document, FloatField, ListField, StringField


class VectorExampleLetter(Document):
    consent_letter = StringField(required=True)
    title = StringField(required=True)
    plot_embedding = ListField(FloatField(), required=True)

    meta = {"collection": "example_consent_letters"}  # Specify the collection name
