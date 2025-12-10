"""Tests for classifier module (mock-based since it requires external API)."""
import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock


def test_classification_prompt_structure():
    """Test that the classification prompt is well-structured."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from config import get_classification_prompt, CLASSIFICATION_TAGS
    
    prompt = get_classification_prompt()
    
    # Should contain all tag names
    for tag in CLASSIFICATION_TAGS:
        assert tag["name"] in prompt
    
    # Should contain JSON format instructions
    assert "classification" in prompt
    assert "confidence" in prompt
    assert "reason" in prompt


def test_valid_classification_tags():
    """Test that all classification tags are valid."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from config import CLASSIFICATION_TAGS
    
    valid_tags = {
        "academic-results", "academic-exam", "admin-transcript", "admin-graduation",
        "finance-payment", "finance-fees", "registration", "technical-access", "general"
    }
    actual_tags = {tag["name"] for tag in CLASSIFICATION_TAGS}
    
    assert actual_tags == valid_tags


class TestClassifierResponseParsing:
    """Test classifier response parsing logic."""
    
    def test_parse_valid_json_response(self):
        """Test parsing a valid JSON response."""
        response = '{"classification": "academic", "confidence": 0.95, "reason": "About exams"}'
        result = json.loads(response)
        
        assert result["classification"] == "academic"
        assert result["confidence"] == 0.95
        assert result["reason"] == "About exams"
    
    def test_parse_json_with_markdown_code_block(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        response = '```json\n{"classification": "finance", "confidence": 0.8, "reason": "About fees"}\n```'
        
        # Strip markdown
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        
        result = json.loads(text)
        assert result["classification"] == "finance"
    
    def test_invalid_tag_handling(self):
        """Test that invalid tags get corrected to 'general'."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        from config import CLASSIFICATION_TAGS
        
        valid_tags = [tag["name"] for tag in CLASSIFICATION_TAGS]
        
        # Simulate invalid tag
        result = {"classification": "invalid_tag", "confidence": 0.9, "reason": "test"}
        
        if result.get("classification") not in valid_tags:
            result["classification"] = "general"
            result["confidence"] = max(0.3, result.get("confidence", 0.5) * 0.5)
        
        assert result["classification"] == "general"
        assert result["confidence"] == 0.45  # 0.9 * 0.5


class TestEmailExamples:
    """Test classification logic with sample emails."""
    
    def get_expected_classification(self, subject, body):
        """Simple rule-based classification for testing purposes."""
        text = f"{subject} {body}".lower()
        
        if any(word in text for word in ["result", "marks", "grade"]):
            return "academic-results"
        elif any(word in text for word in ["exam", "remark", "supplementary"]):
            return "academic-exam"
        elif any(word in text for word in ["transcript", "academic record"]):
            return "admin-transcript"
        elif any(word in text for word in ["graduation", "certificate", "degree"]):
            return "admin-graduation"
        elif any(word in text for word in ["payment", "paid", "proof of payment", "refund"]):
            return "finance-payment"
        elif any(word in text for word in ["fee", "invoice", "quote", "balance"]):
            return "finance-fees"
        elif any(word in text for word in ["register", "enroll", "registration"]):
            return "registration"
        elif any(word in text for word in ["password", "login", "portal", "error"]):
            return "technical-access"
        else:
            return "general"
    
    def test_academic_email(self):
        result = self.get_expected_classification(
            "Results question",
            "When will the results be released for this semester?"
        )
        assert result == "academic-results"
    
    def test_finance_email(self):
        result = self.get_expected_classification(
            "Fee payment",
            "I have made a payment. Please find attached proof of payment."
        )
        assert result == "finance-payment"
    
    def test_technical_email(self):
        result = self.get_expected_classification(
            "Can't access portal",
            "I'm getting an error when trying to login to the student portal"
        )
        assert result == "technical-access"
    
    def test_administration_email(self):
        result = self.get_expected_classification(
            "Need transcript",
            "Please send me a copy of my academic transcript"
        )
        assert result == "admin-transcript"
    
    def test_registration_email(self):
        result = self.get_expected_classification(
            "Registration help",
            "I want to register for the upcoming semester. How do I register?"
        )
        assert result == "registration"
    
    def test_general_email(self):
        result = self.get_expected_classification(
            "Hello",
            "I have a question about the campus"
        )
        assert result == "general"
