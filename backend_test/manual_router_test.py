#!/usr/bin/env python3
"""
Manual integration test for the LLM Router and Auto Response Type.

This script tests the new auto mode routing without requiring pytest.
Run this after starting the backend server.
"""

import requests
import json
import sys

BACKEND_URL = "http://localhost:5001"

def test_query(question, response_type="auto", description=""):
    """Send a query and display the routing decision."""
    print(f"\n{'='*70}")
    print(f"TEST: {description or question}")
    print(f"{'='*70}")
    print(f"Question: {question}")
    print(f"Response Type: {response_type}")
    
    payload = {
        "question": question,
        "response_type": response_type,
        "style": "casual",
        "length": "short",
        "use_cache": False
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/query_v3",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nStatus: ✓ Success")
            print(f"Used RAG: {data.get('used_rag', 'unknown')}")
            
            if 'routing' in data:
                routing = data['routing']
                print(f"\nRouting Decision:")
                print(f"  Intent: {routing.get('intent')}")
                print(f"  Needs Retrieval: {routing.get('needs_retrieval')}")
                print(f"  Response Type: {routing.get('response_type')}")
                print(f"  Confidence: {routing.get('confidence')}")
                print(f"  Reasoning: {routing.get('reasoning')}")
            
            answer = data.get('answer', '')
            print(f"\nAnswer (first 200 chars):")
            print(f"{answer[:200]}...")
            
            return True
        else:
            print(f"\n✗ Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Connection Error: Cannot connect to backend at {BACKEND_URL}")
        print("Make sure the backend server is running (cd backend && python server_v2.py)")
        return False
    except Exception as e:
        print(f"\n✗ Exception: {e}")
        return False


def check_backend_health():
    """Check if backend is running."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ Backend is running at {BACKEND_URL}")
            return True
        else:
            print(f"✗ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to backend: {e}")
        return False


def main():
    """Run integration tests."""
    print("LLM Router Integration Test")
    print("="*70)
    
    if not check_backend_health():
        print("\nPlease start the backend server first:")
        print("  cd backend && python server_v2.py")
        sys.exit(1)
    
    print("\nRunning test queries...\n")
    
    tests = [
        {
            "question": "What is a binary search tree?",
            "description": "Conceptual question (should use RAG + Socratic)"
        },
        {
            "question": "Write a Python function to reverse a string",
            "description": "Code generation (should skip RAG, use Hint)"
        },
        {
            "question": "How does bubble sort work?",
            "description": "Algorithm explanation (should use RAG + Socratic)"
        },
        {
            "question": "Hello, how are you today?",
            "description": "Greeting (should skip RAG)"
        },
        {
            "question": "Create a class to represent a student with name and grade",
            "description": "Code generation (should skip RAG, use Hint)"
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test_query(test["question"], "auto", test["description"]):
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*70}")
    print(f"TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
