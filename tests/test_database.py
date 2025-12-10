"""Tests for database operations (mock-based)."""
import pytest
from unittest.mock import AsyncMock, MagicMock


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
        
        if "SELECT 1 FROM emails WHERE message_id" in query:
            async def first():
                return self.data.get("exists_check")
            mock.first = first
        elif "INSERT INTO emails" in query:
            async def run():
                self._last_id += 1
                result = MagicMock()
                result.meta = MagicMock()
                result.meta.last_row_id = self._last_id
                return result
            mock.run = run
        elif "SELECT * FROM emails WHERE message_id" in query:
            async def first():
                return self.data.get("email")
            mock.first = first
        elif "SELECT * FROM emails ORDER BY" in query:
            async def all():
                result = MagicMock()
                result.results = self.data.get("recent_emails", [])
                return result
            mock.all = all
        elif "SELECT classification, COUNT" in query:
            async def all():
                result = MagicMock()
                result.results = self.data.get("stats", [])
                return result
            mock.all = all
        
        return mock


@pytest.fixture
def mock_db():
    return MockDB()


@pytest.mark.asyncio
async def test_email_exists_returns_false_when_not_found(mock_db):
    """Test email_exists returns False when email not in DB."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from database import email_exists
    
    mock_db.data["exists_check"] = None
    result = await email_exists(mock_db, "test-message-id")
    assert result is False


@pytest.mark.asyncio
async def test_email_exists_returns_true_when_found(mock_db):
    """Test email_exists returns True when email exists."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from database import email_exists
    
    mock_db.data["exists_check"] = {"id": 1}
    result = await email_exists(mock_db, "test-message-id")
    assert result is True


@pytest.mark.asyncio
async def test_save_email_returns_id(mock_db):
    """Test save_email returns the new row ID."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from database import save_email
    
    result = await save_email(
        mock_db,
        message_id="test-123",
        subject="Test Subject",
        snippet="Test snippet",
        from_address="test@example.com",
        from_name="Test User",
        classification="academic",
        confidence=0.95,
        reason="Test reason",
        received_at="2024-01-01T00:00:00Z",
    )
    assert result == 1


@pytest.mark.asyncio
async def test_get_recent_emails_returns_list(mock_db):
    """Test get_recent_emails returns list of emails."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from database import get_recent_emails
    
    mock_email = MagicMock()
    mock_email.id = 1
    mock_email.message_id = "test-123"
    mock_email.subject = "Test"
    mock_email.classification = "academic"
    mock_email.confidence = 0.9
    mock_email.received_at = "2024-01-01"
    
    mock_db.data["recent_emails"] = [mock_email]
    
    result = await get_recent_emails(mock_db, 10)
    assert len(result) == 1
    assert result[0]["classification"] == "academic"


@pytest.mark.asyncio
async def test_get_classification_stats_returns_dict(mock_db):
    """Test get_classification_stats returns stats dictionary."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from database import get_classification_stats
    
    mock_stat = MagicMock()
    mock_stat.classification = "academic"
    mock_stat.count = 5
    
    mock_db.data["stats"] = [mock_stat]
    
    result = await get_classification_stats(mock_db)
    assert result["academic"] == 5
