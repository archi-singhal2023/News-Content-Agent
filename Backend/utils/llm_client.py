import os
import json
import hashlib
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GROQ_API_KEY, MODEL_FAST, MODEL_SMART, CACHE_DIR

client = Groq(api_key=GROQ_API_KEY)
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(model, prompt, system):
    raw = f"{model}::{system}::{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest() + ".json"


def _read_cache(key):
    path = os.path.join(CACHE_DIR, key)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)["response"]
    return None


def _write_cache(key, response):
    path = os.path.join(CACHE_DIR, key)
    with open(path, "w") as f:
        json.dump({"response": response}, f)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=20))
def _call_groq(model, system, prompt, temperature, json_mode=False):
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


def call_llm(prompt, system="You are a helpful, precise research assistant.",
             fast=False, temperature=0.3, use_cache=True, json_mode=False):
    model = MODEL_FAST if fast else MODEL_SMART
    key = _cache_key(model, prompt, system)

    if use_cache:
        cached = _read_cache(key)
        if cached is not None:
            return cached

    result = _call_groq(model, system, prompt, temperature, json_mode=json_mode)

    if use_cache:
        _write_cache(key, result)

    return result

def call_llm_json(prompt: str, system: str, fast: bool = False, temperature: float = 0.2) -> dict:
    """
    Calls the LLM with json_mode enabled and returns an already-parsed dict.
    Handles the "model added extra text around the JSON" edge case automatically,
    so callers don't need to repeat this parsing logic themselves.

    Returns an empty dict {} if parsing fails completely, with the raw text
    included under "_raw_response" for debugging.
    """
    import json
    import re

    raw_response = call_llm(
        prompt=prompt,
        system=system,
        fast=fast,
        temperature=temperature,
        json_mode=True,
    )

    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"_raw_response": raw_response}
    
if __name__ == "__main__":
    test_response = call_llm(
        prompt="Say 'API connection successful' and nothing else.",
        fast=True,
        use_cache=False,
    )
    print(test_response)