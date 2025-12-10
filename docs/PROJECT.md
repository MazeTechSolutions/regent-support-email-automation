# Regent Support Email Automation

Automated email classification system for Regent University student support inbox using Cloudflare Workers (Python), Microsoft Graph API, Gemini LLM, and D1 database.

## Overview

This system automatically:
1. Receives webhook notifications when new emails arrive at `studentsupport@regent.ac.za`
2. Fetches email content from Microsoft Graph API
3. Classifies emails using Google Gemini LLM
4. Applies category tags to emails in Outlook (requires Mail.ReadWrite permission)
5. Stores classification results in Cloudflare D1 database

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  MS Graph API   │────▶│  CF Worker       │────▶│  Gemini API     │
│  (Webhooks)     │     │  (Python)        │     │  (Classification)│
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  D1 Database    │
                        │  (Storage)      │
                        └─────────────────┘
```

## Project Structure

```
├── src/
│   ├── entry.py        # Main worker entrypoint
│   ├── config.py       # Classification tags and LLM prompt
│   ├── classifier.py   # Gemini API integration
│   ├── database.py     # D1 database operations
│   └── msgraph.py      # Microsoft Graph API helpers
├── scripts/
│   ├── check_inbox.py          # Check inbox and D1 status
│   ├── test_webhook.py         # Simulate webhook notification
│   ├── test_gemini.py          # Test Gemini API directly
│   └── create_subscription.py  # Create MS Graph subscription
├── tests/
│   ├── test_classifier.py
│   ├── test_config.py
│   ├── test_database.py
│   └── test_webhook.py
├── .env.example        # Environment variables template
├── pyproject.toml      # Python dependencies
├── wrangler.jsonc      # Cloudflare Worker configuration
├── WEBHOOK_NOTES.txt   # Webhook registration details
└── package.json        # npm scripts
```

## Prerequisites

- [Node.js](https://nodejs.org/) (v18+)
- [uv](https://docs.astral.sh/uv/) - Python package manager
- Cloudflare account with Workers enabled
- Azure AD App Registration with MS Graph permissions
- Google Gemini API key

## Setup

### 1. Clone and Install Dependencies

```bash
git clone <repo-url>
cd regent-support-email-automation
npm install
uv sync
```

### 2. Create Environment File

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `MS_TENANT_ID` - Azure AD tenant ID
- `MS_CLIENT_ID` - Azure AD app client ID
- `MS_CLIENT_SECRET` - Azure AD app client secret
- `MS_USER_EMAIL` - Target mailbox (e.g., studentsupport@regent.ac.za)
- `GEMINI_API_KEY` - Google Gemini API key
- `WEBHOOK_VALIDATION_TOKEN` - Random string for webhook validation

### 3. Create D1 Database

```bash
npx wrangler d1 create regent-support-emails
```

Update `wrangler.jsonc` with the returned database ID.

### 4. Set Cloudflare Secrets

```bash
npx wrangler secret put MS_TENANT_ID
npx wrangler secret put MS_CLIENT_ID
npx wrangler secret put MS_CLIENT_SECRET
npx wrangler secret put MS_USER_EMAIL
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put WEBHOOK_VALIDATION_TOKEN
```

### 5. Deploy

```bash
npm run deploy
```

### 6. Initialize Database

```bash
curl -X POST https://<your-worker-url>/init-db
```

### 7. Register Webhook

```bash
uv run python scripts/create_subscription.py
```

Or via curl:
```bash
curl -X POST https://<your-worker-url>/subscriptions \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://<your-worker-url>/webhook"}'
```

**Important:** Save the subscription ID returned - needed to delete/renew.

## Azure AD App Requirements

Your Azure AD App needs these **Application** permissions (not Delegated):
- `Mail.Read` - Read emails
- `Mail.ReadWrite` - Apply categories to emails (optional but recommended)

Grant admin consent for these permissions in Azure Portal.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/webhook` | GET/POST | MS Graph webhook (validation & notifications) |
| `/subscriptions` | GET | List active subscriptions |
| `/subscriptions` | POST | Create new subscription |
| `/subscriptions` | DELETE | Delete subscription |
| `/emails` | GET | Get recent processed emails |
| `/stats` | GET | Get classification statistics |
| `/init-db` | POST | Initialize database schema |

## Classification Tags

Edit `src/config.py` to modify classification categories:

- `academic-results` - Queries about marks, grades, results
- `academic-exam` - Exam-specific issues (remarks, supplementary)
- `admin-transcript` - Transcript requests
- `admin-graduation` - Graduation inquiries
- `finance-payment` - Payment-related issues
- `finance-fees` - Fee statements, quotes
- `registration` - Enrollment, registration
- `technical-access` - Portal/LMS login issues
- `general` - General inquiries

## Development

### Run Locally

```bash
npm run dev
# or
uv run pywrangler dev
```

### Run Tests

```bash
npm test
# or
uv run pytest tests/ -v
```

### Check Status

```bash
uv run python scripts/check_inbox.py
```

## Managing Webhooks

### List Active Subscriptions
```bash
curl https://<your-worker-url>/subscriptions
```

### Delete Subscription (Pause Processing)
```bash
curl -X DELETE https://<your-worker-url>/subscriptions \
  -H "Content-Type: application/json" \
  -d '{"subscription_id": "<id>"}'
```

### Re-enable Processing
```bash
uv run python scripts/create_subscription.py
```

**Note:** MS Graph subscriptions expire after ~3 days and must be renewed.

## Troubleshooting

### Webhook Not Receiving Notifications
- Verify subscription is active: `GET /subscriptions`
- Check webhook URL is HTTPS and publicly accessible
- Ensure `WEBHOOK_VALIDATION_TOKEN` matches in secrets and subscription

### Classification Failing
- Check Gemini API quota at https://ai.google.dev/
- Verify `GEMINI_API_KEY` secret is set correctly
- Check worker logs: `npx wrangler tail`

### Category Not Applied to Emails
- Add `Mail.ReadWrite` permission in Azure AD
- Grant admin consent
- Redeploy worker

### D1 Errors
- Ensure database is initialized: `POST /init-db`
- Check database ID in `wrangler.jsonc` matches created database

## Monitoring

View real-time logs:
```bash
npx wrangler tail --format=pretty
```

Check processed emails:
```bash
curl https://<your-worker-url>/emails
```

Check classification stats:
```bash
curl https://<your-worker-url>/stats
```
