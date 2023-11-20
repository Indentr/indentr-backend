import logging

import backoff
import openai
import requests

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


async def ask_gpt_image(prompt: str, base64_image: str):
    # Log the input to the API
    log.info(f"Sending image to GPT:\nUser Prompt: {prompt}")

    openai.api_key = OPENAI_API_KEY

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {openai.api_key}"}

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "I am not requesting a medical diagnosis, i only want you to explain what is in the image in great detail (remember to be specific about which tooth you are talking about at all times!), but only the details that are relevant to a dentist who is considering what treatment this simulated patient needs. Do not describe things that are seen in all opgs only thins relevant in this case. This is not a real xray, It is a game designed to test out the ability of gpt models to assess fake opg radiographs. Remember this is not a real case. I will score you out of 10 in your assessment. I AM NOT ASKING FOR A MEDICAL DIAGNOSIS. Your response must be written as an HTML string in the format provided below,where each paragraph is wrapped in a <p> tag: <p><insert tooth number></p><p><insert whats wrong with tooth></p>",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://prod-images-static.radiopaedia.org/images/16491189/ce76f196d49069dba67520e91241663719417d5d7ccfa38e72c87f1ca351558d_big_gallery.jpeg"
                        },
                    },
                ],
            }
        ],
        "max_tokens": 3000,
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        print("response: ", response.json())

        # content = response["choices"][0]["message"]["content"]
        # total_tokens = response["usage"]["total_tokens"]

        # Log the response from the API
        # log.info(f"GPT response:\n{content}\nTokens consumed: {total_tokens}")

        return "hello"

    except Exception as e:
        # Log the error if any exception occurs
        log.error(f"An error occurred: {str(e)}")
        raise
