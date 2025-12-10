"""
D1 Database operations.
"""
import json
from js import console, JSON


async def init_db(db):
    """Initialize the database schema if needed."""
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE NOT NULL,
            conversation_id TEXT,
            subject TEXT,
            snippet TEXT,
            from_address TEXT,
            from_name TEXT,
            classification TEXT,
            confidence REAL,
            reason TEXT,
            draft_reply TEXT,
            received_at TEXT,
            processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """).run()
    
    await db.prepare("""
        CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id)
    """).run()
    
    await db.prepare("""
        CREATE INDEX IF NOT EXISTS idx_emails_classification ON emails(classification)
    """).run()
    
    await db.prepare("""
        CREATE INDEX IF NOT EXISTS idx_emails_conversation_id ON emails(conversation_id)
    """).run()


async def email_exists(db, message_id: str) -> bool:
    """Check if an email has already been processed."""
    result = await db.prepare(
        "SELECT 1 FROM emails WHERE message_id = ?"
    ).bind(message_id).first()
    
    # Debug logging
    console.log(f"email_exists check - result type: {type(result)}, result: {result}")
    
    # D1 returns null/None if no row found
    if result is None:
        return False
    
    # Convert JS result to check if it's actually a row
    try:
        # Try to stringify to see if there's actual data
        result_str = JSON.stringify(result)
        console.log(f"email_exists - stringified: {result_str}")
        if result_str == "null" or result_str == "{}":
            return False
        return True
    except Exception as e:
        console.log(f"email_exists - error checking result: {e}")
        return False


async def save_email(
    db,
    message_id: str,
    subject: str,
    snippet: str,
    from_address: str,
    from_name: str,
    classification: str,
    confidence: float,
    reason: str,
    received_at: str,
    conversation_id: str = "",
    draft_reply: str = "",
) -> int:
    """Save a processed email to the database."""
    console.log(f"Saving email: {message_id[:50]}, subject={subject[:30]}, class={classification}")
    
    # Ensure all values are strings (not None/undefined)
    safe_draft = draft_reply if draft_reply else ""
    safe_subject = subject if subject else "(No subject)"
    safe_snippet = snippet if snippet else ""
    safe_from_addr = from_address if from_address else ""
    safe_from_name = from_name if from_name else ""
    safe_reason = reason if reason else ""
    safe_received = received_at if received_at else ""
    safe_conversation_id = conversation_id if conversation_id else ""
    
    result = await db.prepare("""
        INSERT INTO emails (
            message_id, conversation_id, subject, snippet, from_address, from_name,
            classification, confidence, reason, draft_reply, received_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """).bind(
        message_id,
        safe_conversation_id,
        safe_subject,
        safe_snippet,
        safe_from_addr,
        safe_from_name,
        classification,
        confidence,
        safe_reason,
        safe_draft,
        safe_received,
    ).run()
    
    console.log(f"Email saved successfully")
    return result.meta.last_row_id if result.meta else None


async def get_email_by_message_id(db, message_id: str) -> dict:
    """Get a processed email by its message ID."""
    result = await db.prepare(
        "SELECT * FROM emails WHERE message_id = ?"
    ).bind(message_id).first()
    
    if result:
        return {
            "id": result.id,
            "message_id": result.message_id,
            "conversation_id": result.conversation_id,
            "subject": result.subject,
            "snippet": result.snippet,
            "from_address": result.from_address,
            "from_name": result.from_name,
            "classification": result.classification,
            "confidence": result.confidence,
            "reason": result.reason,
            "draft_reply": result.draft_reply,
            "received_at": result.received_at,
            "processed_at": result.processed_at,
        }
    return None


async def get_recent_emails(db, limit: int = 50) -> list:
    """Get recent processed emails."""
    result = await db.prepare(
        "SELECT * FROM emails ORDER BY processed_at DESC LIMIT ?"
    ).bind(limit).all()
    
    emails = []
    if result.results:
        for row in result.results:
            emails.append({
                "id": row.id,
                "message_id": row.message_id,
                "conversation_id": row.conversation_id,
                "subject": row.subject,
                "classification": row.classification,
                "confidence": row.confidence,
                "received_at": row.received_at,
            })
    return emails


async def get_classification_stats(db) -> dict:
    """Get classification statistics."""
    result = await db.prepare("""
        SELECT classification, COUNT(*) as count
        FROM emails
        GROUP BY classification
    """).all()
    
    stats = {}
    if result.results:
        for row in result.results:
            stats[row.classification] = row.count
    return stats


async def get_emails_by_conversation(db, conversation_id: str) -> list:
    """Get all emails in a conversation thread."""
    result = await db.prepare(
        "SELECT * FROM emails WHERE conversation_id = ? ORDER BY received_at ASC"
    ).bind(conversation_id).all()
    
    emails = []
    if result.results:
        for row in result.results:
            emails.append({
                "id": row.id,
                "message_id": row.message_id,
                "conversation_id": row.conversation_id,
                "subject": row.subject,
                "snippet": row.snippet,
                "from_address": row.from_address,
                "from_name": row.from_name,
                "classification": row.classification,
                "confidence": row.confidence,
                "received_at": row.received_at,
            })
    return emails


async def get_conversation_stats(db) -> dict:
    """Get statistics grouped by conversation."""
    result = await db.prepare("""
        SELECT 
            conversation_id,
            COUNT(*) as message_count,
            GROUP_CONCAT(DISTINCT classification) as classifications
        FROM emails
        WHERE conversation_id IS NOT NULL AND conversation_id != ''
        GROUP BY conversation_id
        ORDER BY message_count DESC
        LIMIT 100
    """).all()
    
    stats = {
        "total_conversations": 0,
        "conversations": []
    }
    if result.results:
        stats["total_conversations"] = len(result.results)
        for row in result.results:
            stats["conversations"].append({
                "conversation_id": row.conversation_id,
                "message_count": row.message_count,
                "classifications": row.classifications.split(",") if row.classifications else [],
            })
    return stats
