"""Tests for classification configuration."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import CLASSIFICATION_TAGS, get_classification_prompt


def test_classification_tags_exist():
    """Verify all expected tags are present."""
    tag_names = [tag["name"] for tag in CLASSIFICATION_TAGS]
    expected = [
        "academic-results", "academic-exam", "academic-assignment",
        "admin-transcript", "admin-graduation",
        "finance-payment", "finance-fees", "registration",
        "technical-proctoring", "technical-access",
        "general-inquiry", "complaint-escalation"
    ]
    assert set(tag_names) == set(expected)


def test_each_tag_has_required_fields():
    """Each tag must have name, description, and examples."""
    for tag in CLASSIFICATION_TAGS:
        assert "name" in tag, f"Tag missing 'name'"
        assert "description" in tag, f"Tag {tag.get('name')} missing 'description'"
        assert "examples" in tag, f"Tag {tag.get('name')} missing 'examples'"
        assert len(tag["examples"]) > 0, f"Tag {tag['name']} has no examples"


def test_get_classification_prompt_includes_all_tags():
    """The prompt should include all tag names."""
    prompt = get_classification_prompt()
    for tag in CLASSIFICATION_TAGS:
        assert tag["name"] in prompt, f"Tag {tag['name']} not in prompt"


def test_get_classification_prompt_includes_json_format():
    """The prompt should specify JSON output format."""
    prompt = get_classification_prompt()
    assert "classification" in prompt
    assert "confidence" in prompt
    assert "reason" in prompt
    assert "JSON" in prompt


def test_tag_names_are_lowercase():
    """Tag names should be lowercase for consistency."""
    for tag in CLASSIFICATION_TAGS:
        assert tag["name"] == tag["name"].lower(), f"Tag {tag['name']} should be lowercase"


def test_tag_descriptions_not_empty():
    """Tag descriptions should be meaningful."""
    for tag in CLASSIFICATION_TAGS:
        assert len(tag["description"]) > 20, f"Tag {tag['name']} has too short description"
