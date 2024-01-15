from mongoengine import Document, FloatField, ReferenceField, StringField


class Pricing(Document):
    practice_id = ReferenceField("Practice", required=True)
    treatment = StringField(required=True)
    price = FloatField(required=True)

    meta = {"collection": "pricing"}

    def __str__(self):
        return f"{self.treatment} - £{self.price}"
