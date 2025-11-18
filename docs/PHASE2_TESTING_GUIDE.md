# Phase 2: Recommendation System Testing Guide

## Overview

This document outlines the comprehensive testing strategy for the recommendation system implementation.

## Test Coverage Summary

### ✅ Unit Tests (`tests/test_recommendation_service.py`)

**Purpose**: Test recommendation service logic in isolation

**Test Classes**:

1. **TestGetRelatedDocuments** - Content-based filtering
   - ✅ `test_related_documents_success` - Verify k-NN similarity search
   - ✅ `test_related_documents_no_embedding` - Handle documents without embeddings
   - ✅ `test_related_documents_not_found` - Handle non-existent documents
   - ✅ `test_personalization_boost` - Verify country/department boosting (1.2x for country, 1.1x for dept)

2. **TestGetTrending** - Trending documents
   - ✅ `test_trending_returns_mock_data` - Verify mock data structure
   - ✅ `test_trending_respects_limit` - Test pagination
   - ✅ `test_trending_without_user` - Test without ACL filtering

3. **TestGetPopularInDepartment** - Collaborative filtering
   - ✅ `test_popular_hr` - HR department popular docs
   - ✅ `test_popular_engineering` - Engineering department popular docs
   - ✅ `test_popular_unknown_department_defaults_to_hr` - Default behavior

4. **TestGetPersonalizedRecommendations** - Mixed strategy
   - ✅ `test_personalized_recommendations` - Verify mixed strategy (40% popular, 40% trending)
   - ✅ `test_personalized_deduplication` - No duplicate doc_ids
   - ✅ `test_personalized_respects_limit` - Pagination works

5. **TestErrorHandling** - Edge cases
   - ✅ `test_opensearch_error_handling` - Graceful degradation
   - ✅ `test_empty_results` - Handle empty result sets

**Run with**:
```bash
pytest tests/test_recommendation_service.py -v
```

### ✅ Integration Tests (`scripts/test_recommendations.py`)

**Purpose**: Test full API endpoints end-to-end

**Test Scenarios**:

1. **Multi-user testing** - Tests with 3 different user profiles:
   - john.doe (HR, UK) - Tests personalization for HR department
   - jane.smith (Engineering, US) - Tests engineering-specific content
   - admin (IT, US) - Tests admin access patterns

2. **All 4 endpoints tested**:
   - `GET /api/v1/recommendations/trending?hours={24,48,72}&limit=5`
   - `GET /api/v1/recommendations/popular?department={dept}&days=30&limit=5`
   - `GET /api/v1/recommendations/related/{doc_id}?limit=5`
   - `GET /api/v1/recommendations/for-you?limit=10`

3. **Performance benchmarks**:
   - Each endpoint tested 3 times
   - Target: <500ms response time
   - Measured: avg, min, max latency

**Run with**:
```bash
# Start API server first
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# In another terminal
python scripts/test_recommendations.py
```

### ✅ Frontend Validation

**UI Components** (`ui/templates/index.html`):

1. **Trending Now** widget
   - Fixed sidebar position (right: 20px, top: 100px)
   - Shows 5 trending documents
   - Updates every page load
   - Displays view counts and source badges

2. **Popular in Department** widget
   - Dynamic department name from user profile
   - Shows 5 popular documents
   - View counts displayed
   - Click-through to documents

3. **JavaScript Functions**:
   - `loadRecommendations()` - Master loader
   - `loadTrending()` - Fetches trending docs
   - `loadPopular()` - Fetches popular docs
   - `viewDocument(docId)` - Document viewer (placeholder)

**Manual Testing Checklist**:
- [ ] Login as john.doe → See HR popular docs
- [ ] Login as jane.smith → See Engineering popular docs
- [ ] Verify trending updates across users
- [ ] Click on recommendation → Should alert with doc ID
- [ ] Verify no duplicate recommendations
- [ ] Test with different window sizes (responsive)

## Test Data

### Mock Trending Documents
```python
- "Q4 2024 Company Strategy Update" (234.5 trend score, 156 views, 12h old)
- "2024 Benefits Enrollment Deadline" (187.3 trend score, 98 views, 8h old)
- "Updated Expense Reimbursement Policy" (156.8 trend score, 67 views, 16h old)
- "Work From Home Best Practices" (142.1 trend score, 89 views, 24h old)
- "VPN Setup Guide for New Employees" (128.5 trend score, 45 views, 6h old)
```

### Mock Popular by Department

**HR**:
- Annual Leave Policy (245 views, 87 unique viewers)
- Recruitment Guidelines 2024 (198 views, 65 unique viewers)
- Performance Review Process (187 views, 78 unique viewers)

**Engineering**:
- Production Deployment Checklist (312 views, 98 unique viewers)
- Code Review Best Practices (289 views, 102 unique viewers)
- On-Call Incident Response Runbook (267 views, 89 unique viewers)

