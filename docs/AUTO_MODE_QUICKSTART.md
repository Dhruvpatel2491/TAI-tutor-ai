# Quick Start: Using Auto Response Type

## Overview
The new "Auto" response type automatically determines the best way to handle your query using an intelligent LLM router.

## How to Use

### Frontend (ChatbotInterface)
1. Open the chatbot interface
2. Look for "Response Type" dropdown
3. Select "Auto (default)" (or leave as default)
4. Ask your question

### API (Direct)
```bash
curl -X POST http://localhost:5001/query_v3 \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is a binary search tree?",
    "response_type": "auto",
    "style": "casual",
    "length": "short"
  }'
```

## What Happens

### Query Flow
```
Your Question
    ↓
LLM Router (llama3:8b)
    ↓
Decision:
├─ Needs RAG? → Yes → Fetch from knowledge base → Socratic/Hint response
└─ Needs RAG? → No  → Direct LLM generation → Code or conversation
    ↓
Your Answer (+ routing metadata)
```

## Example Queries

### Conceptual Question (Uses RAG + Socratic)
```json
{
  "question": "What is recursion?",
  "response_type": "auto"
}
```
**Router Decision:** Retrieves course materials, uses Socratic method

### Code Generation (Skips RAG + Hint)
```json
{
  "question": "Write a function to reverse a string",
  "response_type": "auto"
}
```
**Router Decision:** Generates code directly without retrieval

### Algorithm Explanation (Uses RAG + Socratic)
```json
{
  "question": "How does bubble sort work?",
  "response_type": "auto"
}
```
**Router Decision:** Retrieves algorithm docs, uses guided teaching

### Greeting (Skips RAG)
```json
{
  "question": "Hello!",
  "response_type": "auto"
}
```
**Router Decision:** Simple conversational response

## Response Format

When using auto mode, responses include routing metadata:

```json
{
  "answer": "Let me guide you through understanding binary search trees...",
  "cached": false,
  "style": "casual",
  "response_type": "socratic",
  "original_response_type": "auto",
  "length": "short",
  "used_rag": true,
  "routing": {
    "intent": "rag_retrieval",
    "needs_retrieval": true,
    "response_type": "socratic",
    "confidence": 0.9,
    "reasoning": "Conceptual question about data structures"
  }
}
```

## Benefits

- **Automatic**: No need to choose between Hint and Socratic
- **Efficient**: Skips RAG when not needed
- **Smart**: Matches teaching style to question type
- **Transparent**: See routing decision in response

## Testing

### Start Backend
```bash
cd backend
python server_v2.py
```

### Run Integration Test
```bash
python backend_test/manual_router_test.py
```

This will test:
- ✓ Conceptual questions
- ✓ Code generation
- ✓ Algorithm explanations
- ✓ Greetings

## Troubleshooting

### Router Not Working
- Ensure Ollama is running: `ollama list`
- Pull routing model: `ollama pull llama3:8b`
- Check backend logs for router errors

### Unexpected Routing Decisions
- Review response metadata (`routing` field)
- Check `reasoning` for explanation
- Consider adjusting router temperature in `backend/rag/llm_router.py`

### Slow Responses
- Router adds ~2-5 seconds for decision
- Falls back to heuristics on timeout
- Consider caching for repeated queries

## Manual Override

You can still manually select response type:

```json
{
  "question": "What is a binary search tree?",
  "response_type": "hinting"  // Force hint mode
}
```

Or:

```json
{
  "question": "What is a binary search tree?",
  "response_type": "socratic"  // Force socratic mode
}
```

## More Information

- Full documentation: `docs/LLM_ROUTER.md`
- Router code: `backend/rag/llm_router.py`
- Integration: `backend/server_v2.py` (query_v3 endpoint)
- Tests: `backend_test/test_llm_router.py`
