"""
Gemini-based email classifier.
"""
import json
from js import fetch, Object, console, JSON
from pyodide.ffi import to_js as _to_js

from config import get_classification_prompt, CLASSIFICATION_TAGS, GEMINI_API_URL
from utils import strip_html


def to_js(obj):
    return _to_js(obj, dict_converter=Object.fromEntries)


def js_to_py(js_obj):
    """Convert JS object to Python dict via JSON serialization."""
    return json.loads(JSON.stringify(js_obj))


async def classify_email(api_key: str, subject: str, body: str) -> dict:
    """
    Classify an email using Gemini 2.5 Flash.
    Returns: {
        "classification": str,
        "confidence": float,
        "reason": str,
        "token_usage": {"input_tokens": int, "output_tokens": int, "total_tokens": int} | None
    }
    """
    system_prompt = get_classification_prompt()

    # Strip HTML from body (MS Graph returns HTML content)
    clean_body = strip_html(body)

    # Log body lengths for debugging
    console.log(
        f"[Classification] Raw body length: {len(body)}, Clean body length: {len(clean_body)}, Truncated to: {min(len(clean_body), 5000)}")

    user_prompt = f"""Please classify the following email:

SUBJECT: {subject}

BODY:
{clean_body[:5000]}"""  # Truncate body to ~5k chars to avoid token limits

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\n---\n\n{user_prompt}"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,  # Low temperature for consistent classification
            "maxOutputTokens": 256,
        }
    }

    url = f"{GEMINI_API_URL}?key={api_key}"

    response = await fetch(
        url,
        to_js({
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(payload),
        })
    )

    if not response.ok:
        error_text = await response.text()
        console.error(f"Gemini API error: {response.status} - {error_text}")
        return {
            "classification": "general",
            "confidence": 0.0,
            "reason": f"Classification failed: {response.status}",
            "token_usage": None,
        }

    js_data = await response.json()
    data = js_to_py(js_data)

    # Extract token usage from response
    usage_metadata = data.get("usageMetadata", {})
    token_usage = None
    if usage_metadata:
        token_usage = {
            "input_tokens": usage_metadata.get("promptTokenCount", 0),
            "output_tokens": usage_metadata.get("candidatesTokenCount", 0),
            "total_tokens": usage_metadata.get("totalTokenCount", 0),
        }
        console.log(
            f"[Gemini] Token usage - Input: {token_usage['input_tokens']}, Output: {token_usage['output_tokens']}, Total: {token_usage['total_tokens']}")

    try:
        # Extract the text response safely
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates in response")

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise ValueError("No parts in response")

        text_response = parts[0].get("text", "")
        console.log(f"Gemini raw response: {text_response[:200]}...")

        # Clean up potential markdown code blocks
        text_response = text_response.strip()
        if text_response.startswith("```"):
            lines = text_response.split("\n")
            # Handle both ```json and ``` variants
            text_response = "\n".join(
                lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        # Try to find JSON in the response
        if not text_response.startswith("{"):
            # Try to find JSON object in the text
            start = text_response.find("{")
            end = text_response.rfind("}") + 1
            if start != -1 and end > start:
                text_response = text_response[start:end]

        console.log(f"Parsing JSON: {text_response[:100]}...")
        result = json.loads(text_response)

        # Validate the classification
        valid_tags = [tag["name"] for tag in CLASSIFICATION_TAGS]
        if result.get("classification") not in valid_tags:
            result["classification"] = "general"
            result["confidence"] = max(
                0.3, result.get("confidence", 0.5) * 0.5)
            result["reason"] = f"Invalid tag corrected to general. Original: {result.get('reason', 'N/A')}"

        return {
            "classification": result.get("classification", "general"),
            "confidence": float(result.get("confidence", 0.5)),
            "reason": result.get("reason", "No reason provided"),
            "token_usage": token_usage,
        }

    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as e:
        console.error(f"Failed to parse Gemini response: {e}")
        return {
            "classification": "general",
            "confidence": 0.0,
            "token_usage": token_usage,
            "reason": f"Failed to parse response: {str(e)}",
        }
