import logging

from fastapi import APIRouter, Depends, HTTPException

from app.database.crud import create_new_vector_letter, retrieve_vector_letters
from app.middleware.jwt import JWTBearer
from app.services.openAI import generate_embedding

router = APIRouter(prefix="/vector-letter", tags=["Vector letter"])

# initiates logger
log = logging.getLogger(__name__)


@router.post("/upload-vector-example-letter")
async def upload_vector_example_letter(letter: str, letter_title: str, access_token=Depends(JWTBearer())):
    """
    endpoint to generate an openAI embedding and saves the example letter along with embedding to MongoDB.
    """
    try:
        embedding = await generate_embedding(letter)
        create_new_vector_letter(letter, letter_title, embedding)
        return {"success"}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/get-similar-vector-letter")
async def mongo_vector_search(text: str, access_token=Depends(JWTBearer())):
    """
    endpoint to test the vector search
    """
    try:
        embedding = await generate_embedding(text)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "default",
                    "queryVector": embedding,
                    "path": "plot_embedding",
                    "numCandidates": 100,
                    "limit": 1,
                }
            }
        ]
        letters = retrieve_vector_letters(pipeline)
        return str(letters)

    except HTTPException as e:
        raise e  # Reraise the HTTPException
