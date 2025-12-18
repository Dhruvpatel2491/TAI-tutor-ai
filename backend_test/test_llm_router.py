"""
Test suite for LLM Router functionality.

Tests the intelligent routing logic that determines whether RAG retrieval
is needed and which response type to use.
"""

import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from rag.llm_router import (
    LLMRouter,
    RoutingDecision,
    QueryIntent,
    ResponseTypeDecision,
    route_query
)


def test_router_initialization():
    """Test that the router initializes correctly."""
    router = LLMRouter()
    assert router is not None
    assert router.model == "llama3:8b"
    assert router.temperature == 0.1


def test_fallback_routing_code_generation():
    """Test fallback routing for code generation queries."""
    router = LLMRouter()
    
    # Force fallback by setting llm to None
    router._llm = None
    
    decision = router.route_query("Write a Python function to reverse a string")
    
    assert decision.intent == QueryIntent.CODE_GENERATION
    assert decision.needs_retrieval == False
    assert decision.response_type == ResponseTypeDecision.HINT


def test_fallback_routing_conceptual():
    """Test fallback routing for conceptual queries."""
    router = LLMRouter()
    
    # Force fallback by setting llm to None
    router._llm = None
    
    decision = router.route_query("What is a binary search tree?")
    
    # Default fallback should route to RAG
    assert decision.needs_retrieval == True


def test_fallback_routing_greeting():
    """Test fallback routing for greetings."""
    router = LLMRouter()
    
    # Force fallback by setting llm to None
    router._llm = None
    
    decision = router.route_query("Hello, how are you?")
    
    assert decision.intent == QueryIntent.GENERAL_CONVERSATION
    assert decision.needs_retrieval == False


def test_routing_decision_to_dict():
    """Test that RoutingDecision converts to dict correctly."""
    decision = RoutingDecision(
        intent=QueryIntent.RAG_RETRIEVAL,
        needs_retrieval=True,
        response_type=ResponseTypeDecision.SOCRATIC,
        confidence=0.9,
        reasoning="Test reasoning"
    )
    
    result = decision.to_dict()
    
    assert result["intent"] == "rag_retrieval"
    assert result["needs_retrieval"] == True
    assert result["response_type"] == "socratic"
    assert result["confidence"] == 0.9
    assert result["reasoning"] == "Test reasoning"


def test_route_query_convenience_function():
    """Test the convenience function for routing."""
    decision = route_query("What is recursion?")
    
    # Should return a valid RoutingDecision
    assert isinstance(decision, RoutingDecision)
    assert hasattr(decision, 'intent')
    assert hasattr(decision, 'needs_retrieval')
    assert hasattr(decision, 'response_type')


@pytest.mark.skipif(
    os.environ.get("SKIP_LLM_TESTS") == "1",
    reason="Skipping LLM integration tests"
)
def test_router_with_actual_llm():
    """
    Integration test with actual LLM.
    
    This test requires Ollama to be running with llama3:8b model.
    Skip with SKIP_LLM_TESTS=1 if Ollama is not available.
    """
    router = LLMRouter()
    
    if router._llm is None:
        pytest.skip("LLM not available")
    
    # Test conceptual question
    decision = router.route_query("Explain how quicksort works")
    assert decision is not None
    print(f"\nConceptual query routing: {decision.to_dict()}")
    
    # Test code generation
    decision = router.route_query("Write a function to calculate factorial")
    assert decision is not None
    print(f"\nCode generation routing: {decision.to_dict()}")
    
    # Test greeting
    decision = router.route_query("Hi there!")
    assert decision is not None
    print(f"\nGreeting routing: {decision.to_dict()}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
