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
def _call_groq(model, system, prompt, temperature):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content


def call_llm(prompt, system="You are a helpful, precise research assistant.",
             fast=False, temperature=0.3, use_cache=True):
    model = MODEL_FAST if fast else MODEL_SMART
    key = _cache_key(model, prompt, system)

    if use_cache:
        cached = _read_cache(key)
        if cached is not None:
            return cached

    result = _call_groq(model, system, prompt, temperature)

    if use_cache:
        _write_cache(key, result)

    return result


if __name__ == "__main__":
    test_response = call_llm(
        prompt="Say 'API connection successful' and nothing else.",
        fast=True,
        use_cache=False,
    )
    print(test_response)