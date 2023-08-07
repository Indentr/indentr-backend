from fastapi import APIRouter, Depends, HTTPException, Request
from bson import ObjectId

from app.middleware.jwt import JWTBearer, decodeJWT

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/")
def get_files(request: Request, access_token=Depends(JWTBearer())):
    """
    """

    db = request.app.state.db
    token = decodeJWT(access_token)
    user_id = ObjectId(token['user_id'])

    letters_collection = db['letters']
    letters = list(letters_collection.find({'user_id': user_id}))

    # Access the 'createdAt' field for each letter and convert it to time date format
    # Add a createdAt attribute to letter
    for letter in letters:
        created_at = letter['_id'].generation_time.strftime('%Y-%m-%d %H:%M:%S')
        letter['createdAt'] = created_at
        letter['_id'] = str(letter['_id'])
        letter['user_id'] = str(letter['user_id'])

    return { "letters": letters }
