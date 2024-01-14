from mongoengine import Document, FloatField, ReferenceField, StringField


class Pricing(Document):
    treatment = StringField(required=True)
    price = FloatField(required=True)
    practice_id = ReferenceField("Practice", required=True)

    meta = {"collection": "pricing"}  # Specify the collection name if needed

    def __str__(self):
        return f"{self.treatment} - £{self.price}"
