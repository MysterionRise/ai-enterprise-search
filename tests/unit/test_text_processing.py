"""Unit tests for text processing utilities"""
import pytest
from src.utils.text_processing import (
    detect_language,
    clean_text,
    chunk_text,
    compute_hash,
    extract_keywords,
    truncate_text
)


class TestLanguageDetection:
    """Test language detection"""

    def test_detect_english(self):
        text = "This is a test document in English language"
        assert detect_language(text) == "en"

    def test_detect_short_text_defaults_to_english(self):
        text = "Hi"
        assert detect_language(text) == "en"

    def test_detect_empty_text(self):
        assert detect_language("") == "en"


class TestTextCleaning:
    """Test text cleaning and normalization"""

    def test_clean_extra_whitespace(self):
        text = "This  has   extra    spaces"
        cleaned = clean_text(text)
        assert cleaned == "This has extra spaces"

    def test_clean_control_characters(self):
        text = "Text with\x00control\x1fchars"
        cleaned = clean_text(text)
        assert "\x00" not in cleaned
        assert "\x1f" not in cleaned

    def test_clean_empty_text(self):
        assert clean_text("") == ""

    def test_clean_normalize_quotes(self):
        text = ""Test" with 'fancy' quotes"
        cleaned = clean_text(text)
        assert '"Test"' in cleaned or "'fancy'" in cleaned


class TestTextChunking:
    """Test text chunking functionality"""

    def test_chunk_short_text(self):
        text = "This is a short text"
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
        assert len(chunks) == 1
        assert chunks[0][0] == 0  # chunk_idx
        assert chunks[0][1] == text

    def test_chunk_long_text(self):
        # Create text with 200 words
        text = " ".join([f"word{i}" for i in range(200)])
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 1

    def test_chunk_empty_text(self):
        chunks = chunk_text("")
        assert chunks == []

    def test_chunk_indices_sequential(self):
        text = " ".join([f"word{i}" for i in range(100)])
        chunks = chunk_text(text, chunk_size=20, chunk_overlap=5)
        for i, (idx, _, _, _) in enumerate(chunks):
            assert idx == i


class TestHashing:
    """Test content hashing"""

    def test_compute_hash_consistent(self):
        text = "Test content for hashing"
        hash1 = compute_hash(text)
        hash2 = compute_hash(text)
        assert hash1 == hash2

    def test_compute_hash_different_text(self):
        hash1 = compute_hash("Text 1")
        hash2 = compute_hash("Text 2")
        assert hash1 != hash2

    def test_hash_length(self):
        text = "Test"
        hash_val = compute_hash(text)
        assert len(hash_val) == 64  # SHA-256 hex digest


class TestKeywordExtraction:
    """Test keyword extraction"""

    def test_extract_capitalized_words(self):
        text = "The Company has several Products including Database and Analytics"
        keywords = extract_keywords(text, max_keywords=10)
        assert "Company" in keywords
        assert "Products" in keywords
        assert "Database" in keywords

    def test_extract_max_keywords(self):
        text = " ".join([f"Word{i}" for i in range(20)])
        keywords = extract_keywords(text, max_keywords=5)
        assert len(keywords) <= 5

    def test_extract_from_empty_text(self):
        keywords = extract_keywords("")
        assert keywords == []


class TestTextTruncation:
    """Test text truncation"""

    def test_truncate_long_text(self):
        text = "A" * 1000
        truncated = truncate_text(text, max_length=100)
        assert len(truncated) <= 100
        assert truncated.endswith("...")

    def test_truncate_short_text_unchanged(self):
        text = "Short text"
        truncated = truncate_text(text, max_length=100)
        assert truncated == text

    def test_truncate_exact_length(self):
        text = "A" * 100
        truncated = truncate_text(text, max_length=100)
        assert truncated == text
