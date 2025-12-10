#!/usr/bin/env python3
"""
Test script to simulate MS Graph webhook notification.
"""
import asyncio
import os
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
    
    async with httpx.AsyncClient() as client:
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


async def get_latest_email(access_token: str):
    """Get the most recent email from inbox."""
    user_email = os.environ["MS_USER_EMAIL"]
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/mailFolders/inbox/messages"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"$top": 1, "$orderby": "receivedDateTime desc"},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("value"):
            return data["value"][0]
        return None


async def simulate_webhook(message_id: str):
    """Send a simulated webhook notification to our worker."""
    worker_url = "https://regent-support-email-automation.muhammad-56e.workers.dev/webhook"
    client_state = os.environ["WEBHOOK_VALIDATION_TOKEN"]
    user_email = os.environ["MS_USER_EMAIL"]
    
    # Format like MS Graph notification
    notification = {
        "value": [
            {
                "subscriptionId": "c43f7c5f-cf96-4448-92b3-5f609b742e0a",
                "subscriptionExpirationDateTime": "2025-12-12T09:04:34Z",
                "changeType": "created",
                "resource": f"users/{user_email}/mailFolders/inbox/messages/{message_id}",
                "resourceData": {
                    "@odata.type": "#Microsoft.Graph.Message",
                    "id": message_id
                },
                "clientState": client_state,
                "tenantId": os.environ["MS_TENANT_ID"]
            }
        ]
    }
    
    print(f"\nSending simulated webhook notification...")
    print(f"Message ID: {message_id}")
    print(f"Resource: {notification['value'][0]['resource']}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            worker_url,
            json=notification,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")
        return response.status_code == 202


async def main():
    print("=" * 60)
    print("Webhook Notification Test")
    print("=" * 60)
    
    print("\n[1] Getting access token...")
    token = await get_access_token()
    print("    OK")
    
    print("\n[2] Getting latest email from inbox...")
    email = await get_latest_email(token)
    if not email:
        print("    No emails found!")
        return
    
    print(f"    Found: {email.get('subject', '(no subject)')[:50]}")
    print(f"    ID: {email['id']}")
    
    print("\n[3] Simulating webhook notification...")
    success = await simulate_webhook(email["id"])
    
    if success:
        print("\n[4] Checking if email was processed...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://regent-support-email-automation.muhammad-56e.workers.dev/emails"
            )
            data = response.json()
            emails = data.get("emails", [])
            print(f"    Processed emails in D1: {len(emails)}")
            if emails:
                for e in emails[:3]:
                    print(f"    - {e.get('subject', '(no subject)')[:40]}: {e.get('classification')}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
