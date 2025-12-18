"""
LLM Router for TAI Tutor AI.

This module provides intelligent routing logic that sits before RAG orchestration.
When a user selects "Auto" response type, this router:
1. Analyzes the user's question using a lightweight LLM (llama3:8b)
2. Determines if RAG retrieval is needed from the vector database
3. Decides whether the query is for code generation without retrieval
4. Selects the appropriate response type (hint vs directive)

The router acts as a decision layer to optimize query handling and provide
context-appropriate responses.
"""

import logging
import json
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger("backend.rag.llm_router")

# Try to import LlamaIndex components
try:
    from llama_index.llms.ollama import Ollama
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    logger.warning("LlamaIndex not available. Router functionality limited.")


# Router model configuration
ROUTER_MODEL = "llama3:8b"
ROUTER_TEMPERATURE = 0.1  # Low temperature for consistent routing decisions
ROUTER_MAX_TOKENS = 500
ROUTER_TIMEOUT = 30


class QueryIntent(Enum):
    """Types of query intents the router can identify."""
    RAG_RETRIEVAL = "rag_retrieval"  # Needs knowledge from vector DB
    CODE_GENERATION = "code_generation"  # Generate code without retrieval
    GENERAL_CONVERSATION = "general_conversation"  # Simple conversational query


class ResponseTypeDecision(Enum):
    """Response type decisions for RAG queries."""
    HINT = "hinting"
    DIRECTIVE = "directive"


class RoutingDecision:
    """
    Container for routing decision results.
    
    Attributes:
        intent: The determined query intent
        needs_retrieval: Whether RAG retrieval is required
        response_type: Recommended response type (hint or directive)
        confidence: Confidence score of the decision (0.0 to 1.0)
        reasoning: Brief explanation of the decision
    """
    
    def __init__(
        self,
        intent: QueryIntent,
        needs_retrieval: bool,
        response_type: ResponseTypeDecision,
        confidence: float = 0.8,
        reasoning: str = ""
    ):
        self.intent = intent
        self.needs_retrieval = needs_retrieval
        self.response_type = response_type
        self.confidence = confidence
        self.reasoning = reasoning
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent": self.intent.value,
            "needs_retrieval": self.needs_retrieval,
            "response_type": self.response_type.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning
        }


# Router prompt template
ROUTER_PROMPT_TEMPLATE = """You are an intelligent query router for an educational AI tutor system. 
Your job is to analyze student questions and determine the best way to handle them.

Analyze the following question and provide a routing decision in JSON format.

Question: "{question}"

Determine:
1. Intent: What is the student trying to accomplish?
   - "rag_retrieval": Question needs information from course materials/documentation (concepts, definitions, explanations from PDFs/slides)
   - "code_generation": Student wants code written/generated (without needing course-specific knowledge)
   - "general_conversation": Simple greeting, clarification, or general chat

2. Needs Retrieval: Does this require looking up information in the knowledge base?
   - true: If the question asks about specific course content, algorithms, concepts covered in class
   - false: If it's a general programming question, code generation, or simple conversation

3. Response Type: How should we teach this student?
   - "hinting": For questions where the student should work through it themselves (homework-style)
   - "directive": For conceptual questions where clear, direct explanations help learning (why/how questions)

4. Confidence: How confident are you in this routing decision? (0.0 to 1.0)

5. Reasoning: Brief explanation of your decision (one sentence)

Examples:

Question: "What is a binary search tree?"
{{
  "intent": "rag_retrieval",
  "needs_retrieval": true,
  "response_type": "directive",
  "confidence": 0.9,
  "reasoning": "Conceptual question about a data structure likely covered in course materials"
}}

Question: "Write a Python function to reverse a string"
{{
  "intent": "code_generation",
  "needs_retrieval": false,
  "response_type": "hinting",
  "confidence": 0.85,
  "reasoning": "Code generation request without course-specific context"
}}

Question: "How does the bubble sort algorithm work?"
{{
  "intent": "rag_retrieval",
  "needs_retrieval": true,
  "response_type": "directive",
  "confidence": 0.9,
  "reasoning": "Algorithm explanation likely in course materials, benefits from clear explanations"
}}

Question: "Hello, how are you?"
{{
  "intent": "general_conversation",
  "needs_retrieval": false,
  "response_type": "hinting",
  "confidence": 1.0,
  "reasoning": "Simple greeting, no retrieval or complex teaching needed"
}}

Now analyze this question and respond ONLY with the JSON object (no other text):

Question: "{question}"
"""


