import logging
import backoff
import openai

from app.constants import OPENAI_API_KEY
log = logging.getLogger(__name__)


@backoff.on_exception(backoff.expo, (openai.error.RateLimitError, openai.error.ServiceUnavailableError, openai.error.Timeout))
async def ask_gpt(prompt: str, system_prompt: str):
    # Log the input to the API
    log.info(f"Sending prompt to GPT:\nSystem Prompt: {system_prompt}\nUser Prompt: {prompt}")

    openai.api_key = OPENAI_API_KEY
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], temperature=0.0
        )

        content = response["choices"][0]["message"]["content"]
        total_tokens = response["usage"]["total_tokens"]

        # Log the response from the API
        log.info(f"GPT response:\n{content}\nTokens consumed: {total_tokens}")

        return content
    except openai.error.OpenAIError as e:
        # Log the error if the API call fails
        log.error(f"An error occurred: {str(e)}")
        raise
