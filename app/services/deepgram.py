import json

from deepgram import Deepgram

from app.constants import DEEPGRAM_API_KEY


async def dpg_speech_to_text(file_path):
    # Initializes the Deepgram SDK
    deepgram = Deepgram(DEEPGRAM_API_KEY)
    print("file pathe :")
    print(file_path)

    with open(file_path, "rb") as audio:
        source = {"buffer": audio, "mimetype": "audio/webm"}
        response = deepgram.transcription.sync_prerecorded(source, {"punctuate": True})
        print(json.dumps(response, indent=4))
        return response
