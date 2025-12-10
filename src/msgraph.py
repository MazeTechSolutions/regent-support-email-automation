"""
Microsoft Graph API helper functions.
"""
import json
from js import fetch, Object, console, JSON
from pyodide.ffi import to_js as _to_js

def to_js(obj):
    return _to_js(obj, dict_converter=Object.fromEntries)

def js_to_py(js_obj):
    """Convert JS object to Python dict via JSON serialization."""
    return json.loads(JSON.stringify(js_obj))

def safe_get(obj, *keys, default=None):
    """Safely get nested values from JS or Python objects."""
    current = obj
    for key in keys:
        try:
            if hasattr(current, 'get'):
                current = current.get(key, default)
            elif hasattr(current, key):
                current = getattr(current, key, default)
            elif isinstance(current, (list, tuple)) and isinstance(key, int):
                current = current[key] if len(current) > key else default
            elif hasattr(current, '__getitem__'):
                current = current[key]
            else:
                return default
            if current is None:
                return default
        except (KeyError, IndexError, TypeError, AttributeError):
            return default
    return current

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


async def get_access_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Get OAuth2 access token for MS Graph API using client credentials flow."""
    url = AUTH_URL.format(tenant_id=tenant_id)
    
    body = (
        f"client_id={client_id}"
        f"&client_secret={client_secret}"
        f"&scope=https://graph.microsoft.com/.default"
        f"&grant_type=client_credentials"
    )
    
    response = await fetch(
        url,
        to_js({
            "method": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
            },
            "body": body,
        })
    )
    
    if not response.ok:
        error_text = await response.text()
        raise Exception(f"Failed to get access token: {response.status} - {error_text}")
    
    js_data = await response.json()
    data = js_to_py(js_data)
    return data.get("access_token")


async def get_email_by_id(access_token: str, user_email: str, message_id: str) -> dict:
    """Fetch a specific email by ID."""
    url = f"{GRAPH_BASE_URL}/users/{user_email}/messages/{message_id}"
    
    response = await fetch(
        url,
        to_js({
            "method": "GET",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        })
    )
    
    if not response.ok:
        error_text = await response.text()
        raise Exception(f"Failed to get email: {response.status} - {error_text}")
    
    js_data = await response.json()
    data = js_to_py(js_data)
    
    from_data = data.get("from", {})
    from_email = from_data.get("emailAddress", {}) if from_data else {}
    body_data = data.get("body", {})
    
    return {
        "id": data.get("id", ""),
        "conversation_id": data.get("conversationId", ""),
        "subject": data.get("subject", ""),
        "body_preview": data.get("bodyPreview", ""),
        "body_content": body_data.get("content", "") if body_data else "",
        "from_address": from_email.get("address", "") if from_email else "",
        "from_name": from_email.get("name", "") if from_email else "",
        "received_datetime": data.get("receivedDateTime", ""),
        "categories": data.get("categories", []),
    }


async def apply_category_to_email(access_token: str, user_email: str, message_id: str, category: str) -> bool:
    """Apply a category/tag to an email in the inbox."""
    url = f"{GRAPH_BASE_URL}/users/{user_email}/messages/{message_id}"
    
    response = await fetch(
        url,
        to_js({
            "method": "PATCH",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            "body": json.dumps({"categories": [category]}),
        })
    )
    
    if not response.ok:
        error_text = await response.text()
        console.error(f"Failed to apply category: {response.status} - {error_text}")
        return False
    
    return True


async def create_subscription(
    access_token: str,
    user_email: str,
    webhook_url: str,
    client_state: str,
    expiration_minutes: int = 4230  # Max ~3 days for messages
) -> dict:
    """
    Create a webhook subscription for new emails.
    NOTE: Call this AFTER deployment to register the webhook.
    """
    from datetime import datetime, timedelta, timezone
    
    expiration = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
    expiration_str = expiration.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
    
    url = f"{GRAPH_BASE_URL}/subscriptions"
    
    payload = {
        "changeType": "created",
        "notificationUrl": webhook_url,
        "resource": f"users/{user_email}/mailFolders/inbox/messages",
        "expirationDateTime": expiration_str,
        "clientState": client_state,
    }
    
    response = await fetch(
        url,
        to_js({
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            "body": json.dumps(payload),
        })
    )
    
    if not response.ok:
        error_text = await response.text()
        raise Exception(f"Failed to create subscription: {response.status} - {error_text}")
    
    js_data = await response.json()
    data = js_to_py(js_data)
    return {
        "id": data.get("id", ""),
        "resource": data.get("resource", ""),
        "expiration": data.get("expirationDateTime", ""),
        "client_state": data.get("clientState", ""),
    }


async def renew_subscription(access_token: str, subscription_id: str, expiration_minutes: int = 4230) -> dict:
    """Renew an existing subscription."""
    from datetime import datetime, timedelta, timezone
    
    expiration = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
    expiration_str = expiration.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
    
    url = f"{GRAPH_BASE_URL}/subscriptions/{subscription_id}"
    
    payload = {"expirationDateTime": expiration_str}
    
    response = await fetch(
        url,
        to_js({
            "method": "PATCH",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            "body": json.dumps(payload),
        })
    )
    
    if not response.ok:
        error_text = await response.text()
        raise Exception(f"Failed to renew subscription: {response.status} - {error_text}")
    
    js_data = await response.json()
    data = js_to_py(js_data)
    return {
        "id": data.get("id", ""),
        "expiration": data.get("expirationDateTime", ""),
    }


async def delete_subscription(access_token: str, subscription_id: str) -> bool:
    """Delete a webhook subscription."""
    url = f"{GRAPH_BASE_URL}/subscriptions/{subscription_id}"
    
    response = await fetch(
        url,
        to_js({
            "method": "DELETE",
            "headers": {
                "Authorization": f"Bearer {access_token}",
            },
        })
    )
    
    return response.ok


async def list_subscriptions(access_token: str) -> list:
    """List all active subscriptions."""
    url = f"{GRAPH_BASE_URL}/subscriptions"
    
    response = await fetch(
        url,
        to_js({
            "method": "GET",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        })
    )
    
    if not response.ok:
        error_text = await response.text()
        raise Exception(f"Failed to list subscriptions: {response.status} - {error_text}")
    
    js_data = await response.json()
    data = js_to_py(js_data)
    subscriptions = []
    for sub in data.get("value", []):
        subscriptions.append({
            "id": sub.get("id", ""),
            "resource": sub.get("resource", ""),
            "expiration": sub.get("expirationDateTime", ""),
        })
    return subscriptions
