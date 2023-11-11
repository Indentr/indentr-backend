import logging
import os

import backoff
import openai

from app.constants import OPENAI_API_KEY

# Relative path to the logs directory from the script's location
relative_path_to_logs = os.path.join("..", "logs")

# Absolute path to the logs directory
log_dir = os.path.abspath(relative_path_to_logs)

# Create the logs directory if it doesn't exist
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Now, specify the path to the log file
log_file_path = os.path.join(log_dir, "api_calls.log")

# Set up logging to file with the absolute path to the log file
logging.basicConfig(
    filename=log_file_path,  # Path to log file
    filemode="a",  # Append to the existing log file; use 'w' to overwrite
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Log message format
    level=logging.INFO,  # Logging level
)

# Get the logger
log = logging.getLogger(__name__)

# The rest of your function remains unchanged


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
