# LLM Router and Auto Response Type

## Overview

This feature adds an intelligent routing layer before RAG orchestration that automatically determines the best way to handle each query. When users select "Auto" as the response type, the system uses a lightweight LLM (llama3:8b) to analyze the question and make intelligent decisions about processing.

## Architecture

```
User Query (Response Type: Auto)
        ↓
  LLM Router (llama3:8b)
        ↓
   Decision Tree:
   ├─ RAG Retrieval Needed?
   │  ├─ Yes → Fetch from Vector DB
   │  │        ↓
   │  │   Response Type Decision
   │  │   ├─ Directive (conceptual questions)
   │  │   └─ Hint (problem-solving)
   │  │        ↓
   │  │   Generate Response with RAG
   │  │
   │  └─ No → Direct LLM Generation
   │     ├─ Code Generation (no retrieval)
   │     └─ General Conversation (no retrieval)
   │          ↓
   │     Generate Response without RAG
   │
   └─ Final Response to User
```

## Components

### 1. Frontend Changes (`frontend/src/components/ChatbotInterface.js`)

**Modified Response Type Options:**
- Removed: "Direct"
- Updated: "Hint", "Directive", "Auto (default)"
- Default: "auto"

```javascript
const RESPONSE_TYPES = [
  { value: 'hinting', label: 'Hint' },
  { value: 'directive', label: 'Directive' },
  { value: 'auto', label: 'Auto (default)' }
];
```

### 2. LLM Router Module (`backend/rag/llm_router.py`)

**Purpose:** Intelligent query routing and decision making

**Key Classes:**
- `QueryIntent`: Enum defining query types (RAG_RETRIEVAL, CODE_GENERATION, GENERAL_CONVERSATION)
- `ResponseTypeDecision`: Enum for response types (HINT, DIRECTIVE)
- `RoutingDecision`: Container for routing results
- `LLMRouter`: Main router class using llama3:8b

**Router Logic:**
```python
def route_query(question: str) -> RoutingDecision:
    """
    Analyzes question and returns:
    - intent: Type of query
    - needs_retrieval: Whether to use RAG
    - response_type: Hint or Directive
    - confidence: Decision confidence (0.0-1.0)
    - reasoning: Explanation
    """
```

**Fallback Strategy:**
When LLM is unavailable, uses heuristics:
- Code keywords → CODE_GENERATION
- Conceptual keywords → RAG_RETRIEVAL
- Greetings → GENERAL_CONVERSATION

### 3. Backend Integration (`backend/server_v2.py`)

**Modified Endpoint:** `/query_v3`

**Flow:**
1. Validate response_type (now accepts "auto")
2. If response_type == "auto":
   - Call LLM router
   - Get routing decision
   - Override response_type with router's choice
3. Handle based on routing:
   - **needs_retrieval=False + CODE_GENERATION**: Generate code directly without RAG
   - **needs_retrieval=False + GENERAL_CONVERSATION**: Simple conversational response
   - **needs_retrieval=True**: Standard RAG pipeline with decided response type
4. Return response with routing metadata

**Response Format:**
```json
{
  "answer": "...",
  "cached": false,
  "style": "formal",
  "response_type": "directive",
  "original_response_type": "auto",
  "length": "short",
  "used_rag": true,
  "routing": {
    "intent": "rag_retrieval",
    "needs_retrieval": true,
    "response_type": "directive",
    "confidence": 0.9,
    "reasoning": "Conceptual question about data structures"
  }
}
```

### 4. Prompt Updates (`backend/prompts/chat_prompts.py`)

**Added "auto" to TYPE_TEMPLATES:**
```python
"auto": """AUTO MODE: This response type is determined automatically by an intelligent router.
The router analyzes the question and chooses the most appropriate teaching approach:
- For conceptual questions: Uses Directive method to provide clear explanations
- For problem-solving tasks: Provides hints to scaffold learning
- For code generation: May generate directly without retrieval if appropriate
This template should not be used directly - it's replaced by 'hinting' or 'directive' after routing."""
```

### 5. Validation Updates (`backend/rag/retrieval_chat.py`)

**Updated `validate_response_type()`:**
```python
def validate_response_type(response_type: Optional[str]) -> str:
    """Validate and normalize response type parameter."""
    response_type = (response_type or "auto").lower()
    if response_type not in ["hinting", "directive", "auto"]:
        return "auto"
    return response_type
```

## Router Configuration

**Model:** `llama3:8b`
- Chosen for fast inference while maintaining good decision quality
- Small enough for quick routing decisions
- Accurate enough for intent classification

**Temperature:** `0.1`
- Low temperature for consistent routing decisions
- Reduces randomness in classification

**Timeout:** `30 seconds`
- Reasonable timeout for routing LLM call
- Falls back to heuristics on timeout

