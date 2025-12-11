"""
Common utility functions shared across modules.
"""
import re


def strip_html(html: str) -> str:
    """
    Strip HTML tags, HTML entities, and normalize whitespace.
    Used for processing email body content from MS Graph.
    """
    if not html:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Replace &nbsp; and other common HTML entities
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&#160;', ' ', text)  # numeric form of nbsp
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#\d+;', '', text)  # remove other numeric entities
    text = re.sub(r'&\w+;', '', text)  # remove any remaining named entities
    # Remove zero-width characters and other invisible unicode
    text = re.sub(r'[\u200b-\u200f\u2028-\u202f\u205f-\u206f\ufeff]', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
