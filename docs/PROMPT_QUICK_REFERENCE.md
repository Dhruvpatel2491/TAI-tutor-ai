# Prompt System Quick Reference Guide

## Overview
TAI Tutor AI uses a sophisticated prompt system with built-in guardrails to ensure safe, effective, and educationally sound AI interactions.

---

## Chat System (`chat_prompts.py`)

### Basic Usage
```python
from backend.prompts.chat_prompts import ChatPrompter

# Create prompter with preferences
prompter = ChatPrompter(
    style="formal",        # "formal", "casual", or "technical"
    response_type="direct", # "direct", "hinting", or "directive"
    length="medium"        # "short", "medium", or "long"
)

# Check content safety (NEW!)
is_safe, warning = prompter.check_content_safety(user_question)
if not is_safe:
    return {"error": warning}

# Build and use prompt
prompt = prompter.build_full_prompt(user_question)
# Send to LLM...
```

### Response Styles
| Style | Best For | Tone |
|-------|----------|------|
| **Formal** | Academic assignments, formal learning | Professional, structured |
| **Casual** | Exploratory learning, beginners | Friendly, approachable |
| **Technical** | Advanced topics, deep dives | Precise, detailed |

### Response Types
| Type | Best For | Approach |
|------|----------|----------|
| **Direct** | Quick answers, clarifications | Complete explanation |
| **Hinting** | Homework, building problem-solving skills | Strategic hints, guiding questions |
| **Directive** | Clear explanations, structured learning | Direct, comprehensive instruction |

### Content Safety
**Automatically blocks:**
- Academic dishonesty requests
- Harmful/malicious code
- Security bypasses
- Discriminatory content
- Medical/legal/financial advice

**Allows with context:**
- Educational security topics
- Ethical hacking learning
- Understanding vulnerabilities

---

## CodeQuest System (`codequest_prompts.py`)

### Challenge Generation
```python
from backend.prompts.codequest_prompts import build_challenge_set_prompt

prompt = build_challenge_set_prompt(
    title="Python Basics",
    language="python",
    difficulty="beginner",
    track="Python",
    concepts=["variables", "loops"],
    num_challenges=5
)
# Returns: {"system": "...", "user": "..."}
```

### Solution Generation
```python
from backend.prompts.codequest_prompts import build_solution_prompt

prompt = build_solution_prompt(
    language="python",
    prompt="Write a function to reverse a string",
    starter_code="def reverse_string(s):\n    pass"
)
```

### Safety Features
- ✅ Only educational challenges
- ✅ No malware/exploit generation
- ✅ Secure coding emphasis
- ✅ Best practices in solutions

---

## Planner System (`planner_prompts.py`)

### Generate Learning Plan
```python
from backend.prompts.planner_prompts import build_plan_prompt

prompt = build_plan_prompt(
    requirement="Learn Python in 2 weeks, 1 hour per day",
    user_id="student@example.com",
    original_plan=None,  # Optional: for editing existing plans
    edit_instructions=None  # Optional: specific edits
)
```

### Fallback Plan
```python
from backend.prompts.planner_prompts import generate_fallback_plan

plan = generate_fallback_plan(
    requirement="Learn Python basics",
    user_id="student@example.com"
)
# Returns deterministic plan when LLM unavailable
```

### Plan Features
- ✅ Realistic timeframes with buffers
- ✅ Evidence-based learning principles
- ✅ Concrete exercises and deliverables
- ✅ Self-check questions
- ✅ Resource recommendations

---

## Quiz System (`quiz_prompts.py`)

### Generate Quiz
```python
from backend.prompts.quiz_prompts import build_quiz_generation_prompt

prompt = build_quiz_generation_prompt(
    topic="Python Lists",
    plan_text="...",  # Optional: learning plan for context
    num_questions=5,
    question_types=["multiple_choice", "true_false", "short_answer"],
    difficulty="medium"
)
```

### Evaluate Answer
```python
from backend.prompts.quiz_prompts import build_quiz_evaluation_prompt

prompt = build_quiz_evaluation_prompt(
    question_text="What is a list in Python?",
    correct_answer="A mutable, ordered collection of items",
    user_answer="An ordered sequence that can be changed",
    question_type="short_answer"
)
# Returns: {"is_correct": true/false, "feedback": "..."}
```

### Fallback Questions
```python
from backend.prompts.quiz_prompts import get_fallback_questions

questions = get_fallback_questions(
    topic="Python Basics",
    num_questions=5
)
# Returns list of fallback questions when LLM unavailable
```

---

## Guardrails Summary

### What's Blocked
❌ Academic dishonesty (solving homework/exams)  
❌ Harmful code (malware, exploits, attacks)  
❌ Security bypasses and unauthorized access  
❌ Discriminatory, hateful, violent content  
❌ Plagiarism and copyright infringement  
❌ Medical, legal, financial advice (outside education)  

