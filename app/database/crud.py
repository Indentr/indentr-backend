import base64

from bson import ObjectId
from fastapi import HTTPException


def get_user_details(db, user_id):
    users_collection = db["users"]
    user = users_collection.find_one({"_id": ObjectId(user_id)}, {"_id": 0, "email": 1, "phone": 1, "address": 1, "img": 1})

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Convert the image data to base64
    if "img" in user:
        user["img"] = base64.b64encode(user["img"]).decode("utf-8")

    return user


def update_user_image(db, image, user_id):
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"img": image}})


def get_pricing(db, user_id):
    users_collection = db["users"]
    pricing_collection = db["pricing"]

    # Use the aggregation framework to join the collections and project the desired fields
    result = users_collection.aggregate([
        {"$match": {"_id": ObjectId(user_id)}},
        {"$lookup": {
            "from": "pricing",
            "localField": "practice_id",
            "foreignField": "practice_id",
            "as": "pricing"
        }},
        {"$unwind": "$pricing"},
        {"$project": {"_id": 0, "pricing.pricing": 1}}
    ])

    pricing = next(result, None)

    if pricing is None:
        # raise HTTPException(status_code=404, detail="No pricing found")
        return "No pricing available, use best judgement"

    return pricing["pricing"]         

