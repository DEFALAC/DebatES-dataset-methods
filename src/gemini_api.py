'''
This module provides functions to configure and interact with the Gemini API.
It includes functions for making API calls with rate limiting and saving responses to log files.
'''

import google.generativeai as genai
from datetime import datetime
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")

def configure_api(model_name, system_prompt):
    """Configures the generative AI client.
    Args:
        model_name (str): The name of the model to use.
        system_prompt (str): The system prompt to use for the model.
    Returns:
        client: The configured generative AI client.
    """
    genai.configure(api_key=API_KEY)
    return genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)

def rate_limited_api_call(client, user_prompt, call_count, start_time, log_folder, max_calls=10, interval=69):
    """Handles API calls with rate limiting.
    Args:
        client: The generative AI client.
        user_prompt (str): The user prompt for the API call.
        call_count (int): Number of API calls made.
        start_time (float): Start time of the process.
        log_folder (str): Folder to save logs.
        max_calls (int): Maximum number of calls allowed in the interval.
        interval (int): Time interval in seconds for rate limiting.
    Returns:
        tuple: The API response, updated call count, and start time.
    """
    if call_count >= max_calls:
        elapsed_time = time.time() - start_time
        if elapsed_time < interval:
            time.sleep(interval - elapsed_time)
        call_count = 0
        start_time = time.time()

    response = client.generate_content(user_prompt)
    call_count += 1

    # Save response to log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_file_path = os.path.join(log_folder, f"api_call_{timestamp}.json")
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        json.dump(response.to_dict(), log_file, ensure_ascii=False, indent=4)

    return response, call_count, start_time