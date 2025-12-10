"""Tests for database operations (mock-based)."""
import sys
import os
from unittest.mock import MagicMock

# Mock the js module before importing database (only available in CF Workers runtime)
mock_console = MagicMock()
mock_console.log = MagicMock()
mock_console.warn = MagicMock()
mock_console.error = MagicMock()

mock_json = MagicMock()
mock_json.stringify = MagicMock(return_value='{"test": true}')

sys.modules['js'] = MagicMock()
sys.modules['js'].console = mock_console
sys.modules['js'].JSON = mock_json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from database import (
    email_exists,
    save_email,
    get_email_by_message_id,
    get_recent_emails,
    get_classification_stats,
    get_emails_by_conversation,
    get_conversation_stats,
)


class MockDB:
    """Mock D1 database for testing."""
    
    def __init__(self):
        self.data = {}
        self._last_id = 0
    
    async def exec(self, query):
        return MagicMock()
    
    def prepare(self, query):
        mock = MagicMock()
        mock.bind = MagicMock(return_value=mock)
        
        # email_exists query
        if "SELECT 1 FROM emails WHERE message_id" in query:
            async def first():
                return self.data.get("exists_check")
            mock.first = first
        
        # save_email query
        elif "INSERT INTO emails" in query:
            async def run():
                self._last_id += 1
                result = MagicMock()
                result.meta = MagicMock()
                result.meta.last_row_id = self._last_id
                return result
            mock.run = run
        
        # get_email_by_message_id query
        elif "SELECT * FROM emails WHERE message_id" in query:
            async def first():
                return self.data.get("email")
            mock.first = first
        
        # get_emails_by_conversation query
        elif "SELECT * FROM emails WHERE conversation_id" in query:
            async def all():
                result = MagicMock()
                result.results = self.data.get("conversation_emails", [])
                return result
            mock.all = all
        
        # get_recent_emails query
        elif "SELECT * FROM emails ORDER BY" in query:
            async def all():
                result = MagicMock()
                result.results = self.data.get("recent_emails", [])
                return result
            mock.all = all
        
        # get_classification_stats query
        elif "SELECT classification, COUNT" in query:
            async def all():
                result = MagicMock()
                result.results = self.data.get("classification_stats", [])
                return result
            mock.all = all
        
        # get_conversation_stats query
        elif "GROUP BY conversation_id" in query:
            async def all():
                result = MagicMock()
                result.results = self.data.get("conversation_stats", [])
                return result
            mock.all = all
        
        # Default fallback
        else:
            async def run():
                return MagicMock()
            mock.run = run
            async def all():
                result = MagicMock()
                result.results = []
                return result
            mock.all = all
        
        return mock


@pytest.fixture
def mock_db():
    return MockDB()


# =============================================================================
# email_exists tests
# =============================================================================

@pytest.mark.asyncio
async def test_email_exists_returns_false_when_not_found(mock_db):
    """Test email_exists returns False when email not in DB."""
    mock_db.data["exists_check"] = None
    result = await email_exists(mock_db, "test-message-id")
    assert result is False


@pytest.mark.asyncio
async def test_email_exists_returns_true_when_found(mock_db):
    """Test email_exists returns True when email exists."""
    mock_db.data["exists_check"] = {"id": 1}
    result = await email_exists(mock_db, "test-message-id")
    assert result is True


# =============================================================================
# save_email tests
# =============================================================================

@pytest.mark.asyncio
async def test_save_email_returns_id(mock_db):
    """Test save_email returns the new row ID."""
    result = await save_email(
        mock_db,
        message_id="test-123",
        subject="Test Subject",
        snippet="Test snippet",
        from_address="test@example.com",
        from_name="Test User",
        classification="academic-results",
        confidence=0.95,
        reason="Test reason",
        received_at="2024-01-01T00:00:00Z",
    )
    assert result == 1


@pytest.mark.asyncio
async def test_save_email_with_conversation_id(mock_db):
    """Test save_email stores conversation_id correctly."""
    result = await save_email(
        mock_db,
        message_id="test-456",
        subject="Re: Test Subject",
        snippet="Reply to test",
        from_address="reply@example.com",
        from_name="Reply User",
        classification="academic-results",
        confidence=0.90,
        reason="Follow-up email",
        received_at="2024-01-02T00:00:00Z",
        conversation_id="conv-abc-123",
    )
    assert result == 1


@pytest.mark.asyncio
async def test_save_email_handles_none_values(mock_db):
    """Test save_email handles None values gracefully."""
    result = await save_email(
        mock_db,
        message_id="test-789",
        subject=None,
        snippet=None,
        from_address=None,
        from_name=None,
        classification="general-inquiry",
        confidence=0.5,
        reason=None,
        received_at=None,
        conversation_id=None,
    )
    assert result == 1


