"""Test fixtures and sample data"""

# Sample documents for testing
SAMPLE_DOCUMENTS = [
    {
        "source": "test",
        "source_id": "TEST-001",
        "title": "Test Document 1",
        "content": "This is a test document about enterprise search and information retrieval.",
        "content_type": "text/plain",
        "acl_allow": ["all-employees"],
        "country_tags": ["US"],
        "department": "Engineering",
        "tags": ["test", "search"],
    },
    {
        "source": "test",
        "source_id": "TEST-002",
        "title": "HR Policy Document",
        "content": "This document contains information about remote work policy and benefits.",
        "content_type": "text/plain",
        "acl_allow": ["all-employees", "uk-hr"],
        "country_tags": ["UK"],
        "department": "HR",
        "tags": ["policy", "hr", "remote-work"],
    },
]

# Sample users
SAMPLE_USERS = [
    {
        "username": "testuser1",
        "email": "test1@example.com",
        "password": "testpass123",
        "groups": ["all-employees"],
        "department": "Engineering",
        "country": "US",
    },
    {
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "testpass123",
        "groups": ["all-employees", "uk-hr"],
        "department": "HR",
        "country": "UK",
    },
]
