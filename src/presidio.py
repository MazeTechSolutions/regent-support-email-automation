"""
Presidio PII masking service.
Soft-fail design - if Presidio is unavailable, returns original text.
"""
import json
from js import fetch, Object, console, JSON
from pyodide.ffi import to_js as _to_js


def to_js(obj):
    return _to_js(obj, dict_converter=Object.fromEntries)


def js_to_py(js_obj):
    """Convert JS object to Python dict via JSON serialization."""
    return json.loads(JSON.stringify(js_obj))


# Presidio configuration
PRESIDIO_CONFIG = {
    "enabled": True,
    "analyzer_url": "https://analyzer-gqabp4wdwtvje.azurewebsites.net",
    "anonymizer_url": "https://webapp-gqabp4wdwtvje.azurewebsites.net",
    "timeout_ms": 10000,  # 10 second timeout
    "score_threshold": 0.7,
    "entities": ["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "ZA_ID_NUMBER"],
    "regent_domains": ["@regent.ac.za", "@myregent.ac.za"],
    # South African ID Number recognizer
    "za_id_recognizer": {
        "name": "South African ID Recognizer",
        "supported_language": "en",
        "patterns": [
            {
                "name": "ZA ID (strict)",
                "regex": r"\b\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{4}[01][89]\d\b",
                "score": 0.85
            }
        ],
        "context": ["id", "ID", "identity", "passport", "ID/Passport", "ID Number", "sa id"],
        "supported_entity": "ZA_ID_NUMBER"
    }
}


async def analyze_text(text: str) -> list:
    """
    Call Presidio analyzer to detect PII entities.
    Returns list of detected entities or empty list on failure.
    """
    if not PRESIDIO_CONFIG["enabled"]:
        return []
    
    try:
        url = f"{PRESIDIO_CONFIG['analyzer_url']}/analyze"
        
        payload = {
            "text": text,
            "language": "en",
            "entities": PRESIDIO_CONFIG["entities"],
            "score_threshold": PRESIDIO_CONFIG["score_threshold"],
            "ad_hoc_recognizers": [PRESIDIO_CONFIG["za_id_recognizer"]],
        }
        
        response = await fetch(
            url,
            to_js({
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload),
                "signal": None,  # Could add AbortController for timeout
            })
        )
        
        if not response.ok:
            console.warn(f"Presidio analyzer error: {response.status}")
            return []
        
        js_data = await response.json()
        return js_to_py(js_data)
    
    except Exception as e:
        console.warn(f"Presidio analyzer failed (soft fail): {e}")
        return []


def filter_regent_emails(text: str, analyzer_results: list) -> list:
    """Filter out Regent email addresses from masking."""
    filtered = []
    for result in analyzer_results:
        if result.get("entity_type") == "EMAIL_ADDRESS":
            email_text = text[result["start"]:result["end"]].lower()
            if any(domain in email_text for domain in PRESIDIO_CONFIG["regent_domains"]):
                continue  # Skip Regent emails
        filtered.append(result)
    return filtered


async def anonymize_text(text: str, analyzer_results: list) -> str:
    """
    Call Presidio anonymizer to mask detected PII.
    Returns masked text or original text on failure.
    """
    if not PRESIDIO_CONFIG["enabled"] or not analyzer_results:
        return text
    
    # Filter out Regent emails
    filtered_results = filter_regent_emails(text, analyzer_results)
    
    if not filtered_results:
        return text
    
    try:
        url = f"{PRESIDIO_CONFIG['anonymizer_url']}/anonymize"
        
        payload = {
            "text": text,
            "analyzer_results": filtered_results,
        }
        
        response = await fetch(
            url,
            to_js({
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload),
            })
        )
        
        if not response.ok:
            console.warn(f"Presidio anonymizer error: {response.status}")
            return text
        
        js_data = await response.json()
        data = js_to_py(js_data)
        return data.get("text", text)
    
    except Exception as e:
        console.warn(f"Presidio anonymizer failed (soft fail): {e}")
        return text


