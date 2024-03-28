# Practice CRUD file
# -- Files must start with either create, retrieve, update, delete

from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.practice import Practice


def create_new_practice(
    practice_name: str,
    email: str,
    url: str,
    address: str,
    phone: str,
    stripe_customer_id: str = None,
    triage_email: str = None,
    gratis_password=None,
):
    # Default triage email destination to practice email if it is unset
    if not triage_email:
        triage_email = email

    # Create a Practice document
    new_practice = Practice(
        practice_name=practice_name,
        primary_email=email,
        website_url=url,
        address=address,
        phone=phone,
        triage_email=triage_email,
        stripe_customer_id=stripe_customer_id,
        gratis_password=gratis_password,
    )
    new_practice.save()

    practice_dict = new_practice.to_mongo().to_dict()

    # Convert ObjectId to string in practice_dict
    practice_dict["_id"] = str(new_practice.id)

    return practice_dict["_id"]


# Function to find a practice by email
def retrieve_practice_by_email(email: str):
    practice = Practice.objects(primary_email=email).first()

    if not practice:
        raise HTTPException(status_code=404, detail="Practice not found")

    return practice.to_mongo().to_dict()


def retrieve_practice_by_stripe_customer_id(stripe_customer_id: str):
    practice = Practice.objects(stripe_customer_id=stripe_customer_id).first()

    if not practice:
        raise HTTPException(status_code=404, detail="Practice not found")

    return practice.to_mongo().to_dict()


def retrieve_practice_by_id(practice_id: str):
    try:
        practice = Practice.objects.get(id=practice_id)
        practice_dict = practice.to_mongo().to_dict()

        practice_dict["_id"] = str(practice.id)

        return practice_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Practice not found") from None


def update_practice_details(
    practice_id: str,
    name: str = None,
    email: str = None,
    address: str = None,
    phone: str = None,
    stripe_customer_id: str = None,
    gratis_password: str = None,
):
    try:
        practice = Practice.objects.get(id=practice_id)
        if name:
            practice.practice_name = name

        if email:
            try:
                # Attempt to retrieve the user by email
                existing_practice = retrieve_practice_by_email(email)
            except HTTPException as e:
                # Handle the 404 exception if user is not found
                if e.status_code == 404:
                    existing_practice = None
                else:
                    raise

            # Check if the email already exists
            if existing_practice:
                raise HTTPException(status_code=400, detail="Email already in use")

            practice.primary_email = email

        if address:
            practice.address = address

        if phone:
            practice.phone = phone

        if stripe_customer_id:
            practice.stripe_customer_id = stripe_customer_id

        if gratis_password:
            practice.gratis_password = gratis_password

        practice.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Practice not found") from None
