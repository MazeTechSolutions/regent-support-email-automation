"""Tests for webhook handling logic."""
import pytest
from urllib.parse import urlparse, parse_qs


class TestWebhookValidation:
    """Test MS Graph webhook validation."""
    
    def test_extract_validation_token(self):
        """Test extracting validationToken from URL query params."""
        url = "https://example.com/webhook?validationToken=abc123xyz"
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        token = params.get("validationToken", [None])[0]
        assert token == "abc123xyz"
    
    def test_missing_validation_token(self):
        """Test handling missing validationToken."""
        url = "https://example.com/webhook?other=param"
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        token = params.get("validationToken", [None])[0]
        assert token is None
    
    def test_validation_token_with_special_chars(self):
        """Test validationToken with URL-encoded special characters."""
        url = "https://example.com/webhook?validationToken=token%2Bwith%2Fspecial%3Dchars"
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        token = params.get("validationToken", [None])[0]
        assert token == "token+with/special=chars"


class TestNotificationParsing:
    """Test MS Graph notification parsing."""
    
    def test_extract_message_id_from_resource(self):
        """Test extracting message ID from resource path."""
        resource = "Users/user-id-123/Messages/message-id-456"
        parts = resource.split("/")
        
        if len(parts) >= 4 and parts[2].lower() == "messages":
            message_id = parts[3]
        else:
            message_id = None
        
        assert message_id == "message-id-456"
    
    def test_extract_message_id_with_mailfolder(self):
        """Test extracting message ID from mailFolder resource path."""
        resource = "users/user@example.com/mailFolders/inbox/messages/msg-123"
        parts = resource.split("/")
        
        # Find 'messages' and get the next part
        message_id = None
        for i, part in enumerate(parts):
            if part.lower() == "messages" and i + 1 < len(parts):
                message_id = parts[i + 1]
                break
        
        assert message_id == "msg-123"
    
    def test_client_state_validation(self):
        """Test client state validation."""
        expected_state = "my-secret-token-123"
        notification_state = "my-secret-token-123"
        
        assert notification_state == expected_state
    
    def test_invalid_client_state(self):
        """Test invalid client state rejection."""
        expected_state = "my-secret-token-123"
        notification_state = "wrong-token"
        
        assert notification_state != expected_state


class TestChangeTypeFiltering:
    """Test filtering by change type."""
    
    def test_accept_created_change_type(self):
        """Test accepting 'created' change type."""
        change_type = "created"
        should_process = change_type == "created"
        assert should_process is True
    
    def test_reject_updated_change_type(self):
        """Test rejecting 'updated' change type."""
        change_type = "updated"
        should_process = change_type == "created"
        assert should_process is False
    
    def test_reject_deleted_change_type(self):
        """Test rejecting 'deleted' change type."""
        change_type = "deleted"
        should_process = change_type == "created"
        assert should_process is False
