"""
Common utility functions shared across modules.
"""
import re


def strip_html(html: str) -> str:
    """
    Strip HTML tags and normalize whitespace.
    Used for processing email body content from MS Graph.
    """
    if not html:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
