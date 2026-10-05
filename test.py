"""Verify the Groq API key stored in the project .env file."""

from pathlib import Path

import httpx
from dotenv import dotenv_values


ENV_FILE = Path(__file__).resolve().parent / ".env"
MODELS_URL = "https://api.groq.com/openai/v1/models"


def main() -> int:
    api_key = str(dotenv_values(ENV_FILE, interpolate=False).get("GROQ_API_KEY") or "").strip()

    if not api_key:
        print(f"ERROR: GROQ_API_KEY is missing from {ENV_FILE}")
        return 1

    try:
        response = httpx.get(
            MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )
    except httpx.RequestError as error:
        print(f"ERROR: Could not reach Groq: {error}")
        return 2

    if response.status_code == 200:
        models = response.json().get("data", [])
        print("SUCCESS: The Groq API key is valid.")
        print(f"Groq returned {len(models)} available model(s).")
        return 0

    if response.status_code == 401:
        print("FAILED: Groq rejected the API key (HTTP 401).")
        return 3

    if response.status_code == 403:
        print("FAILED: The key was recognized but does not have permission (HTTP 403).")
        return 4

    if response.status_code == 429:
        print("REACHED GROQ: The request was rate-limited (HTTP 429).")
        return 5

    print(f"FAILED: Groq returned unexpected HTTP status {response.status_code}.")
    return 6


if __name__ == "__main__":
    raise SystemExit(main())
