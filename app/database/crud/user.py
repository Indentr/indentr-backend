# User CRUD file
# -- Files must start with either create, retrieve, update, delete

from fastapi import HTTPException
from mongoengine import DoesNotExist
from werkzeug.security import generate_password_hash

from app.database.schemas.config import Config
from app.database.schemas.user import User


def create_new_user(name: str, email: str, password: str, practice_id: str, role: str):
    # Check if provided role is valid
    if role not in User.ROLES:
        raise ValueError(f"Invalid role: {role}")

    # Hash the password
    hash_pass = generate_password_hash(password, method="scrypt")
    # Create a User document
    new_user = User(name=name, email=email, password=hash_pass, practice_id=practice_id, role=role)
    new_user.save()

    user_dict = new_user.to_mongo().to_dict()

    # Convert ObjectId to string in user_object
    user_dict["_id"] = str(new_user.id)
    practice_id = user_dict.get("practice_id")
    if practice_id:
        user_dict["practice_id"] = str(new_user.practice_id.id)
    user_dict.pop("password", None)

    return user_dict


def delete_member(member_id: str, practice_id: str):
    # Check that the user's practice_id matches the practice_id being passed and the role is Member
    user_to_delete = User.objects(id=member_id, practice_id=practice_id, role="Member").first()

    if not user_to_delete:
        raise HTTPException(status_code=404, detail="No member with that id found in practice")

    # Delete the user document
    user_to_delete.delete()


def retrieve_allow_user_registrations():
    # Check if user registrations are allowed
    configs_doc = Config.objects.first()
    if not configs_doc:
        raise HTTPException(status_code=404, detail="Config document not found.")

    return configs_doc.allow_registrations


def retrieve_user_by_id(user_id: str):
    try:
        user = User.objects.get(id=user_id)
        user_dict = user.to_mongo().to_dict()

        # Convert ObjectId to string in user_object
        user_dict["_id"] = str(user.id)
        practice_id = user_dict.get("practice_id")
        if practice_id:
            user_dict["practice_id"] = str(user.practice_id.id)
        user_dict.pop("password", None)

        return user_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


# Function to find a user by email
def retrieve_user_by_email(email: str):
    user = User.objects(email=email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user.to_mongo().to_dict()


def retrieve_all_practice_users(practice_id: str):
    # Query all users with the given practice_id
    practice_members = User.objects(practice_id=practice_id).only("name", "email", "role").select_related()

    if not practice_members:
        return []

    # Convert the QuerySet to a list of dictionaries
    members_dict_list = []
    for member in practice_members:
        member_dict = member.to_mongo().to_dict()
        member_dict["_id"] = str(member.id)
        members_dict_list.append(member_dict)

    return members_dict_list


def update_user_details(user_id: str, name: str = None, email: str = None, password: str = None):
    try:
        user = User.objects.get(id=user_id)
        if name:
            user.name = name

        if email:
            try:
                # Attempt to retrieve the user by email
                existing_user = retrieve_user_by_email(email)
            except HTTPException as e:
                # Handle the 404 exception if user is not found
                if e.status_code == 404:
                    existing_user = None
                else:
                    raise

            # Check if the email already exists
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already in use")

            user.email = email

        if password:
            hash_pass = generate_password_hash(password, method="scrypt")
            user.password = hash_pass

        user.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None
