# Regent Support Email Automation

Cloudflare Python Worker that classifies incoming Regent student support emails using Gemini, tags them in Outlook, and stores results in D1.

## Quick start
- Prereqs: Node 18+, `uv`, Cloudflare account, Gemini API key, Azure AD App with **Application** permissions `Mail.Read` (+ `Mail.ReadWrite` to apply categories).
- Install: `npm install` && `uv sync` (creates `.venv` when needed).
- Configure: copy `.env.example` → `.env`, then set Cloudflare secrets:
  - `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_USER_EMAIL`, `GEMINI_API_KEY`, `WEBHOOK_VALIDATION_TOKEN`
- Run locally: `npm run dev` (or `uv run pywrangler dev`).
- Tests: `npm test` (or `uv run pytest tests/ -v`).
- Deploy: `npm run deploy`.

## Database
- Create D1: `npx wrangler d1 create regent-support-emails` and set the ID in `wrangler.jsonc` (binding `DB`).
- Init schema after deploy: `curl -X POST https://<worker-url>/init-db`.

## Webhook registration
- Register: `curl -X POST https://<worker-url>/subscriptions -H "Content-Type: application/json" -d '{"webhook_url": "https://<worker-url>/webhook"}'`
- Save the `subscription_id`. Subscriptions expire after ~3 days; the Worker cron renews them daily at 06:00 UTC.
- List: `curl https://<worker-url>/subscriptions`
- Delete: `curl -X DELETE https://<worker-url>/subscriptions -H "Content-Type: application/json" -d '{"subscription_id":"<id>"}'`

## Endpoints
- `/` health; `/webhook` validation + notifications
- `/subscriptions` GET/POST/DELETE manage Graph subscriptions
- `/emails` recent processed emails; `/stats` classification counts
- `/init-db` create/ensure schema

## Notes
- D1 table `emails` stores message_id, subject/snippet, from, classification, confidence, reason, timestamps; duplicates are skipped by `message_id`.
- Gemini model: `gemini-2.5-flash` with prompt and tags in `src/config.py`.
- Logs: `npx wrangler tail --format=pretty`.
