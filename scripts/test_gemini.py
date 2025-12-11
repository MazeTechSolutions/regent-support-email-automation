#!/usr/bin/env python3
"""
Test Gemini classifier directly.
"""
import httpx
import asyncio
import os
import json
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value


async def test_gemini():
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    # Simple test prompt
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": """Classify this email:
Subject: Need my transcript
Body: Please send me my academic transcript for my job application.

Respond in JSON format: {"classification": "admin-transcript", "confidence": 0.95, "reason": "Requesting transcript"}"""}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 256,
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            print(f"Response: {text}")
        else:
            print(f"Error: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_gemini())
