# Regent Support Email Automation

Automated email classification system for Regent University student support inbox using Cloudflare Workers (Python), Microsoft Graph API, Gemini LLM, and D1 database.

## Overview

This system automatically:
1. Receives webhook notifications when new emails arrive at `studentsupport@regent.ac.za`
2. Fetches email content from Microsoft Graph API
3. Classifies emails using Google Gemini LLM
4. Applies category tags to emails in Outlook (requires Mail.ReadWrite permission)
5. Stores classification results in Cloudflare D1 database

### Email processing flow
- `/webhook` validates the Graph `validationToken` (GET/POST). Notifications must include the matching `clientState` (`WEBHOOK_VALIDATION_TOKEN`).
- For each `created` notification, extracts the `message_id` and skips processing if it already exists in D1.
- Fetches the email via MS Graph using client credentials (`MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_USER_EMAIL`).
- Classifies `subject + bodyPreview` with Gemini (`GEMINI_MODEL` in `src/config.py`, default `gemini-2.5-flash-lite`) using the prompt in `src/config.py`.
- Applies an Outlook category using the title-cased classification (best-effort; logs a warning if `Mail.ReadWrite` is missing).
- Persists the record to D1 with subject/snippet/from/reason/confidence and timestamps.
- Returns `202 Accepted` even on errors to prevent Graph retries (errors are logged).

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

## Runtime configuration (wrangler.jsonc)
- `main`: `src/entry.py` (Python Workers, `compatibility_date` `2025-12-09`, `python_workers` flag)
- D1 binding `DB` → `regent-support-emails` (remote enabled)
- Cron trigger `0 6 * * *` renews MS Graph subscriptions daily (~3-day expiry)
- Custom domain route: `support-classifier.regent.business`
- Secrets expected at deploy time: `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_USER_EMAIL`, `GEMINI_API_KEY`, `WEBHOOK_VALIDATION_TOKEN`

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
See `WEBHOOK_NOTES.txt` for the latest deployed URLs and subscription IDs.

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
| `/conversations` | GET | Get conversation statistics (grouped by thread) |
| `/conversation/{id}` | GET | Get all emails in a specific conversation thread |
| `/init-db` | POST | Initialize database schema |
| cron | scheduled | Daily renewal of MS Graph subscriptions |

## Classification Tags

Edit `src/config.py` to modify classification categories:

- `academic-results` - Marks, missing results, blocked results
- `academic-exam` - Exam issues, supplementaries, Aegrotat/sick exams
- `academic-assignment` - Assignment submissions, extensions, marking feedback
- `admin-transcript` - Academic records, transcript holds/requests
- `admin-graduation` - Graduation ceremonies, certificates, timelines
- `finance-payment` - POP, refunds, allocations, blocked for payment
- `finance-fees` - Statements, invoices, quotes, balances
- `registration` - Enrolment, add/repeat modules, registration forms
- `technical-proctoring` - SMOWL/in-exam outages (camera, C-LS-1001, kicked out)
- `technical-access` - Login/access issues not during an exam
- `general-inquiry` - Timetables, module codes, calendar dates, pass marks
- `complaint-escalation` - Formal grievances or repeated unresolved issues
- (Fallback) `general` is used by the Worker if a tag is invalid/unclear

## Data model (D1)
- Table `emails` (created by `/init-db` or `init_db` in `database.py`)
  - `message_id` (unique), `conversation_id`, `subject`, `snippet`, `from_address`, `from_name`
  - `classification`, `confidence`, `reason`, `draft_reply`
  - `received_at`, `processed_at`, `created_at`
- Indexes: `idx_emails_message_id`, `idx_emails_classification`, `idx_emails_conversation_id`
- Duplicate guard: Worker checks `email_exists` before reprocessing
- Conversation tracking: `conversation_id` from MS Graph groups related emails in a thread

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

### Auto-renewal
- Subscriptions expire after ~3 days; the Worker cron renews them daily at 06:00 UTC.
- Check logs (`npx wrangler tail`) to confirm renewals.

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

**Note:** MS Graph subscriptions expire after ~3 days; auto-renew runs daily via cron, but re-register if cron is disabled or credentials change.

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
