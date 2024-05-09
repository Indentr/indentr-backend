import logging

from deepgram import DeepgramClient, PrerecordedOptions

from app.constants import DEEPGRAM_API_KEY

# initiates logger
log = logging.getLogger(__name__)


async def dpg_speech_to_text(audio_buffer):
    try:
        # Initializes the Deepgram SDK
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)

        # Use BytesIO object as the buffer for Deepgram API
        source = {"buffer": audio_buffer, "mimetype": "audio/webm"}

        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            language="en",
        )

        response = deepgram.listen.prerecorded.v("1").transcribe_file(source, options)

        return response

    except Exception as e:
        log.debug(f"Exception: {e}")
        raise e
