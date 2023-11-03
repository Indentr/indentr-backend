import base64

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.user import userDetails

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/")
def get_profile(request: Request, access_token=Depends(JWTBearer())):
    """
    Retrieves the user's profile information along with their latest letters.
    """

    db = request.app.state.db
    token = decodeJWT(access_token)

    user_id = token["user_id"]
    users_collection = db["users"]
    user = users_collection.find_one({"_id": ObjectId(user_id)}, {"_id": 0, "email": 1, "phone": 1, "address": 1, "img": 1})
    if user is not None:
        user_object = {
            "email": user["email"],
            "phone": user.get("phone", None),
            "address": user.get("address", None),
            "img": base64.b64encode(user.get("img", b"")).decode("utf-8"),
        }

    letters_collection = db["letters"]
    letters = list(letters_collection.find({"user_id": ObjectId(user_id)}).sort("_id", -1).limit(3))

    # Access the 'createdAt' field for each letter and convert it to time date format
    # Add a createdAt attribute to letter
    for letter in letters:
        created_at = letter["_id"].generation_time.strftime("%Y-%m-%d %H:%M:%S")
        letter["createdAt"] = created_at
        letter["_id"] = str(letter["_id"])
        letter["user_id"] = str(letter["user_id"])

    return {"user": user_object, "letters": letters}


@router.post("/saveImg")
async def save_img(request: Request, access_token=Depends(JWTBearer())):
    """
    # Upload and Save User Profile Image
    Allows a user to upload and save an image for their profile.
    The image data is received as binary data in the request stream.
    The image is then associated with the user's email and stored in the database.
    """

    try:
        # Get the image data from the request stream
        image = b""
        async for chunk in request.stream():
            image += chunk

        if not image:
            raise HTTPException(status_code=400, detail="No image data provided")

        # Extract user's email from JWT token
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        print(user_id)

        # Update the user's image in MongoDB
        dbUsers = request.app.state.db.users
        dbUsers.update_one({"_id": ObjectId(user_id)}, {"$set": {"img": image}})

        encoded_image = base64.b64encode(image).decode("utf-8")

        return {"image": encoded_image}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save image") from e


@router.post("/saveDetails")
async def save_details(body: userDetails, request: Request, access_token=Depends(JWTBearer())):
    """
    Saves the user's email, phone number, and address to the database.
    """

    try:
        email = body.email
        phone = body.phone
        address = body.address

        if not email or not phone or not address:
            raise HTTPException(status_code=400, detail="No data provided")

        # Extract user's email from JWT token
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        # Update the user's image in MongoDB
        dbUsers = request.app.state.db.users
        dbUsers.update_one({"_id": ObjectId(user_id)}, {"$set": {"email": email, "phone": phone, "address": address}})

        return {"email": email, "phone": phone, "address": address}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save details") from e
