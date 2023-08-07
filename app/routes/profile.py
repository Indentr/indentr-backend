import base64

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.user import userDetails

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/")
def get_profile(request: Request, access_token=Depends(JWTBearer())):
    """
    Get the user's profile information and their latest letters.

    Parameters:
    - request (Request): The request object from FastAPI.
    - access_token (str, optional): The JWT access token obtained from the `JWTBearer` dependency.

    Returns:
        dict: A dictionary containing the user's profile information and their latest letters.

    Raises:
        `HTTPException`: If the access token is invalid or if there are any errors during data retrieval.
    """

    db = request.app.state.db
    token = decodeJWT(access_token)

    user_id = token['user_id']
    users_collection = db['users']
    user = users_collection.find_one({'_id': ObjectId(user_id)}, {'_id': 0, 'email': 1, 'phone': 1, 'address': 1, 'img': 1})
    if user is not None:
        user_object = {
            'email': user['email'],
            'phone': user.get('phone', None),
            'address': user.get('address', None),
            'img': base64.b64encode(user.get('img', b'')).decode('utf-8')
        }

    letters_collection = db['letters']
    letters = list(letters_collection.find({'user_email': user['email']}).sort('_id', -1).limit(3))


    # Access the 'createdAt' field for each letter and convert it to time date format
    # Add a createdAt attribute to letter
    for letter in letters:
        created_at = letter['_id'].generation_time.strftime('%Y-%m-%d %H:%M:%S')
        letter['createdAt'] = created_at
        letter['_id'] = str(letter['_id'])

    return { "user": user_object, "letters": letters }





@router.post("/saveImg")
async def saveImg(request: Request, access_token=Depends(JWTBearer())):
    """
    Upload and save the user's profile image.

    This endpoint allows a user to upload and save their profile image. The image data is received
    as binary data in the request stream. The image is then associated with the user's email and
    stored in the database.

    Parameters:
    - request (Request): The request object from FastAPI.
    - access_token (str, optional): The JWT access token obtained from the `JWTBearer` dependency.

    Returns:
        dict: A dictionary containing the encoded image data of the saved image.

    Raises:
        `HTTPException`: If there are any errors during image upload or database update.
    """

    try:
        # Get the image data from the request stream
        image = b''
        async for chunk in request.stream():
            image += chunk

        if not image:
            raise HTTPException(status_code=400, detail="No image data provided")

        # Extract user's email from JWT token
        token = decodeJWT(access_token)
        user_email = token['user_id']


        # Update the user's image in MongoDB
        dbUsers = request.app.state.db.users
        dbUsers.update_one(
            {'email': user_email},
            {'$set': {'img': image}}
        )

        encoded_image = base64.b64encode(image).decode('utf-8')

        return { 'image': encoded_image }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save image") from e






@router.post("/saveDetails")
async def saveDetails(body: userDetails, request: Request, access_token=Depends(JWTBearer())):
    """
    Save User Details

    Save the user's email, phone number, and address to the database.

    Args:
        body (userDetails): The user details to be updated.
        request (Request): The request object from FastAPI.
        access_token (str, optional): The JWT access token obtained from the `JWTBearer` dependency.

    Returns:
        dict: A dictionary containing the updated user details.

    Raises:
        HTTPException: If there are any errors during the update process.
    """

    try:
        email = body.email
        phone = body.phone
        address = body.address

        if not email or not phone or not address:
            raise HTTPException(status_code=400, detail="No data provided")

        # Extract user's email from JWT token
        token = decodeJWT(access_token)
        user_email = token['user_id']


        # Update the user's image in MongoDB
        dbUsers = request.app.state.db.users
        dbUsers.update_one(
            {'email': user_email},
            {'$set': {
                'email': email,
                'phone': phone,
                'address': address
            }}
        )

        return { 'email': email, 'phone': phone, 'address': address }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save details") from e