async def mask_pii(text: str) -> dict:
    """
    Main function to mask PII in text.
    Returns dict with masked text and metadata.
    Always succeeds (soft fail design).
    
    Returns:
        {
            "masked_text": str,  # Masked version (or original if failed)
            "original_text": str,  # Always the original
            "entities_found": int,  # Number of entities detected
            "entities_masked": int,  # Number actually masked (after filtering)
            "success": bool,  # Whether masking was performed
        }
    """
    result = {
        "masked_text": text,
        "original_text": text,
        "entities_found": 0,
        "entities_masked": 0,
        "success": False,
    }
    
    if not PRESIDIO_CONFIG["enabled"]:
        return result
    
    if not text or not text.strip():
        return result
    
    try:
        # Analyze
        analyzer_results = await analyze_text(text)
        result["entities_found"] = len(analyzer_results)
        
        if not analyzer_results:
            result["success"] = True  # No PII found is still a success
            return result
        
        # Filter and count
        filtered_results = filter_regent_emails(text, analyzer_results)
        result["entities_masked"] = len(filtered_results)
        
        # Anonymize
        masked_text = await anonymize_text(text, analyzer_results)
        result["masked_text"] = masked_text
        result["success"] = True
        
        if result["entities_masked"] > 0:
            console.log(f"PII masked: {result['entities_masked']} entities")
        
        return result
    
    except Exception as e:
        console.warn(f"PII masking failed (soft fail): {e}")
        return result


async def mask_email_content(subject: str, body: str, from_name: str = "", from_address: str = "") -> dict:
    """
    Mask PII in email content fields.
    Convenience function for email processing.
    
    Returns:
        {
            "subject": str,  # Masked subject
            "body": str,  # Masked body
            "from_name": str,  # Masked from name
            "from_address": str,  # Masked from address (preserves Regent emails)
            "original_subject": str,
            "original_body": str,
            "total_entities_found": int,
            "total_entities_masked": int,
            "success": bool,
        }
    """
    result = {
        "subject": subject,
        "body": body,
        "from_name": from_name,
        "from_address": from_address,
        "original_subject": subject,
        "original_body": body,
        "total_entities_found": 0,
        "total_entities_masked": 0,
        "success": False,
    }
    
    if not PRESIDIO_CONFIG["enabled"]:
        return result
    
    try:
        # Mask subject
        subject_result = await mask_pii(subject)
        result["subject"] = subject_result["masked_text"]
        result["total_entities_found"] += subject_result["entities_found"]
        result["total_entities_masked"] += subject_result["entities_masked"]
        
        # Mask body
        body_result = await mask_pii(body)
        result["body"] = body_result["masked_text"]
        result["total_entities_found"] += body_result["entities_found"]
        result["total_entities_masked"] += body_result["entities_masked"]
        
        # Mask from_name if provided
        if from_name:
            name_result = await mask_pii(from_name)
            result["from_name"] = name_result["masked_text"]
            result["total_entities_found"] += name_result["entities_found"]
            result["total_entities_masked"] += name_result["entities_masked"]
        
        # Mask from_address (will preserve Regent emails due to filter)
        if from_address:
            addr_result = await mask_pii(from_address)
            result["from_address"] = addr_result["masked_text"]
            result["total_entities_found"] += addr_result["entities_found"]
            result["total_entities_masked"] += addr_result["entities_masked"]
        
        result["success"] = True
        
        if result["total_entities_masked"] > 0:
            console.log(f"Email PII masked: {result['total_entities_masked']} entities in {result['total_entities_found']} detected")
        
        return result
    
    except Exception as e:
        console.warn(f"Email PII masking failed (soft fail): {e}")
        return result


def set_presidio_enabled(enabled: bool):
    """Enable or disable Presidio masking."""
    PRESIDIO_CONFIG["enabled"] = enabled


def set_presidio_urls(analyzer_url: str = None, anonymizer_url: str = None):
    """Update Presidio service URLs."""
    if analyzer_url:
        PRESIDIO_CONFIG["analyzer_url"] = analyzer_url
    if anonymizer_url:
        PRESIDIO_CONFIG["anonymizer_url"] = anonymizer_url


def set_score_threshold(threshold: float):
    """Set the minimum confidence score for PII detection."""
    PRESIDIO_CONFIG["score_threshold"] = threshold


def get_presidio_config() -> dict:
    """Get current Presidio configuration."""
    return PRESIDIO_CONFIG.copy()
