import base64

from fastapi import APIRouter, Depends, HTTPException, Request

from app.database.crud import (
    get_last_three_letters,
    get_user_by_id,
    update_user_details,
    update_user_image,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.user import userDetails

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/")
def get_profile(access_token=Depends(JWTBearer())):
    """
    Retrieves the user's profile information along with their latest letters.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        user = get_user_by_id(user_id)
        letters = get_last_three_letters(user_id)

        # Convert the image data to base64 if it's in binary format
        user_img = user.get("img")
        if user_img:
            user["img"] = base64.b64encode(user["img"]).decode("utf-8")

        # Convert ObjectId to string in user_object
        user["_id"] = str(user["_id"])
        user.pop("password", None)

        for letter in letters:
            created_at = letter["_id"].generation_time.strftime("%Y-%m-%d %H:%M:%S")
            letter["createdAt"] = created_at
            letter["_id"] = str(letter["_id"])
            letter["user_id"] = str(letter["user_id"])

        return {"user": user, "letters": letters}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


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

        update_user_image(image, user_id)
        encoded_image = base64.b64encode(image).decode("utf-8")
        return {"image": encoded_image}

    except HTTPException as e:
        raise e  # Reraise the HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save image") from e


@router.post("/saveDetails")
async def save_details(body: userDetails, access_token=Depends(JWTBearer())):
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

        # Update the user's details in MongoDB
        user = update_user_details(user_id, email, phone, address)
        return {"email": user["email"], "phone": user["phone"], "address": user["address"]}

    except HTTPException as e:
        raise e  # Reraise the HTTPException
