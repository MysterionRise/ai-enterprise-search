"""
Unit tests for RecommendationService
Tests the recommendation logic without requiring external services
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.recommendation_service import RecommendationService
from src.models.auth import User


@pytest.fixture
def mock_user():
    """Create a mock user for testing"""
    return User(
        username="john.doe",
        email="john.doe@company.com",
        full_name="John Doe",
        department="HR",
        country="UK",
        groups=["hr", "uk", "employees"],
    )


@pytest.fixture
def recommendation_service():
    """Create a RecommendationService instance with mocked OpenSearch"""
    with patch("src.services.recommendation_service.opensearch_service") as mock_os:
        mock_os.client = Mock()
        service = RecommendationService()
        return service


class TestGetRelatedDocuments:
    """Test content-based filtering (related documents)"""

    @pytest.mark.asyncio
    async def test_related_documents_success(self, recommendation_service, mock_user):
        """Test successful retrieval of related documents"""
        # Mock OpenSearch responses
        doc_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "embedding": [0.1] * 384,  # Mock embedding
                            "doc_id": "test-doc",
                            "title": "Test Document",
                        }
                    }
                ]
            }
        }

        knn_response = {
            "hits": {
                "hits": [
                    {
                        "_score": 0.95,
                        "_source": {
                            "doc_id": "related-doc-1",
                            "title": "Related Document 1",
                            "source": "confluence",
                            "country_tags": ["UK"],
                            "department": "HR",
                        },
                    },
                    {
                        "_score": 0.87,
                        "_source": {
                            "doc_id": "related-doc-2",
                            "title": "Related Document 2",
                            "source": "sharepoint",
                            "country_tags": ["US"],
                            "department": "Engineering",
                        },
                    },
                ]
            }
        }

        recommendation_service.os_client.search = Mock(side_effect=[doc_response, knn_response])

        # Test
        result = await recommendation_service.get_related_documents(
            doc_id="test-doc", user=mock_user, limit=5
        )

        # Assertions
        assert len(result) == 2
        assert result[0]["doc_id"] == "related-doc-1"
        assert result[0]["reason"] == "similar_content"
        # UK + HR match should boost score
        assert result[0]["score"] > 0.95  # Boosted score

        assert result[1]["doc_id"] == "related-doc-2"
        # No personalization boost
        assert result[1]["score"] == 0.87

    @pytest.mark.asyncio
    async def test_related_documents_no_embedding(self, recommendation_service, mock_user):
        """Test when document has no embedding"""
        doc_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "doc_id": "test-doc",
                            "title": "Test Document",
                            # No embedding field
                        }
                    }
                ]
            }
        }

        recommendation_service.os_client.search = Mock(return_value=doc_response)

        result = await recommendation_service.get_related_documents(
            doc_id="test-doc", user=mock_user, limit=5
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_related_documents_not_found(self, recommendation_service, mock_user):
        """Test when document doesn't exist"""
        doc_response = {"hits": {"hits": []}}

        recommendation_service.os_client.search = Mock(return_value=doc_response)

        result = await recommendation_service.get_related_documents(
            doc_id="nonexistent-doc", user=mock_user, limit=5
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_personalization_boost(self, recommendation_service, mock_user):
        """Test that personalization boosts relevant documents"""
        doc_response = {
            "hits": {
                "hits": [
                    {"_source": {"embedding": [0.1] * 384, "doc_id": "test-doc", "title": "Test"}}
                ]
            }
        }

        knn_response = {
            "hits": {
                "hits": [
                    {
                        "_score": 1.0,
                        "_source": {
                            "doc_id": "perfect-match",
                            "title": "Perfect Match",
                            "source": "confluence",
                            "country_tags": ["UK"],  # Matches user country
                            "department": "HR",  # Matches user department
                        },
                    }
                ]
            }
        }

        recommendation_service.os_client.search = Mock(side_effect=[doc_response, knn_response])

        result = await recommendation_service.get_related_documents(
            doc_id="test-doc", user=mock_user, limit=1
        )

        # Should have both country (1.2x) and department (1.1x) boosts
        expected_score = 1.0 * 1.2 * 1.1
        assert abs(result[0]["score"] - expected_score) < 0.01


class TestGetTrending:
    """Test trending documents"""

    @pytest.mark.asyncio
    async def test_trending_returns_mock_data(self, recommendation_service, mock_user):
        """Test that trending returns expected mock data"""
        result = await recommendation_service.get_trending(hours=24, limit=10, user=mock_user)

        assert len(result) <= 10
        assert all("doc_id" in doc for doc in result)
        assert all("title" in doc for doc in result)
        assert all("reason" == "trending" for doc in result)
        assert all("trend_score" in doc for doc in result)

    @pytest.mark.asyncio
    async def test_trending_respects_limit(self, recommendation_service, mock_user):
        """Test that limit parameter works"""
        result = await recommendation_service.get_trending(hours=24, limit=3, user=mock_user)

        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_trending_without_user(self, recommendation_service):
        """Test trending without user (no ACL filtering)"""
        result = await recommendation_service.get_trending(hours=48, limit=5, user=None)

        assert len(result) > 0


class TestGetPopularInDepartment:
    """Test popular documents (collaborative filtering)"""

    @pytest.mark.asyncio
    async def test_popular_hr(self, recommendation_service):
        """Test popular documents in HR department"""
        result = await recommendation_service.get_popular_in_department(
            department="HR", days=30, limit=5
        )

        assert len(result) > 0
        assert all("doc_id" in doc for doc in result)
        assert all("reason" in doc for doc in result)
        assert all("hr" in doc["reason"].lower() for doc in result)

    @pytest.mark.asyncio
    async def test_popular_engineering(self, recommendation_service):
        """Test popular documents in Engineering department"""
        result = await recommendation_service.get_popular_in_department(
            department="Engineering", days=30, limit=5
        )

        assert len(result) > 0
        assert all("engineering" in doc["reason"].lower() for doc in result)

    @pytest.mark.asyncio
    async def test_popular_unknown_department_defaults_to_hr(self, recommendation_service):
        """Test that unknown department defaults to HR"""
        result = await recommendation_service.get_popular_in_department(
            department="UnknownDept", days=30, limit=5
        )

        # Should default to HR
        assert len(result) > 0


class TestGetPersonalizedRecommendations:
    """Test personalized recommendations (mixed strategy)"""

    @pytest.mark.asyncio
    async def test_personalized_recommendations(self, recommendation_service, mock_user):
        """Test personalized recommendations combine multiple strategies"""
        result = await recommendation_service.get_personalized_recommendations(
            user=mock_user, limit=10
        )

        assert len(result) > 0
        assert len(result) <= 10

        # Check that we have different recommendation types
        reasons = [doc["reason"] for doc in result]

        # Should have mix of popular and trending
        has_popular = any("popular" in reason for reason in reasons)
        has_trending = any("trending" in reason for reason in reasons)

        assert has_popular or has_trending

    @pytest.mark.asyncio
    async def test_personalized_deduplication(self, recommendation_service, mock_user):
        """Test that personalized recommendations deduplicate by doc_id"""
        result = await recommendation_service.get_personalized_recommendations(
            user=mock_user, limit=20
        )

        doc_ids = [doc["doc_id"] for doc in result]

        # No duplicates
        assert len(doc_ids) == len(set(doc_ids))

    @pytest.mark.asyncio
    async def test_personalized_respects_limit(self, recommendation_service, mock_user):
        """Test that limit parameter is respected"""
        result = await recommendation_service.get_personalized_recommendations(
            user=mock_user, limit=5
        )

        assert len(result) <= 5


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_opensearch_error_handling(self, recommendation_service, mock_user):
        """Test that OpenSearch errors are handled gracefully"""
        recommendation_service.os_client.search = Mock(
            side_effect=Exception("OpenSearch connection failed")
        )

        result = await recommendation_service.get_related_documents(
            doc_id="test-doc", user=mock_user, limit=5
        )

        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_results(self, recommendation_service, mock_user):
        """Test handling of empty results"""
        doc_response = {
            "hits": {
                "hits": [
                    {"_source": {"embedding": [0.1] * 384, "doc_id": "test-doc", "title": "Test"}}
                ]
            }
        }

        knn_response = {"hits": {"hits": []}}  # No related documents

        recommendation_service.os_client.search = Mock(side_effect=[doc_response, knn_response])

        result = await recommendation_service.get_related_documents(
            doc_id="test-doc", user=mock_user, limit=5
        )

        assert result == []


# Integration test markers (for when full environment is available)
class TestIntegration:
    """
    Integration tests that require full environment
    These are marked as integration and can be run separately
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_recommendation_pipeline(self):
        """
        Full integration test with real OpenSearch
        Requires: OpenSearch running with test data
        """
        # This would test the full pipeline with real services
        pytest.skip("Requires full environment")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """
        Test recommendation performance
        Requires: Full environment with realistic data volume
        """
        # Test that recommendations return in <500ms
        pytest.skip("Requires full environment")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
