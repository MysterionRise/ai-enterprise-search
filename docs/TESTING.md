# Testing Guide

## Overview

This project uses pytest for testing with comprehensive unit and integration tests.

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Unit Tests Only
```bash
pytest tests/unit -v
```

### Run Integration Tests Only
```bash
pytest tests/integration -v
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html
# View report: open htmlcov/index.html
```

### Run Specific Test File
```bash
pytest tests/unit/test_security.py -v
```

### Run Specific Test
```bash
pytest tests/unit/test_security.py::TestPasswordHashing::test_hash_password -v
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **test_models.py**: Data model validation
- **test_security.py**: Authentication and JWT tokens
- **test_text_processing.py**: Text utilities (chunking, language detection, etc.)

### Integration Tests (`tests/integration/`)
- **test_auth_api.py**: Authentication endpoints
- **test_health_api.py**: Health check endpoints

## Prerequisites for Integration Tests

Integration tests require services to be running:

```bash
# Start required services
docker-compose up -d postgres redis

# Run integration tests
pytest tests/integration -v
```

## Writing Tests

### Unit Test Example
```python
def test_my_function():
    """Test description"""
    result = my_function("input")
    assert result == "expected_output"
```

### Integration Test Example
```python
def test_api_endpoint(client, auth_headers):
    """Test API endpoint"""
    response = client.get("/api/v1/endpoint", headers=auth_headers)
    assert response.status_code == 200
```

## Fixtures

Available fixtures (see `tests/conftest.py`):
- `client`: FastAPI test client
- `auth_headers`: Authenticated request headers
- `mock_document`: Sample document for testing
- `mock_search_request`: Sample search request

## Coverage Goals

- Aim for >80% code coverage
- Critical paths (auth, search) should have >90% coverage
- All public APIs should have integration tests

## CI/CD

Tests run automatically on:
- Every push to main/develop branches
- Every pull request
- Manual workflow dispatch

See `.github/workflows/ci.yml` for CI configuration.

## Troubleshooting

### Tests failing with import errors
```bash
# Ensure src is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
pytest
```

### Database connection errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Verify connection
psql -h localhost -U searchuser -d enterprise_search_test
```

### OpenSearch tests failing
```bash
# Start OpenSearch for full integration tests
docker-compose up -d opensearch

# Wait for cluster to be ready
curl http://localhost:9200/_cluster/health
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Names**: Use descriptive test names
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Services**: Use mocks for external APIs
5. **Clean Up**: Use fixtures for setup/teardown
6. **Fast Tests**: Keep unit tests fast (<100ms each)

## Continuous Improvement

- Add tests for new features
- Update tests when fixing bugs
- Review coverage reports regularly
- Refactor tests to reduce duplication