**IT**:
- IT Helpdesk Ticket Guidelines (423 views, 134 unique viewers)
- Information Security Policy (398 views, 156 unique viewers)

## Expected Behaviors

### 1. Content-Based Filtering (Related Documents)

**Algorithm**:
```python
1. Get source document's embedding
2. Run k-NN search on embeddings index
3. Filter by user ACL (acl_allow contains user.groups, acl_deny doesn't)
4. Apply personalization boost:
   - Country match: score *= 1.2
   - Department match: score *= 1.1
5. Deduplicate by doc_id
6. Return top N results
```

**Expected Results**:
- Should return documents similar by content
- User's country/department docs should rank higher
- No duplicates
- Respects ACL permissions

### 2. Trending Documents

**Algorithm** (Production):
```python
score = (view_count / age_hours^0.8) * (1 + avg_dwell_time/60000)
```

**Current**: Mock data with pre-calculated scores

**Expected Results**:
- Recent documents with high views rank higher
- Time-decay reduces score for older docs
- Different time windows (24h, 48h, 72h) show different results

### 3. Popular in Department

**Algorithm** (Production):
```python
SELECT doc_id, COUNT(*) as views, COUNT(DISTINCT user_id) as unique_viewers
FROM document_views
WHERE department = :dept AND timestamp > NOW() - :days
GROUP BY doc_id
ORDER BY views DESC, unique_viewers DESC
LIMIT :limit
```

**Current**: Mock data by department

**Expected Results**:
- Department-specific content
- Sorted by view count
- Shows collaborative filtering ("People in your dept are viewing...")

### 4. Personalized Recommendations

**Strategy Mix**:
- 40% Popular in user's department (4 docs)
- 40% Trending (4 docs)
- 20% Buffer for additional trending (2 docs)

**Expected Results**:
- Mixed content from multiple strategies
- Deduplication across sources
- Personalized to user's department/country
- Always returns diverse content

## Performance Targets

### Response Time SLAs

| Endpoint | Target | Max Acceptable |
|----------|--------|----------------|
| Trending | <200ms | <500ms |
| Popular | <200ms | <500ms |
| Related | <300ms | <700ms (k-NN search) |
| Personalized | <400ms | <1000ms |

### Scalability Targets

- **Concurrent users**: 100+ simultaneous requests
- **Cache hit rate**: >80% for trending/popular
- **Database queries**: <5 per personalized request

## Known Limitations (Current MVP)

1. **Mock Data**: Trending and popular use mock data
   - ✅ Ready for analytics integration
   - ✅ Schema designed for production
   - ⏳ Awaiting document_views table implementation

2. **No Caching**: Each request queries fresh
   - ⏳ Redis caching planned for Phase 3
   - Target: 5-minute cache for trending, 15-minute for popular

3. **Limited Related Docs**: Depends on indexed documents
   - ✅ Algorithm implemented
   - ⏳ Awaiting full document ingestion

4. **No A/B Testing**: Single recommendation strategy
   - ⏳ Planned for Phase 4

## Continuous Testing

### Pre-commit Checks
```bash
# Run before committing
black src/ tests/
pytest tests/test_recommendation_service.py -v
```

### Integration Testing
```bash
# After deployment
./scripts/test_recommendations.py
```

### Load Testing (Future)
```bash
# Locust load test
locust -f tests/load/test_recommendations.py --host http://localhost:8000
```

## Success Criteria

✅ **Code Quality**:
- All unit tests pass
- Black formatting applied
- Type hints present
- Docstrings complete

✅ **Functionality**:
- All 4 endpoints return valid responses
- ACL filtering works correctly
- Personalization boosts apply correctly
- No duplicate recommendations

✅ **Performance**:
- Response times <500ms
- No memory leaks
- Handles concurrent requests

✅ **User Experience**:
- UI widgets load smoothly
- Recommendations update on login
- Click handlers work
- Responsive design

## Next Steps

1. **Phase 3**: Replace mock data with real analytics
   - Implement document_views table
   - Add view tracking middleware
   - Calculate real trending scores

2. **Phase 4**: Advanced features
   - Collaborative filtering using user similarity
   - Session-based recommendations
   - A/B testing framework
   - ML-based ranking

3. **Phase 5**: Optimization
   - Redis caching layer
   - Pre-computed recommendations
   - Real-time streaming updates
   - Personalized ranking models

## Appendix: Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run only recommendation tests
pytest tests/test_recommendation_service.py -v

# Run with coverage
pytest tests/ --cov=src/services/recommendation_service --cov-report=html

# Run integration tests
python scripts/test_recommendations.py

# Run specific test class
pytest tests/test_recommendation_service.py::TestGetRelatedDocuments -v

# Run with detailed output
pytest tests/test_recommendation_service.py -vv -s
```