# =============================================================================
# get_email_by_message_id tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_email_by_message_id_returns_email(mock_db):
    """Test get_email_by_message_id returns full email data."""
    mock_email = MagicMock()
    mock_email.id = 1
    mock_email.message_id = "test-123"
    mock_email.conversation_id = "conv-456"
    mock_email.subject = "Test Subject"
    mock_email.snippet = "Test snippet"
    mock_email.from_address = "test@example.com"
    mock_email.from_name = "Test User"
    mock_email.classification = "finance-payment"
    mock_email.confidence = 0.95
    mock_email.reason = "Payment related"
    mock_email.draft_reply = ""
    mock_email.received_at = "2024-01-01"
    mock_email.processed_at = "2024-01-01"
    
    mock_db.data["email"] = mock_email
    
    result = await get_email_by_message_id(mock_db, "test-123")
    
    assert result is not None
    assert result["message_id"] == "test-123"
    assert result["conversation_id"] == "conv-456"
    assert result["subject"] == "Test Subject"
    assert result["classification"] == "finance-payment"


@pytest.mark.asyncio
async def test_get_email_by_message_id_returns_none_when_not_found(mock_db):
    """Test get_email_by_message_id returns None when email not found."""
    mock_db.data["email"] = None
    
    result = await get_email_by_message_id(mock_db, "nonexistent-id")
    assert result is None


# =============================================================================
# get_recent_emails tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_recent_emails_returns_list(mock_db):
    """Test get_recent_emails returns list of emails."""
    mock_email = MagicMock()
    mock_email.id = 1
    mock_email.message_id = "test-123"
    mock_email.conversation_id = "conv-123"
    mock_email.subject = "Test"
    mock_email.classification = "academic-results"
    mock_email.confidence = 0.9
    mock_email.received_at = "2024-01-01"
    
    mock_db.data["recent_emails"] = [mock_email]
    
    result = await get_recent_emails(mock_db, 10)
    
    assert len(result) == 1
    assert result[0]["message_id"] == "test-123"
    assert result[0]["conversation_id"] == "conv-123"
    assert result[0]["classification"] == "academic-results"


@pytest.mark.asyncio
async def test_get_recent_emails_returns_empty_list(mock_db):
    """Test get_recent_emails returns empty list when no emails."""
    mock_db.data["recent_emails"] = []
    
    result = await get_recent_emails(mock_db, 10)
    assert result == []


@pytest.mark.asyncio
async def test_get_recent_emails_returns_multiple(mock_db):
    """Test get_recent_emails returns multiple emails."""
    mock_email1 = MagicMock()
    mock_email1.id = 1
    mock_email1.message_id = "msg-1"
    mock_email1.conversation_id = "conv-1"
    mock_email1.subject = "First"
    mock_email1.classification = "finance-fees"
    mock_email1.confidence = 0.9
    mock_email1.received_at = "2024-01-01"
    
    mock_email2 = MagicMock()
    mock_email2.id = 2
    mock_email2.message_id = "msg-2"
    mock_email2.conversation_id = "conv-1"
    mock_email2.subject = "Second"
    mock_email2.classification = "finance-fees"
    mock_email2.confidence = 0.85
    mock_email2.received_at = "2024-01-02"
    
    mock_db.data["recent_emails"] = [mock_email1, mock_email2]
    
    result = await get_recent_emails(mock_db, 10)
    
    assert len(result) == 2
    assert result[0]["message_id"] == "msg-1"
    assert result[1]["message_id"] == "msg-2"


# =============================================================================
# get_classification_stats tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_classification_stats_returns_dict(mock_db):
    """Test get_classification_stats returns stats dictionary."""
    mock_stat = MagicMock()
    mock_stat.classification = "academic-results"
    mock_stat.count = 5
    
    mock_db.data["classification_stats"] = [mock_stat]
    
    result = await get_classification_stats(mock_db)
    assert result["academic-results"] == 5


@pytest.mark.asyncio
async def test_get_classification_stats_multiple_categories(mock_db):
    """Test get_classification_stats with multiple categories."""
    mock_stats = []
    for cat, count in [("academic-results", 10), ("finance-payment", 5), ("registration", 3)]:
        stat = MagicMock()
        stat.classification = cat
        stat.count = count
        mock_stats.append(stat)
    
    mock_db.data["classification_stats"] = mock_stats
    
    result = await get_classification_stats(mock_db)
    
    assert result["academic-results"] == 10
    assert result["finance-payment"] == 5
    assert result["registration"] == 3


@pytest.mark.asyncio
async def test_get_classification_stats_empty(mock_db):
    """Test get_classification_stats returns empty dict when no data."""
    mock_db.data["classification_stats"] = []
    
    result = await get_classification_stats(mock_db)
    assert result == {}


