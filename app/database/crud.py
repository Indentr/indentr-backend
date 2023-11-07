from bson import ObjectId
from fastapi import HTTPException


def get_user_details(db, user_id):
    users_collection = db["users"]
    user = users_collection.find_one({"_id": ObjectId(user_id)}, {"_id": 0, "email": 1, "phone": 1, "address": 1, "img": 1})

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def update_user_image(db, image, user_id):
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"img": image}})
