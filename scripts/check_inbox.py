#!/usr/bin/env python3
"""
Local script to check inbox emails and test MS Graph API connection.
Uses .env file for credentials.
"""
import asyncio
import os
import sys
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

try:
    import httpx
except ImportError:
    print("Please install httpx: pip install httpx")
    sys.exit(1)


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


async def get_recent_emails(access_token: str, limit: int = 10):
    """Get recent emails from inbox."""
    user_email = os.environ["MS_USER_EMAIL"]
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/mailFolders/inbox/messages"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"$top": limit, "$orderby": "receivedDateTime desc"},
        )
        response.raise_for_status()
        return response.json()


async def check_d1_emails():
    """Check what emails are stored in D1 via the worker."""
    worker_url = "https://regent-support-email-automation.muhammad-56e.workers.dev"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{worker_url}/emails")
        return response.json()


async def check_stats():
    """Check classification stats from D1."""
    worker_url = "https://regent-support-email-automation.muhammad-56e.workers.dev"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{worker_url}/stats")
        return response.json()


async def main():
    print("=" * 60)
    print("MS Graph Inbox Check")
    print("=" * 60)
    
    try:
        # Get access token
        print("\n[1] Getting access token...")
        token = await get_access_token()
        print("    OK - Token obtained")
        
        # Get recent emails
        print("\n[2] Fetching recent emails from inbox...")
        emails_data = await get_recent_emails(token, limit=10)
        emails = emails_data.get("value", [])
        
        print(f"    Found {len(emails)} emails in inbox:")
        print("-" * 60)
        for i, email in enumerate(emails, 1):
            subject = email.get("subject", "(no subject)")[:50]
            from_data = email.get("from", {}).get("emailAddress", {})
            from_addr = from_data.get("address", "unknown")
            received = email.get("receivedDateTime", "")[:19]
            categories = email.get("categories", [])
            
            print(f"    {i}. {subject}")
            print(f"       From: {from_addr}")
            print(f"       Received: {received}")
            if categories:
                print(f"       Categories: {', '.join(categories)}")
            print()
        
        # Check D1 database
        print("\n[3] Checking D1 database (processed emails)...")
        d1_emails = await check_d1_emails()
        stored = d1_emails.get("emails", [])
        print(f"    {len(stored)} emails processed and stored")
        
        if stored:
            print("-" * 60)
            for email in stored[:5]:
                print(f"    - {email.get('subject', '(no subject)')[:40]}")
                print(f"      Classification: {email.get('classification')} ({email.get('confidence', 0):.2f})")
        
        # Check stats
        print("\n[4] Classification statistics...")
        stats_data = await check_stats()
        stats = stats_data.get("stats", {})
        
        if stats:
            print("-" * 60)
            for tag, count in stats.items():
                print(f"    {tag}: {count}")
        else:
            print("    No stats yet (no emails processed)")
        
        print("\n" + "=" * 60)
        print("Done!")
        
    except httpx.HTTPStatusError as e:
        print(f"\nHTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
    except KeyError as e:
        print(f"\nMissing environment variable: {e}")
        print("Make sure .env file has all required variables")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(main())
