import pytest
import json
from httpx import AsyncClient
from app.main import app

@pytest.fixture
def evaluation_dataset():
    """Load evaluation dataset"""
    with open("tests/evaluation/test_dataset.json") as f:
        return json.load(f)

@pytest.mark.asyncio
async def test_evaluate_accuracy(evaluation_dataset):
    """Evaluate system accuracy dengan dataset"""
    
    results = []
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        for test_case in evaluation_dataset["test_cases"]:
            query = test_case["query"]
            expected_keywords = test_case["expected_keywords"]
            min_relevance = test_case["min_relevance"]
            
            response = await client.post("/api/chat/", json={"query": query})
            
            if response.status_code == 200:
                data = response.json()
                answer = data["answer"].lower()
                sources = data["sources"]
                
                # Check keyword presence
                keyword_match = sum(1 for kw in expected_keywords if kw in answer)
                keyword_score = keyword_match / len(expected_keywords)
                
                # Check source relevance
                avg_relevance = sum(s["similarity_score"] for s in sources) / len(sources) if sources else 0
                
                passed = keyword_score >= 0.5 and avg_relevance >= min_relevance
                
                results.append({
                    "id": test_case["id"],
                    "query": query,
                    "keyword_score": keyword_score,
                    "avg_relevance": avg_relevance,
                    "passed": passed
                })
            else:
                results.append({
                    "id": test_case["id"],
                    "query": query,
                    "error": response.status_code,
                    "passed": False
                })
    
    # Calculate overall accuracy
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    accuracy = passed_count / total_count if total_count > 0 else 0
    
    print(f"\n=== Evaluation Results ===")
    print(f"Total: {total_count}")
    print(f"Passed: {passed_count}")
    print(f"Accuracy: {accuracy * 100:.1f}%")
    print(f"\nDetails:")
    for r in results:
        status = "✓" if r["passed"] else "✗"
        print(f"{status} [{r['id']}] {r['query']}")
    
    # Assert minimum accuracy
    assert accuracy >= 0.6, f"Accuracy {accuracy*100:.1f}% below 60% threshold"
