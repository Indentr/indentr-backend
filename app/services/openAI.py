import backoff
import openai

from app.config import config


@backoff.on_exception(backoff.expo, (openai.error.RateLimitError, openai.error.ServiceUnavailableError, openai.error.Timeout))
async def ask_gpt(prompt: str, system_prompt: str):
    openai.api_key = config.get('OPENAI_API_KEY')
    response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0  # Set temperature to 0
        )

    content = response['choices'][0]['message']['content']
    total_tokens = response["usage"]["total_tokens"]
    print(f"GPT response:\n{content}\nTokens consumed: \033[92m{total_tokens}\033[0m")

    return content