class LLMRouter:
    """
    Intelligent query router using LLM for decision making.
    
    This router analyzes incoming queries and determines the optimal
    handling strategy before RAG orchestration.
    """
    
    def __init__(
        self,
        model: str = ROUTER_MODEL,
        temperature: float = ROUTER_TEMPERATURE,
        max_tokens: int = ROUTER_MAX_TOKENS,
        timeout: int = ROUTER_TIMEOUT
    ):
        """
        Initialize the LLM router.
        
        Args:
            model: LLM model to use for routing decisions
            temperature: Temperature for generation (low for consistency)
            max_tokens: Maximum tokens in response
            timeout: Timeout for LLM calls in seconds
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        if not LLAMA_INDEX_AVAILABLE:
            logger.error("LlamaIndex not available. Router cannot function.")
            self._llm = None
        else:
            try:
                self._llm = Ollama(
                    model=self.model,
                    temperature=self.temperature,
                    request_timeout=self.timeout
                )
                logger.info(f"LLM Router initialized with model: {self.model}")
            except Exception as e:
                logger.exception(f"Failed to initialize LLM router: {e}")
                self._llm = None
    
    def route_query(
        self,
        question: str,
        conversation_history: Optional[list] = None
    ) -> RoutingDecision:
        """
        Route a query and determine handling strategy.
        
        Args:
            question: The user's question
            conversation_history: Optional conversation history for context
            
        Returns:
            RoutingDecision with intent, retrieval needs, and response type
        """
        if not self._llm:
            logger.warning("LLM not available, using fallback routing")
            return self._fallback_routing(question)
        
        try:
            # Build the routing prompt
            prompt = ROUTER_PROMPT_TEMPLATE.format(question=question)
            
            # Get LLM decision
            response = self._llm.complete(prompt)
            response_text = str(response).strip()
            
            # Parse JSON response
            routing_data = self._parse_routing_response(response_text)
            
            if routing_data:
                return self._create_decision_from_data(routing_data)
            
            else:
                logger.warning("Failed to parse routing response, using fallback")
                return self._fallback_routing(question)
                
        except Exception as e:
            logger.exception(f"Error in query routing: {e}")
            return self._fallback_routing(question)
    
    def _parse_routing_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse the LLM's JSON response.
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            # Try to extract JSON from response
            # Sometimes LLM adds explanation before/after JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                return None
            
            json_str = response_text[start_idx:end_idx + 1]
            data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["intent", "needs_retrieval", "response_type", "confidence"]
            if all(field in data for field in required_fields):
                return data
            else:
                logger.warning(f"Missing required fields in routing response: {data}")
                return None
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from routing response: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error parsing routing response: {e}")
            return None
    
    def _create_decision_from_data(self, data: Dict[str, Any]) -> RoutingDecision:
        """
        Create a RoutingDecision from parsed data.
        
        Args:
            data: Parsed routing response data
            
        Returns:
            RoutingDecision object
        """
        try:
            # Map intent string to enum
            intent_str = data["intent"]
            if intent_str == "rag_retrieval":
                intent = QueryIntent.RAG_RETRIEVAL
            elif intent_str == "code_generation":
                intent = QueryIntent.CODE_GENERATION
            else:
                intent = QueryIntent.GENERAL_CONVERSATION
            
            # Map response type string to enum
            response_type_str = data["response_type"]
            if response_type_str == "directive":
                response_type = ResponseTypeDecision.DIRECTIVE
            else:
                response_type = ResponseTypeDecision.HINT
            
            needs_retrieval = bool(data["needs_retrieval"])
            confidence = float(data.get("confidence", 0.8))
            reasoning = data.get("reasoning", "")
            
            return RoutingDecision(
                intent=intent,
                needs_retrieval=needs_retrieval,
                response_type=response_type,
                confidence=confidence,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.exception(f"Error creating decision from data: {e}")
            return self._fallback_routing("")
    
    def _fallback_routing(self, question: str) -> RoutingDecision:
        """
        Fallback routing logic using simple heuristics.
        
        Used when LLM is unavailable or fails.
        
        Args:
            question: The user's question
            
        Returns:
            RoutingDecision based on heuristics
        """
        question_lower = question.lower()
        
        # Heuristic: Code generation keywords
        code_keywords = ["write", "create", "generate", "implement", "code", "function", "class"]
        is_code_gen = any(kw in question_lower for kw in code_keywords)
        
        # Heuristic: Conceptual question keywords
        concept_keywords = ["what is", "how does", "explain", "why", "difference between"]
        is_conceptual = any(kw in question_lower for kw in concept_keywords)
        
        # Heuristic: Greeting/conversation keywords
        greeting_keywords = ["hello", "hi", "hey", "thanks", "thank you"]
        is_greeting = any(kw in question_lower for kw in greeting_keywords)
        
        if is_greeting:
            return RoutingDecision(
                intent=QueryIntent.GENERAL_CONVERSATION,
                needs_retrieval=False,
                response_type=ResponseTypeDecision.HINT,
                confidence=0.9,
                reasoning="Simple greeting detected"
            )
        elif is_code_gen and not is_conceptual:
            return RoutingDecision(
                intent=QueryIntent.CODE_GENERATION,
                needs_retrieval=False,
                response_type=ResponseTypeDecision.HINT,
                confidence=0.7,
                reasoning="Code generation request (fallback heuristic)"
            )
        else:
            # Default: assume needs retrieval and use directive method
            return RoutingDecision(
                intent=QueryIntent.RAG_RETRIEVAL,
                needs_retrieval=True,
                response_type=ResponseTypeDecision.DIRECTIVE,
                confidence=0.6,
                reasoning="Default routing to RAG with directive method (fallback heuristic)"
            )


# Global router instance
_router_instance: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """
    Get or create the global router instance.
    
    Returns:
        LLMRouter instance
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance


def route_query(
    question: str,
    conversation_history: Optional[list] = None
) -> RoutingDecision:
    """
    Convenience function to route a query using the global router.
    
    Args:
        question: The user's question
        conversation_history: Optional conversation history
        
    Returns:
        RoutingDecision object
    """
    router = get_router()
    return router.route_query(question, conversation_history)