## Router Prompt Template

The router uses a structured prompt that asks the LLM to:
1. Identify query intent (RAG/code/conversation)
2. Determine if retrieval is needed
3. Select response type (hint/directive)
4. Provide confidence score
5. Explain reasoning

Response format: JSON with required fields

## Use Cases

### Case 1: Conceptual Question
**Query:** "What is a binary search tree?"
**Router Decision:**
- Intent: RAG_RETRIEVAL
- Needs Retrieval: True
- Response Type: Directive
- Reasoning: "Conceptual question about data structures, benefits from clear explanations"

**Processing:** Uses RAG to fetch course materials, applies Directive method

### Case 2: Code Generation
**Query:** "Write a Python function to reverse a string"
**Router Decision:**
- Intent: CODE_GENERATION
- Needs Retrieval: False
- Response Type: Hint
- Reasoning: "Code generation without course-specific context"

**Processing:** Generates code directly with LLM, skips RAG retrieval

### Case 3: Algorithm Explanation
**Query:** "How does quicksort work?"
**Router Decision:**
- Intent: RAG_RETRIEVAL
- Needs Retrieval: True
- Response Type: Directive
- Reasoning: "Algorithm explanation likely in course materials"

**Processing:** Retrieves algorithm content from PDFs/slides, uses Directive teaching

### Case 4: General Conversation
**Query:** "Hello, how are you?"
**Router Decision:**
- Intent: GENERAL_CONVERSATION
- Needs Retrieval: False
- Response Type: Hint
- Reasoning: "Simple greeting"

**Processing:** Direct conversational response, no RAG needed

## Benefits

1. **Optimized Performance**: Skips expensive RAG retrieval when not needed
2. **Better UX**: Automatic selection of teaching method based on question type
3. **Resource Efficiency**: Reduces unnecessary vector DB queries
4. **Intelligent Teaching**: Matches pedagogy to question type
5. **Fallback Safety**: Heuristic-based fallback if LLM routing fails

## Testing

### Unit Tests (`backend_test/test_llm_router.py`)
- Router initialization
- Fallback routing logic
- RoutingDecision serialization
- Integration with actual LLM (optional)

### Manual Integration Test (`backend_test/manual_router_test.py`)
Run after starting backend:
```bash
python backend_test/manual_router_test.py
```

Tests various query types and verifies routing decisions.

## Configuration

### Environment Variables
None required - uses defaults from `config.py`

### Model Requirements
- `llama3:8b` must be available in Ollama
- If not available, falls back to heuristic routing

### Performance Tuning
Adjust in `backend/rag/llm_router.py`:
- `ROUTER_MODEL`: Change routing model
- `ROUTER_TEMPERATURE`: Adjust consistency vs creativity
- `ROUTER_MAX_TOKENS`: Limit response length
- `ROUTER_TIMEOUT`: Adjust timeout before fallback

## Migration Notes

### Breaking Changes
- Response type "direct" removed from frontend
- Default response type changed from "direct" to "auto"

### Backward Compatibility
- Old endpoints still work
- "direct" in API calls is treated as "auto"
- No database schema changes

### Deployment Steps
1. Update frontend build
2. Deploy backend with new router module
3. Ensure llama3:8b is pulled in Ollama
4. Test with integration script
5. Monitor routing decisions in logs

## Monitoring

### Log Messages
```
INFO: Router decision: {"intent": "rag_retrieval", ...}
INFO: Handling code generation without RAG retrieval
INFO: Handling general conversation without RAG retrieval
WARNING: Router failed, using default RAG path
```

### Metrics to Track
- Routing decision distribution (RAG vs direct)
- Router confidence scores
- Fallback frequency
- Response time with/without RAG

## Future Enhancements

1. **Router Model Selection**: Allow configuration of routing model
2. **Confidence Thresholds**: Skip RAG only above certain confidence
3. **Learning from Feedback**: Train router on user feedback
4. **Multi-turn Context**: Better routing with conversation history
5. **Hybrid Approach**: Combine RAG and direct generation
6. **Cost Optimization**: Track and optimize token usage

## Troubleshooting

### Router Always Falls Back
- Check if Ollama is running: `ollama list`
- Verify llama3:8b is available: `ollama pull llama3:8b`
- Check logs for connection errors

### Incorrect Routing Decisions
- Review routing prompt template
- Adjust temperature (currently 0.1)
- Check router model performance

### Slow Response Times
- Reduce router timeout
- Use faster routing model
- Enable response caching

## References

- Router implementation: `backend/rag/llm_router.py`
- Query endpoint: `backend/server_v2.py` (query_v3)
- Frontend UI: `frontend/src/components/ChatbotInterface.js`
- Prompt templates: `backend/prompts/chat_prompts.py`
