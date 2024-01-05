import json
from deepgram import Deepgram

from app.constants import DEEPGRAM_API_KEY


async def dpg_speech_to_text(audio_buffer):
    # Initializes the Deepgram SDK
    deepgram = Deepgram(DEEPGRAM_API_KEY)

    # Use BytesIO object as the buffer for Deepgram API
    source = {"buffer": audio_buffer, "mimetype": "audio/webm"}
    
    response = deepgram.transcription.sync_prerecorded(source, {"punctuate": False})
    
    return response