### What's Allowed
✅ Educational security concepts  
✅ Understanding vulnerabilities (defensive perspective)  
✅ Ethical hacking learning  
✅ Secure coding best practices  
✅ General educational content  

---

## Best Practices

### For Students
1. **Try First**: Attempt problems before asking for help
2. **Use Hints**: Start with "hinting" mode for homework
3. **Verify Understanding**: Don't just copy answers
4. **Ask Follow-ups**: Dig deeper with questions
5. **Cite AI Help**: When required by your institution

### For Educators
1. **Set Expectations**: Clarify appropriate AI usage
2. **Monitor Usage**: Review student interactions
3. **Supplement Teaching**: Use as enhancement, not replacement
4. **Adjust Settings**: Choose response types based on learning goals
5. **Provide Guidance**: Teach effective AI tutoring use

### For Developers
1. **Validate Outputs**: Always parse and check LLM responses
2. **Handle Errors**: Implement fallback mechanisms
3. **Test Safety**: Verify guardrails with edge cases
4. **Monitor Metrics**: Track prompt performance
5. **Iterate**: Refine based on real usage

---

## Common Patterns

### Multi-turn Conversation
```python
# Initialize with history
prompter = ChatPrompter(style="casual", response_type="hinting")

# Add previous messages
prompter.add_message("user", "What is a variable?")
prompter.add_message("assistant", "A variable is like a labeled box...")

# Continue conversation
new_prompt = prompter.build_full_prompt("How do I create one in Python?")
```

### Custom Response Preferences
```python
# Different contexts, different settings
homework_prompter = ChatPrompter(
    style="formal", 
    response_type="hinting", 
    length="medium"
)

quick_answer_prompter = ChatPrompter(
    style="casual", 
    response_type="direct", 
    length="short"
)

deep_dive_prompter = ChatPrompter(
    style="technical", 
    response_type="directive", 
    length="long"
)
```

### Safety-First Flow
```python
def process_question(user_input, user_prefs):
    # 1. Create prompter
    prompter = ChatPrompter(**user_prefs)
    
    # 2. Check safety
    is_safe, warning = prompter.check_content_safety(user_input)
    if not is_safe:
        return {"error": warning, "safe": False}
    
    # 3. Build prompt
    prompt = prompter.build_full_prompt(user_input)
    
    # 4. Send to LLM (your implementation)
    response = call_llm(prompt)
    
    # 5. Return result
    return {"response": response, "safe": True}
```

---

## Troubleshooting

### Issue: Content blocked unnecessarily
**Solution**: 
- Rephrase with educational context
- Use phrases like "learn about", "understand how to protect against"
- Frame in defensive/educational perspective

### Issue: Prompts too verbose
**Solution**:
- Use "short" length setting
- Choose "direct" response type
- Request specific information in question

### Issue: Responses not helpful
**Solution**:
- Provide more context in question
- Try different response type (hinting vs direct)
- Include conversation history for continuity
- Adjust style based on technical level

### Issue: LLM unavailable
**Solution**:
- System automatically uses fallback mechanisms
- Fallback plans/quizzes provide basic functionality
- Check logs for actual errors
- Verify LLM service connection

---

## API Integration Examples

### REST API Usage
```python
# Chat endpoint
POST /api/chat
{
    "question": "What is a Python list?",
    "style": "casual",
    "response_type": "direct",
    "length": "medium",
    "history": []
}

# CodeQuest challenge generation
POST /api/codequest/generate
{
    "title": "Python Basics",
    "language": "python",
    "difficulty": "beginner",
    "num_challenges": 3
}

# Learning plan generation
POST /api/planner/generate
{
    "requirement": "Learn Python in 2 weeks",
    "user_id": "student123"
}

# Quiz generation
POST /api/quiz/generate
{
    "topic": "Python Lists",
    "num_questions": 5,
    "difficulty": "medium"
}
```

---

## Version Information

**Current Version**: 2.0 (Post-Refactoring with Guardrails)  
**Last Updated**: December 17, 2025  
**Compatible With**: TAI Tutor AI v2.x

---

## Additional Resources

- **Full Documentation**: `docs/prompts.txt`
- **Refactoring Summary**: `docs/PROMPT_REFACTORING_SUMMARY.md`
- **Backend Architecture**: `docs/BACKEND_REFACTORING.md`
- **API Documentation**: `docs/README.md`

---

## Quick Command Reference

```bash
# Run backend server
cd backend && python server_v2.py

# Run tests
pytest backend_test/

# Check prompt files
ls backend/prompts/

# View documentation
cat docs/prompts.txt
```

---

**For support, issues, or questions**: Refer to project documentation or contact the development team.
