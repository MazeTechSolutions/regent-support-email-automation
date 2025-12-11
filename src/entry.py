"""
Regent Support Email Automation Worker
Handles MS Graph webhooks, classifies emails using Gemini, stores in D1.
"""
import json
from urllib.parse import urlparse, parse_qs

from js import console, Object, JSON
from pyodide.ffi import to_js as _to_js
from workers import Response, WorkerEntrypoint

from msgraph import (
    get_access_token,
    get_email_by_id,
    apply_category_to_email,
    create_subscription,
    list_subscriptions,
    delete_subscription,
    renew_subscription,
)
from classifier import classify_email
from presidio import mask_email_content, get_presidio_config
from database import (
    init_db,
    email_exists,
    save_email,
    save_llm_usage,
    get_recent_emails,
    get_classification_stats,
    get_emails_by_conversation,
    get_conversation_stats,
    get_llm_usage_stats,
)


def to_js(obj):
    return _to_js(obj, dict_converter=Object.fromEntries)


def js_to_py(js_obj):
    """Convert JS object to Python dict via JSON serialization."""
    return json.loads(JSON.stringify(js_obj))


class Default(WorkerEntrypoint):

    async def fetch(self, request):
        url = urlparse(request.url)
        path = url.path
        method = request.method

        # Health check
        if path == "/" and method == "GET":
            return Response.json(to_js({
                "status": "ok",
                "service": "regent-support-email-automation",
            }))

        # MS Graph webhook validation (can come as GET or POST with validationToken)
        if path == "/webhook":
            params = parse_qs(url.query)
            validation_token = params.get("validationToken", [None])[0]
            if validation_token:
                console.log(f"Webhook validation request received ({method})")
                return Response(validation_token)

            # If no validation token and it's GET, return error
            if method == "GET":
                return Response("Missing validationToken", status=400)

            # POST without validation token = actual notification
            if method == "POST":
                return await self._handle_webhook_notification(request)

        # Manual subscription management endpoints
        if path == "/subscriptions" and method == "GET":
            return await self._list_subscriptions()

        if path == "/subscriptions" and method == "POST":
            return await self._create_subscription(request)

        if path == "/subscriptions" and method == "DELETE":
            return await self._delete_subscription(request)

        # Stats and recent emails
        if path == "/stats" and method == "GET":
            return await self._get_stats()

        if path == "/emails" and method == "GET":
            return await self._get_recent_emails()

        # Conversation endpoints
        if path == "/conversations" and method == "GET":
            return await self._get_conversation_stats()

        if path.startswith("/conversation/") and method == "GET":
            conversation_id = path[14:]  # Remove "/conversation/" prefix
            return await self._get_conversation(conversation_id)

        # Init DB (one-time setup)
        if path == "/init-db" and method == "POST":
            return await self._init_database()

        # Presidio config status
        if path == "/presidio-config" and method == "GET":
            return Response.json(to_js({"presidio": get_presidio_config()}))

        # LLM usage stats
        if path == "/llm-usage" and method == "GET":
            return await self._get_llm_usage()

        return Response("Not Found", status=404)

    async def _handle_webhook_notification(self, request):
        """Process incoming webhook notification from MS Graph."""
        try:
            # Get raw text and parse as JSON to ensure pure Python objects
            raw_body = await request.text()
            body = json.loads(raw_body)

            # Get notifications from body (pure Python dict now)
            notifications = body.get("value", [])
            console.log(
                f"Webhook received: {len(notifications)} notifications")

            # Validate client state
            expected_state = str(self.env.WEBHOOK_VALIDATION_TOKEN)

            # Process each notification
            for i in range(len(notifications)):
                notification = notifications[i]

                # Verify client state
                notification_state = notification.get("clientState", "")
                if notification_state != expected_state:
                    console.warn(f"Invalid client state in notification {i}")
                    continue

                change_type = notification.get("changeType", "")
                if change_type != "created":
                    console.log(
                        f"Skipping non-created notification: {change_type}")
                    continue

                resource = notification.get("resource", "")
                console.log(f"Processing resource: {resource}")

                # Extract message ID from resource path
                # Format: users/{email}/mailFolders/inbox/messages/{message-id}
                parts = resource.split("/")
                message_id = None
                for j in range(len(parts)):
                    if parts[j].lower() == "messages" and j + 1 < len(parts):
                        message_id = parts[j + 1]
                        break

                if message_id:
                    console.log(f"Processing message: {message_id[:50]}...")
                    await self._process_email(message_id)
                else:
                    console.warn(
                        f"Could not extract message ID from resource: {resource}")

            # MS Graph expects 202 Accepted
            return Response("", status=202)

        except Exception as e:
            console.error(f"Webhook processing error: {e}")
            # Still return 202 to prevent retries
            return Response("", status=202)

    async def _process_email(self, message_id: str):
        """Fetch, classify, tag, and store an email."""
        try:
            db = self.env.DB

            # Check if already processed
            if await email_exists(db, message_id):
                console.log(f"Email {message_id} already processed, skipping")
                return

            # Get access token
            access_token = await get_access_token(
                self.env.MS_TENANT_ID,
                self.env.MS_CLIENT_ID,
                self.env.MS_CLIENT_SECRET,
            )

            # Fetch email details
            user_email = str(self.env.MS_USER_EMAIL)
            email = await get_email_by_id(access_token, user_email, message_id)

            console.log(
                f"Processing email: {email.get('subject', 'No subject')}")
            console.log(
                f"Email data: from={email.get('from_address')}, received={email.get('received_datetime')}")

            # Mask PII before sending to LLM (soft fail - uses original if masking fails)
            masked = await mask_email_content(
                subject=email.get("subject", ""),
                body=email.get("body_content", ""),
                from_name=email.get("from_name", ""),
                from_address=email.get("from_address", ""),
            )

            if masked["success"] and masked["total_entities_masked"] > 0:
                console.log(
                    f"PII masked for classification: {masked['total_entities_masked']} entities")

            # Classify the email using masked content (protects PII from LLM)
            classification_result = await classify_email(
                self.env.GEMINI_API_KEY,
                masked["subject"],
                masked["body"],
            )

            classification = classification_result.get(
                "classification", "general")
            confidence = classification_result.get("confidence", 0)
            console.log(f"Classification: {classification} ({confidence})")

            # Apply category to email in Outlook (optional - may fail if no Mail.ReadWrite permission)
            try:
                category_name = classification.replace('-', ' ').title()
                console.log(
                    f"Applying category '{category_name}' to email {message_id[:20]}...")
                success = await apply_category_to_email(access_token, user_email, message_id, category_name)
                if success:
                    console.log(
                        f"Category '{category_name}' applied successfully")
                else:
                    console.warn(
                        f"Failed to apply category '{category_name}' - check Mail.ReadWrite permission")
            except Exception as cat_err:
                console.error(
                    f"Error applying category '{category_name}': {cat_err}")

            # Save to database (include full body text for reference)
            reason = classification_result.get("reason", "") or "No reason"
            email_id = await save_email(
                db,
                message_id=message_id,
                subject=email.get("subject", "") or "(No subject)",
                snippet=(email.get("body_preview", "") or "")[:500],
                from_address=email.get("from_address", "") or "",
                from_name=email.get("from_name", "") or "",
                classification=classification,
                confidence=float(confidence),
                reason=reason,
                received_at=email.get("received_datetime", "") or "",
                conversation_id=email.get("conversation_id", "") or "",
                # Store cleaned body text (truncated)
                body_text=masked["body"][:10000],
            )

            # Save token usage if available
            token_usage = classification_result.get("token_usage")
            if token_usage and email_id:
                await save_llm_usage(
                    db,
                    email_id=email_id,
                    model="gemini-2.5-flash",
                    operation="classification",
                    input_tokens=token_usage.get("input_tokens", 0),
                    output_tokens=token_usage.get("output_tokens", 0),
                    total_tokens=token_usage.get("total_tokens", 0),
                )

            console.log(f"Email {message_id} processed successfully")

        except Exception as e:
            console.error(f"Error processing email {message_id}: {e}")

    async def _init_database(self):
        """Initialize the database schema."""
        try:
            await init_db(self.env.DB)
            return Response.json(to_js({"status": "ok", "message": "Database initialized"}))
        except Exception as e:
            return Response.json(to_js({"status": "error", "message": str(e)}), status=500)

    async def _list_subscriptions(self):
        """List active MS Graph subscriptions."""
        try:
            access_token = await get_access_token(
                self.env.MS_TENANT_ID,
                self.env.MS_CLIENT_ID,
                self.env.MS_CLIENT_SECRET,
            )
            subscriptions = await list_subscriptions(access_token)
            return Response.json(to_js({"subscriptions": subscriptions}))
        except Exception as e:
            return Response.json(to_js({"error": str(e)}), status=500)

    async def _create_subscription(self, request):
        """Create a new MS Graph webhook subscription."""
        try:
            # Get the worker URL from the request or body
            js_body = await request.json()
            body = js_to_py(js_body)
            webhook_url = body.get("webhook_url")

            if not webhook_url:
                return Response.json(to_js({
                    "error": "webhook_url required in body"
                }), status=400)

            access_token = await get_access_token(
                self.env.MS_TENANT_ID,
                self.env.MS_CLIENT_ID,
                self.env.MS_CLIENT_SECRET,
            )

            subscription = await create_subscription(
                access_token,
                self.env.MS_USER_EMAIL,
                webhook_url,
                self.env.WEBHOOK_VALIDATION_TOKEN,
            )

            return Response.json(to_js({
                "status": "ok",
                "subscription": subscription,
                "note": "Save the subscription ID - needed to delete/renew"
            }))

        except Exception as e:
            return Response.json(to_js({"error": str(e)}), status=500)

    async def _delete_subscription(self, request):
        """Delete an MS Graph webhook subscription."""
        try:
            js_body = await request.json()
            body = js_to_py(js_body)
            subscription_id = body.get("subscription_id")

            if not subscription_id:
                return Response.json(to_js({
                    "error": "subscription_id required in body"
                }), status=400)

            access_token = await get_access_token(
                self.env.MS_TENANT_ID,
                self.env.MS_CLIENT_ID,
                self.env.MS_CLIENT_SECRET,
            )

            success = await delete_subscription(access_token, subscription_id)

            return Response.json(to_js({
                "status": "ok" if success else "failed",
                "deleted": subscription_id,
            }))

        except Exception as e:
            return Response.json(to_js({"error": str(e)}), status=500)

    async def _get_stats(self):
        """Get classification statistics."""
        try:
            stats = await get_classification_stats(self.env.DB)
            return Response.json(to_js({"stats": stats}))
        except Exception as e:
            return Response.json(to_js({"error": str(e)}), status=500)

    async def _get_recent_emails(self):
        """Get recent processed emails."""
        try:
            emails = await get_recent_emails(self.env.DB, 50)
            return Response.json(to_js({"emails": emails}))
        except Exception as e:
            return Response.json(to_js({"error": str(e)}), status=500)

    async def _get_conversation_stats(self):
        """Get conversation statistics."""
        try:
            stats = await get_conversation_stats(self.env.DB)
            return Response.json(to_js({"conversation_stats": stats}))
        except Exception as e:
            return Response.json(to_js({"error": str(e)}), status=500)

    async def _get_conversation(self, conversation_id: str):
        """Get all emails in a conversation."""
        try:
            emails = await get_emails_by_conversation(self.env.DB, conversation_id)
            return Response.json(to_js({"conversation_id": conversation_id, "emails": emails}))
        except Exception as e:
            return Response.json(to_js({"error": str(e)}), status=500)

    async def _get_llm_usage(self):
        """Get LLM token usage statistics."""
        try:
            stats = await get_llm_usage_stats(self.env.DB)
            return Response.json(to_js(stats))
        except Exception as e:
            return Response.json(to_js({"error": str(e)}), status=500)

    async def scheduled(self, event):
        """
        Cron trigger handler - renews MS Graph subscriptions before they expire.
        Runs daily to ensure subscriptions stay active (they expire after ~3 days).
        """
        console.log("Scheduled task: Renewing MS Graph subscriptions...")

        try:
            access_token = await get_access_token(
                self.env.MS_TENANT_ID,
                self.env.MS_CLIENT_ID,
                self.env.MS_CLIENT_SECRET,
            )

            # Get all active subscriptions
            subscriptions = await list_subscriptions(access_token)
            console.log(f"Found {len(subscriptions)} subscription(s) to renew")

            renewed_count = 0
            for sub in subscriptions:
                sub_id = sub.get("id")
                if sub_id:
                    try:
                        result = await renew_subscription(access_token, sub_id)
                        console.log(
                            f"Renewed subscription {sub_id[:20]}... - expires {result.get('expiration', 'unknown')}")
                        renewed_count += 1
                    except Exception as e:
                        console.error(
                            f"Failed to renew subscription {sub_id[:20]}...: {e}")

            console.log(
                f"Subscription renewal complete: {renewed_count}/{len(subscriptions)} renewed")

        except Exception as e:
            console.error(f"Scheduled subscription renewal failed: {e}")
