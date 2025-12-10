#!/usr/bin/env python3
"""
Local script to create MS Graph webhook subscription for debugging.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
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

import httpx


async def get_access_token():
    """Get OAuth2 access token."""
    tenant_id = os.environ["MS_TENANT_ID"]
    client_id = os.environ["MS_CLIENT_ID"]
    client_secret = os.environ["MS_CLIENT_SECRET"]
    
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def create_subscription(access_token: str):
    """Create webhook subscription."""
    user_email = os.environ["MS_USER_EMAIL"]
    webhook_url = "https://regent-support-email-automation.muhammad-56e.workers.dev/webhook"
    client_state = os.environ["WEBHOOK_VALIDATION_TOKEN"]
    
    # Expiration - 3 days from now (max for messages)
    expiration = datetime.now(timezone.utc) + timedelta(minutes=4230)
    expiration_str = expiration.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
    
    payload = {
        "changeType": "created",
        "notificationUrl": webhook_url,
        "resource": f"users/{user_email}/mailFolders/inbox/messages",
        "expirationDateTime": expiration_str,
        "clientState": client_state,
    }
    
    print("Creating subscription with payload:")
    print(f"  changeType: {payload['changeType']}")
    print(f"  notificationUrl: {payload['notificationUrl']}")
    print(f"  resource: {payload['resource']}")
    print(f"  expirationDateTime: {payload['expirationDateTime']}")
    print(f"  clientState: {payload['clientState'][:10]}...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://graph.microsoft.com/v1.0/subscriptions",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 201:
            data = response.json()
            print("\n SUCCESS!")
            print(f"Subscription ID: {data['id']}")
            print(f"Expires: {data['expirationDateTime']}")
            return data
        
        return None


async def list_subscriptions(access_token: str):
    """List existing subscriptions."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/subscriptions",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            return response.json().get("value", [])
        return []


async def main():
    print("=" * 60)
    print("MS Graph Subscription Creator (Debug)")
    print("=" * 60)
    
    print("\n[1] Getting access token...")
    token = await get_access_token()
    print("    OK")
    
    print("\n[2] Checking for existing subscriptions...")
    existing = await list_subscriptions(token)
    user_email = os.environ["MS_USER_EMAIL"]
    
    for sub in existing:
        if user_email in sub.get("resource", ""):
            print(f"    Found existing subscription: {sub['id']}")
            print(f"    Resource: {sub['resource']}")
            print(f"    Expires: {sub['expirationDateTime']}")
            print("\n    Subscription already exists. Delete it first if you want to recreate.")
            return
    
    print("    No existing subscription found.")
    
    print("\n[3] Creating subscription...")
    result = await create_subscription(token)
    
    if result:
        print("\n" + "=" * 60)
        print("SAVE THIS SUBSCRIPTION ID:")
        print(result['id'])
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
