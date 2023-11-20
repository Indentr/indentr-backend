import json

from bson import ObjectId
from fastapi import HTTPException
from mongoengine import DoesNotExist
from werkzeug.security import generate_password_hash

from app.database.schemas.config import Config
from app.database.schemas.letter import Letter
from app.database.schemas.pricing import Pricing
from app.database.schemas.user import User


# User ---------------------------
def get_user_by_id(user_id):
    try:
        user = User.objects.get(id=ObjectId(user_id))
        return user.to_mongo().to_dict()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")


def update_user_image(image, user_id):
    try:
        user = User.objects.get(id=ObjectId(user_id))
        user.img = image
        user.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")


def update_user_details(user_id, email, phone, address):
    try:
        user = User.objects.get(id=ObjectId(user_id))
        user.email = email
        user.phone = phone
        user.address = address
        user.save()

        return user.to_mongo().to_dict()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")


# Function to find a user by email
def get_user_by_email(email):
    user = User.objects(email=email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user.to_mongo().to_dict()


# Function to check if user registrations are allowed and email exists
def check_user_registration_and_email(email):
    # Check if user registrations are allowed
    configs_doc = Config.objects.first()

    if not configs_doc:
        raise HTTPException(status_code=404, detail="Config document not found.")

    if not configs_doc.allow_registrations:
        raise HTTPException(status_code=403, detail="User registrations are not allowed at the moment.")

    # Check if the email already exists
    existing_user = User.objects(email=email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use")


def create_new_user(name, email, password):
    # Hash the password
    hash_pass = generate_password_hash(password, method="scrypt")
    # Create a User document
    new_user = User(name=name, email=email, password=hash_pass)
    new_user.save()


# Pricing ---------------------------
def get_pricing(user_id):
    try:
        user = User.objects.get(id=ObjectId(user_id))
        pricing = Pricing.objects(practice_id=user.practice_id).first()

        if pricing is None:
            # raise HTTPException(status_code=404, detail="No pricing found")
            return "No pricing available, use best judgement"

        return pricing.pricing

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")


# Letter ---------------------------
def get_last_three_letters(user_id):
    try:
        letters = Letter.objects(user_id=ObjectId(user_id)).order_by("-_id").limit(3)
        # Convert each letter to a dictionary
        letters_dict = [letter.to_mongo().to_dict() for letter in letters]
        return letters_dict

    except DoesNotExist:
        # Handle the case where no letters are found
        return []


def get_all_users_letters(user_id: str):
    try:
        User.objects.get(id=ObjectId(user_id))
        # Query letters using MongoEngine
        letters = Letter.objects(user_id=user_id).order_by("patient_info__last_name")
        # Transform the MongoEngine documents to a list of dictionaries
        letters_list = []
        for letter in letters:
            created_at = letter.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
            letter_dict = letter.to_mongo().to_dict()
            letter_dict["createdAt"] = created_at
            letter_dict["_id"] = str(letter.id)
            letter_dict["user_id"] = str(letter.user_id.id)

            letters_list.append(letter_dict)

        return letters_list

    except DoesNotExist as e:
        # Check if the exception is related to User or Letter
        if "User" in str(e):
            raise HTTPException(status_code=404, detail="User not found")
        elif "Letter" in str(e):
            raise HTTPException(status_code=404, detail="No letter found")
        else:
            raise e


# Function to get a specific letter
def get_user_letter(letter_id, user_id):
    # Query the letter using MongoEngine
    letter = Letter.objects(id=ObjectId(letter_id), user_id=user_id).first()

    if not letter:
        # Handle case where the letter doesn't exist or doesn't belong to the user
        raise HTTPException(status_code=400, detail="No letter found")

    created_at = letter.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
    letter_dict = letter.to_mongo().to_dict()
    letter_dict["createdAt"] = created_at
    letter_dict["_id"] = str(letter.id)
    letter_dict["user_id"] = str(letter.user_id.id)

    return letter_dict


def create_new_letter(user_id, treatment_plan, patient_details):
    try:
        user = User.objects.get(id=user_id)

        # Create a new Letter document
        letter = Letter(consent_letter=treatment_plan, patient_info=json.loads(patient_details), user_id=user)

        # Save the new letter to the database
        letter.save()

        return str(letter.id)

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")


# Function to update the consent letter
def update_letter(letter_id, treatment_plan, user_id):
    # Use MongoEngine to find and update the document
    letter = Letter.objects(id=ObjectId(letter_id), user_id=ObjectId(user_id)).first()

    if not letter:
        raise HTTPException(status_code=404, detail="No letter found")

    # Update the consent_letter field
    letter.consent_letter = treatment_plan
    letter.save()
