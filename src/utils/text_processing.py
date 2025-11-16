"""Text processing utilities"""

from typing import List, Tuple
import re
import hashlib
from langdetect import detect, LangDetectException
import logging

from src.core.config import settings

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect language of text

    Args:
        text: Input text

    Returns:
        ISO 639-1 language code (e.g., 'en', 'fr')
    """
    if not text or len(text) < 10:
        return "en"  # Default to English for short text

    try:
        lang = detect(text)
        # Validate against supported languages
        if lang in settings.SUPPORTED_LANGUAGES:
            return lang
        return "en"  # Default to English if unsupported
    except LangDetectException:
        logger.warning("Language detection failed, defaulting to English")
        return "en"


def clean_text(text: str) -> str:
    """
    Clean and normalize text

    Args:
        text: Input text

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove control characters
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)

    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(""", "'").replace(""", "'")

    return text.strip()


def chunk_text(
    text: str, chunk_size: int = None, chunk_overlap: int = None, doc_id: str = None
) -> List[Tuple[int, str, int, int]]:
    """
    Split text into overlapping chunks

    Args:
        text: Input text to chunk
        chunk_size: Maximum tokens per chunk (default from settings)
        chunk_overlap: Overlap between chunks in tokens (default from settings)
        doc_id: Document ID for logging

    Returns:
        List of tuples: (chunk_idx, chunk_text, char_start, char_end)
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    if not text:
        return []

    # Simple word-based chunking (approximation for tokens)
    # In production, use tiktoken or similar for accurate token counting
    words = text.split()

    if len(words) <= chunk_size:
        # Text fits in one chunk
        return [(0, text, 0, len(text))]

    chunks = []
    chunk_idx = 0
    start_word = 0

    while start_word < len(words):
        end_word = min(start_word + chunk_size, len(words))

        # Get chunk words
        chunk_words = words[start_word:end_word]
        chunk_text = " ".join(chunk_words)

        # Calculate character positions (approximate)
        char_start = len(" ".join(words[:start_word]))
        char_end = char_start + len(chunk_text)

        chunks.append((chunk_idx, chunk_text, char_start, char_end))

        chunk_idx += 1
        start_word += chunk_size - chunk_overlap

    logger.info(
        f"Split document into {len(chunks)} chunks (chunk_size={chunk_size}, overlap={chunk_overlap})"
    )
    return chunks


def compute_hash(text: str) -> str:
    """
    Compute SHA-256 hash of text for deduplication

    Args:
        text: Input text

    Returns:
        Hex digest of hash
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract keywords from text (simple implementation)

    Args:
        text: Input text
        max_keywords: Maximum number of keywords

    Returns:
        List of keywords
    """
    # Simple implementation: extract capitalized words
    # In production, use TF-IDF or proper keyword extraction
    words = text.split()
    capitalized = [w.strip(".,!?;:") for w in words if w and w[0].isupper() and len(w) > 3]

    # Remove duplicates and limit
    keywords = list(dict.fromkeys(capitalized))[:max_keywords]
    return keywords


def truncate_text(text: str, max_length: int = 500) -> str:
    """
    Truncate text to maximum length

    Args:
        text: Input text
        max_length: Maximum length in characters

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
