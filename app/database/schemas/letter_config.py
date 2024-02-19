from mongoengine import (
    BinaryField,
    BooleanField,
    Document,
    ReferenceField,
    StringField,
    signals,
)

from app.database.schemas.practice import Practice


class LetterConfig(Document):
    RECIPIENT_NAMING = ("first_lastname", "lastname")
    DENTIST_NAMING = ("dentist_name", "dentist_practice_name", "practice_name")

    practice_id = ReferenceField(Practice, required=True)

    # Intro
    image = BinaryField()
    include_image = BooleanField(default=False)
    patient_address = BooleanField(default=True)
    date = BooleanField(default=False)
    salutation = StringField(default="Dear")
    recipient_naming = StringField(choices=RECIPIENT_NAMING, required=True, default="first_lastname")

    # Fees
    pricing = BooleanField(default=False)
    include_insurance_info = BooleanField(default=False)
    patient_insurance_info = StringField(default="hello")

    # Consent
    patient_signature = BooleanField(default=True)
    dentist_signature = BooleanField(default=True)

    # Signoff
    practice_contact_details = BooleanField(default=True)
    contact_details_text = StringField(default="")
    sign_off = StringField(default="From")
    dentist_naming = StringField(choices=DENTIST_NAMING, required=True, default="dentist_name")

    @classmethod
    def post_init(cls, sender, document, **kwargs):
        practice_id = document.practice_id.id
        practice_details = Practice.objects.get(id=practice_id)

        custom_paragraph = f"Should you have any questions or require further clarification on any aspect of the treatment, please do not hesitate to contact us{' on ' + practice_details.phone if practice_details.phone else ''}{' or email us at ' + practice_details.primary_email if practice_details.primary_email else ''}. We are here to support you every step of the way and ensure that you are comfortable and informed throughout the process."

        # Update the contact_details_text field
        document.contact_details_text = custom_paragraph

    meta = {"collection": "letter_config"}  # Specify the collection name


signals.post_init.connect(LetterConfig.post_init, sender=LetterConfig)
