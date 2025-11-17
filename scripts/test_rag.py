"""
Test RAG (Retrieval-Augmented Generation) functionality
"""
import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000"


async def test_rag():
    """Test RAG endpoints with various queries"""

    print("=" * 80)
    print("RAG FUNCTIONALITY TEST")
    print("=" * 80)
    print()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Login
        print("1. Logging in as demo user...")
        try:
            login_response = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                data={"username": "john.doe", "password": "password123"}
            )
            login_response.raise_for_status()
            token = login_response.json()["access_token"]
            print("   ✓ Login successful")
        except Exception as e:
            print(f"   ✗ Login failed: {e}")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Check RAG health
        print("\n2. Checking RAG service health...")
        try:
            health_response = await client.get(
                f"{BASE_URL}/api/v1/rag/health"
            )
            health_data = health_response.json()
            print(f"   Status: {health_data['status']}")
            print(f"   LLM Available: {health_data['llm_available']}")
            print(f"   Provider: {health_data['provider']}")
            print(f"   Model: {health_data['model']}")

            if not health_data['llm_available']:
                print("\n   ⚠️  WARNING: LLM service not available!")
                print("   Make sure Ollama is running and the model is downloaded:")
                print("   - Start Ollama: ollama serve")
                print("   - Pull model: ollama pull llama3.1:8b-instruct-q4_0")
                print()
                # Continue anyway to test other parts
        except Exception as e:
            print(f"   ✗ Health check failed: {e}")

        # Step 3: Test RAG with various queries
        test_queries = [
            {
                "query": "What is our remote work policy?",
                "description": "Policy question"
            },
            {
                "query": "How do I request vacation time?",
                "description": "Process question"
            },
            {
                "query": "What are the office hours?",
                "description": "Simple factual question"
            },
            {
                "query": "Tell me about expense reimbursement",
                "description": "General information query"
            }
        ]

        for i, test_case in enumerate(test_queries, 1):
            query = test_case["query"]
            description = test_case["description"]

            print(f"\n{'=' * 80}")
            print(f"TEST {i}: {description}")
            print(f"QUERY: {query}")
            print('=' * 80)

            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/rag/ask",
                    headers=headers,
                    json={
                        "query": query,
                        "num_chunks": 5,
                        "temperature": 0.3
                    }
                )

                if response.status_code == 200:
                    data = response.json()

                    print(f"\n✓ Answer generated successfully\n")
                    print("ANSWER:")
                    print("-" * 80)
                    print(data['answer'])
                    print("-" * 80)

                    print(f"\nSOURCES ({len(data['sources'])}):")
                    for j, source in enumerate(data['sources'], 1):
                        print(f"  [{j}] {source['title']}")
                        print(f"      Source: {source['source']}")
                        print(f"      Score: {source['score']:.3f}")
                        print(f"      Snippet: {source['snippet'][:100]}...")

                    if data['citations']:
                        print(f"\nCITATIONS ({len(data['citations'])}):")
                        for citation in data['citations']:
                            print(f"  - {citation['reference']}: {citation['title']}")

                    print(f"\nMETADATA:")
                    print(f"  Retrieval Time: {data['metadata']['retrieval_time_ms']:.0f}ms")
                    print(f"  Generation Time: {data['metadata']['generation_time_ms']:.0f}ms")
                    print(f"  Total Time: {data['metadata']['total_time_ms']:.0f}ms")
                    print(f"  Chunks Used: {data['metadata']['chunks_used']}")
                    print(f"  Model: {data['metadata']['model']}")
                    print(f"  Temperature: {data['metadata']['temperature']}")

                    print(f"\n✓ Test {i} PASSED")
                else:
                    print(f"\n✗ Test {i} FAILED")
                    print(f"   Status Code: {response.status_code}")
                    print(f"   Response: {response.text}")

            except httpx.TimeoutException:
                print(f"\n✗ Test {i} TIMEOUT")
                print("   LLM generation took too long (>60s)")
            except Exception as e:
                print(f"\n✗ Test {i} ERROR")
                print(f"   Error: {e}")

        # Step 4: Test available models endpoint
        print(f"\n{'=' * 80}")
        print("AVAILABLE MODELS TEST")
        print('=' * 80)
        try:
            models_response = await client.get(
                f"{BASE_URL}/api/v1/rag/models",
                headers=headers
            )
            if models_response.status_code == 200:
                models_data = models_response.json()
                print(f"\nProvider: {models_data['provider']}")
                print(f"Current Model: {models_data['current_model']}")
                print(f"Available Models ({len(models_data['models'])}):")
                for model in models_data['models']:
                    marker = "★" if model == models_data['current_model'] else " "
                    print(f"  {marker} {model}")
                print("\n✓ Models endpoint PASSED")
            else:
                print(f"\n✗ Models endpoint FAILED: {models_response.status_code}")
        except Exception as e:
            print(f"\n✗ Models endpoint ERROR: {e}")

    print(f"\n{'=' * 80}")
    print("RAG TEST COMPLETE")
    print('=' * 80)


async def test_streaming():
    """Test RAG streaming endpoint"""
    print("\n" + "=" * 80)
    print("STREAMING TEST")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Login
        login_response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={"username": "john.doe", "password": "password123"}
        )
        token = login_response.json()["access_token"]

        print("\nStreaming answer for: 'What is our remote work policy?'")
        print("-" * 80)

        try:
            async with client.stream(
                "POST",
                f"{BASE_URL}/api/v1/rag/ask/stream",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "query": "What is our remote work policy?",
                    "num_chunks": 5
                }
            ) as response:
                response.raise_for_status()

                sources_received = False
                tokens_received = 0

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        data = json.loads(line[6:])  # Remove 'data: ' prefix

                        if data["type"] == "sources":
                            sources_received = True
                            print(f"\n✓ Received {len(data['sources'])} sources")

                        elif data["type"] == "token":
                            if tokens_received == 0:
                                print("\nGenerated text:", end=" ")
                            print(data["token"], end="", flush=True)
                            tokens_received += 1

                        elif data["type"] == "done":
                            print(f"\n\n✓ Streaming complete ({tokens_received} tokens)")

                        elif data["type"] == "error":
                            print(f"\n✗ Error: {data['message']}")

                if sources_received and tokens_received > 0:
                    print("\n✓ Streaming test PASSED")
                else:
                    print("\n✗ Streaming test FAILED")

        except Exception as e:
            print(f"\n✗ Streaming test ERROR: {e}")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("ENTERPRISE SEARCH - RAG TEST SUITE")
    print("=" * 80)
    print("\nThis script tests the RAG (Retrieval-Augmented Generation) functionality")
    print("Make sure the following services are running:")
    print("  - API server (localhost:8000)")
    print("  - Ollama service with llama3.1:8b-instruct-q4_0 model")
    print()

    # Run tests
    asyncio.run(test_rag())

    # Ask if user wants to test streaming
    print("\n" + "-" * 80)
    response = input("Test streaming endpoint? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(test_streaming())

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nTest suite failed: {e}")
        sys.exit(1)
