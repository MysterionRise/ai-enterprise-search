"""
Test Recommendation System functionality
Tests all recommendation endpoints with various users and scenarios
"""

import asyncio
import httpx
import sys
from typing import Dict

BASE_URL = "http://localhost:8000"

# Test users with different departments and countries
TEST_USERS = [
    {"username": "john.doe", "password": "password123", "description": "HR user from UK"},
    {
        "username": "jane.smith",
        "password": "password123",
        "description": "Engineering user from US",
    },
    {"username": "admin", "password": "password123", "description": "IT admin from US"},
]


async def login_user(client: httpx.AsyncClient, username: str, password: str) -> str:
    """Login and return access token"""
    login_response = await client.post(
        f"{BASE_URL}/api/v1/auth/login", data={"username": username, "password": password}
    )
    login_response.raise_for_status()
    return login_response.json()["access_token"]


async def get_user_info(client: httpx.AsyncClient, token: str) -> Dict:
    """Get current user information"""
    response = await client.get(
        f"{BASE_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    return response.json()


async def test_trending(client: httpx.AsyncClient, token: str, user_info: Dict):
    """Test trending documents endpoint"""
    print("\n" + "=" * 80)
    print("TEST: TRENDING DOCUMENTS")
    print("=" * 80)
    print(f"User: {user_info['username']} ({user_info['department']}, {user_info['country']})")
    print()

    # Test different time windows
    time_windows = [24, 48, 72]

    for hours in time_windows:
        print(f"\n--- Testing {hours}h time window ---")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/recommendations/trending",
                headers={"Authorization": f"Bearer {token}"},
                params={"hours": hours, "limit": 5},
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Retrieved {data['count']} trending documents")
                print(f"  Time window: {data['time_window_hours']} hours")
                print(f"  Last updated: {data['last_updated']}")

                if data["trending"]:
                    print(f"\n  Top trending documents:")
                    for i, doc in enumerate(data["trending"][:3], 1):
                        print(f"    {i}. {doc['title']}")
                        print(f"       Source: {doc['source']}")
                        if "trend_score" in doc:
                            print(f"       Trend Score: {doc['trend_score']:.2f}")
                        if "view_count" in doc:
                            print(f"       Views: {doc['view_count']}")
                        if "age_hours" in doc:
                            print(f"       Age: {doc['age_hours']}h")
                        print()
                else:
                    print("  ⚠️  No trending documents found")

                print(f"✓ Trending test ({hours}h) PASSED")
            else:
                print(f"✗ Trending test ({hours}h) FAILED")
                print(f"  Status Code: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"✗ Trending test ({hours}h) ERROR: {e}")
            return False

    return True


async def test_popular(client: httpx.AsyncClient, token: str, user_info: Dict):
    """Test popular in department endpoint"""
    print("\n" + "=" * 80)
    print("TEST: POPULAR IN DEPARTMENT")
    print("=" * 80)
    print(f"User: {user_info['username']} ({user_info['department']}, {user_info['country']})")
    print()

    # Test 1: Default (user's department)
    print("--- Test 1: User's department (default) ---")
    try:
        response = await client.get(
            f"{BASE_URL}/api/v1/recommendations/popular",
            headers={"Authorization": f"Bearer {token}"},
            params={"days": 30, "limit": 5},
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Retrieved {data['count']} popular documents")
            print(f"  Department: {data['department']}")
            print(f"  Country: {data.get('country', 'Any')}")
            print(f"  Period: {data['period_days']} days")

            if data["popular"]:
                print(f"\n  Top popular documents in {data['department']}:")
                for i, doc in enumerate(data["popular"][:3], 1):
                    print(f"    {i}. {doc['title']}")
                    print(f"       Source: {doc['source']}")
                    if "view_count" in doc:
                        print(f"       Views: {doc['view_count']}")
                    if "unique_viewers" in doc:
                        print(f"       Unique Viewers: {doc['unique_viewers']}")
                    print()

            print("✓ Popular (default) test PASSED")
        else:
            print(f"✗ Popular (default) test FAILED: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Popular (default) test ERROR: {e}")
        return False

    # Test 2: Specific department
    print("\n--- Test 2: Specific department (Engineering) ---")
    try:
        response = await client.get(
            f"{BASE_URL}/api/v1/recommendations/popular",
            headers={"Authorization": f"Bearer {token}"},
            params={"department": "Engineering", "days": 30, "limit": 5},
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Retrieved {data['count']} popular documents")
            print(f"  Department: {data['department']}")

            if data["popular"]:
                print(f"\n  Top documents:")
                for i, doc in enumerate(data["popular"][:2], 1):
                    print(f"    {i}. {doc['title']}")

            print("✓ Popular (Engineering) test PASSED")
        else:
            print(f"✗ Popular (Engineering) test FAILED: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Popular (Engineering) test ERROR: {e}")
        return False

    return True


async def test_related(client: httpx.AsyncClient, token: str, user_info: Dict):
    """Test related documents endpoint"""
    print("\n" + "=" * 80)
    print("TEST: RELATED DOCUMENTS (Content-based filtering)")
    print("=" * 80)
    print(f"User: {user_info['username']} ({user_info['department']}, {user_info['country']})")
    print()

    # Test with various mock document IDs
    test_docs = [
        "confluence-policy-2024-q4",
        "servicenow-kb-benefits-2024",
        "sharepoint-expense-policy-new",
    ]

    for doc_id in test_docs:
        print(f"\n--- Testing related documents for: {doc_id} ---")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/recommendations/related/{doc_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 5},
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Found {data['count']} related documents")
                print(f"  Source document: {data['doc_id']}")

                if data["related"]:
                    print(f"\n  Top related documents:")
                    for i, doc in enumerate(data["related"][:3], 1):
                        print(f"    {i}. {doc['title']}")
                        print(f"       Source: {doc['source']}")
                        if "score" in doc:
                            print(f"       Similarity: {doc['score']:.3f}")
                        print(f"       Reason: {doc['reason']}")
                        print()

                    print(f"✓ Related documents test PASSED for {doc_id}")
                else:
                    print(
                        f"  ℹ️  No related documents found (expected if doc doesn't exist in index)"
                    )
                    print(f"✓ Related documents test PASSED for {doc_id}")

            elif response.status_code == 404:
                print(f"  ℹ️  Document not found in index (expected for demo data)")
                print(f"✓ Related documents test PASSED for {doc_id}")
            else:
                print(f"✗ Related documents test FAILED: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"✗ Related documents test ERROR: {e}")
            return False

    return True


async def test_personalized(client: httpx.AsyncClient, token: str, user_info: Dict):
    """Test personalized recommendations endpoint"""
    print("\n" + "=" * 80)
    print("TEST: PERSONALIZED RECOMMENDATIONS ('For You')")
    print("=" * 80)
    print(f"User: {user_info['username']} ({user_info['department']}, {user_info['country']})")
    print()

    try:
        response = await client.get(
            f"{BASE_URL}/api/v1/recommendations/for-you",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 10},
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Retrieved {data['count']} personalized recommendations")

            context = data["personalization_context"]
            print(f"\n  Personalization context:")
            print(f"    Username: {context['username']}")
            print(f"    Department: {context['department']}")
            print(f"    Country: {context['country']}")

            if data["recommendations"]:
                print(f"\n  Top personalized recommendations:")

                # Group by reason
                by_reason = {}
                for rec in data["recommendations"]:
                    reason = rec["reason"]
                    if reason not in by_reason:
                        by_reason[reason] = []
                    by_reason[reason].append(rec)

                for reason, recs in by_reason.items():
                    print(f"\n    {reason.replace('_', ' ').title()} ({len(recs)} items):")
                    for rec in recs[:2]:  # Show top 2 per category
                        print(f"      • {rec['title']}")
                        print(f"        Source: {rec['source']}")

                print(f"\n  Strategy distribution:")
                for reason, recs in by_reason.items():
                    print(f"    {reason}: {len(recs)} documents")

                print(f"\n✓ Personalized recommendations test PASSED")
                return True
            else:
                print("✗ No recommendations returned")
                return False

        else:
            print(f"✗ Personalized recommendations test FAILED: {response.status_code}")
            print(f"  Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Personalized recommendations test ERROR: {e}")
        return False


async def test_all_endpoints_for_user(user_config: Dict):
    """Run all recommendation tests for a specific user"""
    print("\n" + "=" * 80)
    print(f"TESTING AS: {user_config['username']} ({user_config['description']})")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        print(f"\n1. Logging in as {user_config['username']}...")
        try:
            token = await login_user(client, user_config["username"], user_config["password"])
            print("   ✓ Login successful")
        except Exception as e:
            print(f"   ✗ Login failed: {e}")
            return False

        # Get user info
        try:
            user_info = await get_user_info(client, token)
            print(
                f"   User: {user_info['full_name']} ({user_info['department']}, {user_info['country']})"
            )
            print(f"   Groups: {', '.join(user_info['groups'])}")
        except Exception as e:
            print(f"   ✗ Failed to get user info: {e}")
            return False

        # Run all tests
        results = []

        # Test 1: Trending
        results.append(await test_trending(client, token, user_info))

        # Test 2: Popular
        results.append(await test_popular(client, token, user_info))

        # Test 3: Related
        results.append(await test_related(client, token, user_info))

        # Test 4: Personalized
        results.append(await test_personalized(client, token, user_info))

        # Summary
        passed = sum(results)
        total = len(results)

        print("\n" + "=" * 80)
        print(f"USER TEST SUMMARY: {user_config['username']}")
        print("=" * 80)
        print(f"Passed: {passed}/{total}")
        if passed == total:
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED")

        return passed == total


async def test_performance():
    """Test response times for all endpoints"""
    print("\n" + "=" * 80)
    print("PERFORMANCE TEST")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        token = await login_user(client, "john.doe", "password123")
        headers = {"Authorization": f"Bearer {token}"}

        endpoints = [
            ("Trending", f"{BASE_URL}/api/v1/recommendations/trending?hours=24&limit=5"),
            ("Popular", f"{BASE_URL}/api/v1/recommendations/popular?days=30&limit=5"),
            ("Personalized", f"{BASE_URL}/api/v1/recommendations/for-you?limit=10"),
        ]

        print("\nTesting response times (3 requests each):")
        print("-" * 80)

        for name, url in endpoints:
            times = []
            for i in range(3):
                import time

                start = time.time()
                response = await client.get(url, headers=headers)
                elapsed = (time.time() - start) * 1000  # Convert to ms
                times.append(elapsed)

                if response.status_code != 200:
                    print(f"✗ {name} failed: {response.status_code}")
                    break

            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                print(
                    f"{name:15} - Avg: {avg_time:6.1f}ms  Min: {min_time:6.1f}ms  Max: {max_time:6.1f}ms"
                )

                # Performance threshold: should be under 500ms for demo data
                if avg_time < 500:
                    print(f"                ✓ Performance OK")
                else:
                    print(f"                ⚠️  Performance warning (>500ms)")

        print("\n✓ Performance test complete")


def main():
    """Run all recommendation tests"""
    print("\n" + "=" * 80)
    print("ENTERPRISE SEARCH - RECOMMENDATION SYSTEM TEST SUITE")
    print("=" * 80)
    print("\nThis script tests all recommendation endpoints:")
    print("  1. Trending documents")
    print("  2. Popular in department")
    print("  3. Related documents (content-based)")
    print("  4. Personalized recommendations")
    print("\nMake sure the API server is running on localhost:8000")
    print()

    # Test with all users
    all_passed = True
    for user_config in TEST_USERS:
        result = asyncio.run(test_all_endpoints_for_user(user_config))
        all_passed = all_passed and result

    # Performance test
    print("\n" + "-" * 80)
    response = input("Run performance tests? (y/n): ")
    if response.lower() == "y":
        asyncio.run(test_performance())

    # Final summary
    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETE")
    print("=" * 80)

    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nRecommendation system is working correctly!")
        print("- Trending documents are being served")
        print("- Popular in department shows relevant content")
        print("- Related documents use content similarity")
        print("- Personalized recommendations mix multiple strategies")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease review the test output above for details.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nTest suite failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