# =============================================================================
# get_emails_by_conversation tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_emails_by_conversation_returns_thread(mock_db):
    """Test get_emails_by_conversation returns all emails in a thread."""
    mock_email1 = MagicMock()
    mock_email1.id = 1
    mock_email1.message_id = "msg-1"
    mock_email1.conversation_id = "conv-abc"
    mock_email1.subject = "Initial question"
    mock_email1.snippet = "I have a question..."
    mock_email1.from_address = "student@example.com"
    mock_email1.from_name = "Student"
    mock_email1.classification = "academic-results"
    mock_email1.confidence = 0.9
    mock_email1.received_at = "2024-01-01T10:00:00Z"
    
    mock_email2 = MagicMock()
    mock_email2.id = 2
    mock_email2.message_id = "msg-2"
    mock_email2.conversation_id = "conv-abc"
    mock_email2.subject = "Re: Initial question"
    mock_email2.snippet = "Following up..."
    mock_email2.from_address = "student@example.com"
    mock_email2.from_name = "Student"
    mock_email2.classification = "academic-results"
    mock_email2.confidence = 0.85
    mock_email2.received_at = "2024-01-02T10:00:00Z"
    
    mock_db.data["conversation_emails"] = [mock_email1, mock_email2]
    
    result = await get_emails_by_conversation(mock_db, "conv-abc")
    
    assert len(result) == 2
    assert result[0]["conversation_id"] == "conv-abc"
    assert result[1]["conversation_id"] == "conv-abc"
    assert result[0]["subject"] == "Initial question"
    assert result[1]["subject"] == "Re: Initial question"


@pytest.mark.asyncio
async def test_get_emails_by_conversation_returns_empty(mock_db):
    """Test get_emails_by_conversation returns empty list for unknown conversation."""
    mock_db.data["conversation_emails"] = []
    
    result = await get_emails_by_conversation(mock_db, "nonexistent-conv")
    assert result == []


@pytest.mark.asyncio
async def test_get_emails_by_conversation_includes_all_fields(mock_db):
    """Test get_emails_by_conversation returns all expected fields."""
    mock_email = MagicMock()
    mock_email.id = 1
    mock_email.message_id = "msg-1"
    mock_email.conversation_id = "conv-123"
    mock_email.subject = "Test"
    mock_email.snippet = "Test snippet"
    mock_email.from_address = "test@example.com"
    mock_email.from_name = "Test User"
    mock_email.classification = "registration"
    mock_email.confidence = 0.88
    mock_email.received_at = "2024-01-01"
    
    mock_db.data["conversation_emails"] = [mock_email]
    
    result = await get_emails_by_conversation(mock_db, "conv-123")
    
    assert len(result) == 1
    email = result[0]
    assert "id" in email
    assert "message_id" in email
    assert "conversation_id" in email
    assert "subject" in email
    assert "snippet" in email
    assert "from_address" in email
    assert "from_name" in email
    assert "classification" in email
    assert "confidence" in email
    assert "received_at" in email


# =============================================================================
# get_conversation_stats tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_conversation_stats_returns_stats(mock_db):
    """Test get_conversation_stats returns conversation statistics."""
    mock_stat = MagicMock()
    mock_stat.conversation_id = "conv-123"
    mock_stat.message_count = 3
    mock_stat.classifications = "academic-results,academic-exam"
    
    mock_db.data["conversation_stats"] = [mock_stat]
    
    result = await get_conversation_stats(mock_db)
    
    assert result["total_conversations"] == 1
    assert len(result["conversations"]) == 1
    assert result["conversations"][0]["conversation_id"] == "conv-123"
    assert result["conversations"][0]["message_count"] == 3
    assert "academic-results" in result["conversations"][0]["classifications"]
    assert "academic-exam" in result["conversations"][0]["classifications"]


@pytest.mark.asyncio
async def test_get_conversation_stats_empty(mock_db):
    """Test get_conversation_stats returns empty when no conversations."""
    mock_db.data["conversation_stats"] = []
    
    result = await get_conversation_stats(mock_db)
    
    assert result["total_conversations"] == 0
    assert result["conversations"] == []


@pytest.mark.asyncio
async def test_get_conversation_stats_multiple_conversations(mock_db):
    """Test get_conversation_stats with multiple conversations."""
    mock_stats = []
    
    stat1 = MagicMock()
    stat1.conversation_id = "conv-1"
    stat1.message_count = 5
    stat1.classifications = "finance-payment,finance-fees"
    mock_stats.append(stat1)
    
    stat2 = MagicMock()
    stat2.conversation_id = "conv-2"
    stat2.message_count = 2
    stat2.classifications = "registration"
    mock_stats.append(stat2)
    
    mock_db.data["conversation_stats"] = mock_stats
    
    result = await get_conversation_stats(mock_db)
    
    assert result["total_conversations"] == 2
    assert len(result["conversations"]) == 2


@pytest.mark.asyncio
async def test_get_conversation_stats_handles_null_classifications(mock_db):
    """Test get_conversation_stats handles null classifications gracefully."""
    mock_stat = MagicMock()
    mock_stat.conversation_id = "conv-null"
    mock_stat.message_count = 1
    mock_stat.classifications = None
    
    mock_db.data["conversation_stats"] = [mock_stat]
    
    result = await get_conversation_stats(mock_db)
    
    assert result["total_conversations"] == 1
    assert result["conversations"][0]["classifications"] == []
