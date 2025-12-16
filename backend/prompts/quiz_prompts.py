"""
Quiz-related prompts for TAI Tutor AI.

This module contains prompt templates for quiz generation and evaluation.
"""

from typing import List, Optional


def build_quiz_generation_prompt(
    topic: str,
    plan_text: Optional[str] = None,
    num_questions: int = 5,
    question_types: Optional[List[str]] = None,
    difficulty: str = "medium"
) -> str:
    """
    Build prompt for quiz generation.
    
    Args:
        topic: Quiz topic/subject
        plan_text: Optional learning plan text for context
        num_questions: Number of questions to generate
        question_types: List of question types to include
        difficulty: Difficulty level (easy, medium, hard)
    
    Returns:
        Formatted prompt string for LLM
    """
    if question_types is None:
        question_types = ["multiple_choice", "true_false", "short_answer"]
    
    types_desc = ", ".join(question_types)
    
    plan_context = ""
    if plan_text:
        plan_context = f"""
Based on the following learning plan, generate questions that test understanding of the covered material:

--- LEARNING PLAN START ---
{plan_text[:3000]}
--- LEARNING PLAN END ---
"""
    
    prompt = f"""You are an expert educational quiz generator. Generate a quiz based on the following requirements.

Topic: {topic}
Number of questions: {num_questions}
Question types to include: {types_desc}
Difficulty level: {difficulty}
{plan_context}

Generate exactly {num_questions} questions in valid JSON format. Return ONLY a JSON array with no additional text or markdown.

Each question object must have these fields:
- "question_id": unique string identifier (e.g., "q1", "q2")
- "question_text": the question text
- "question_type": one of "multiple_choice", "true_false", or "short_answer"
- "options": array of 4 options for multiple_choice (include A, B, C, D prefixes), null for others
- "correct_answer": the correct answer (for multiple choice, include the letter prefix like "A. ...")
- "explanation": brief explanation of why the answer is correct
- "difficulty": "{difficulty}"
- "topic": "{topic}"

For true_false questions:
- options should be ["True", "False"]
- correct_answer should be "True" or "False"

For short_answer questions:
- options should be null
- correct_answer should be the expected answer (keep it concise, 1-3 words)

Example format:
[
  {{
    "question_id": "q1",
    "question_text": "What is the primary purpose of a variable in programming?",
    "question_type": "multiple_choice",
    "options": ["A. To store data", "B. To display output", "C. To create loops", "D. To define functions"],
    "correct_answer": "A. To store data",
    "explanation": "Variables are containers for storing data values.",
    "difficulty": "easy",
    "topic": "Programming Basics"
  }}
]

Return ONLY the JSON array, no markdown code blocks, no explanations before or after.
"""
    return prompt


def build_quiz_evaluation_prompt(
    question_text: str,
    correct_answer: str,
    user_answer: str,
    question_type: str = "short_answer"
) -> str:
    """
    Build prompt for evaluating a quiz answer (for short answers that need semantic matching).
    
    Args:
        question_text: The original question
        correct_answer: The expected correct answer
        user_answer: The user's submitted answer
        question_type: Type of question
    
    Returns:
        Formatted prompt for answer evaluation
    """
    return f"""You are an educational assessment evaluator. Evaluate whether the student's answer is correct.

Question: {question_text}
Correct Answer: {correct_answer}
Student's Answer: {user_answer}
Question Type: {question_type}

Evaluate if the student's answer is semantically correct (for short answers, allow paraphrasing and minor variations).

Return ONLY a JSON object with these fields:
- "is_correct": boolean (true if answer is acceptable, false otherwise)
- "feedback": brief feedback for the student

Example:
{{"is_correct": true, "feedback": "Correct! Your answer captures the key concept."}}
"""


# =============================================================================
# Fallback Templates for when LLM is unavailable
# =============================================================================

FALLBACK_QUESTION_TEMPLATES = [
    {
        "type": "multiple_choice",
        "text": "What is the primary concept behind {topic}?",
        "options": [
            "A. Understanding {topic} fundamentals",
            "B. Avoiding all related concepts",
            "C. Ignoring best practices",
            "D. None of the above"
        ],
        "answer": "A. Understanding {topic} fundamentals",
        "explanation": "The primary concept is to understand {topic} fundamentals."
    },
    {
        "type": "true_false",
        "text": "Learning {topic} requires practice and understanding.",
        "options": ["True", "False"],
        "answer": "True",
        "explanation": "Practice and understanding are essential for learning any topic."
    },
    {
        "type": "short_answer",
        "text": "Name one key aspect of {topic}.",
        "options": None,
        "answer": "Practice",
        "explanation": "Practice is a key aspect of mastering {topic}."
    },
    {
        "type": "multiple_choice",
        "text": "Which approach is best for learning {topic}?",
        "options": [
            "A. Hands-on practice",
            "B. Only reading",
            "C. Memorization only",
            "D. Avoiding examples"
        ],
        "answer": "A. Hands-on practice",
        "explanation": "Hands-on practice is the most effective approach."
    },
    {
        "type": "true_false",
        "text": "{topic} is a topic that can be learned in isolation without any context.",
        "options": ["True", "False"],
        "answer": "False",
        "explanation": "Context and connections to other concepts are important for learning."
    }
]


def get_fallback_questions(topic: str, num_questions: int = 5) -> List[dict]:
    """
    Get fallback questions when LLM is unavailable.
    
    Args:
        topic: Quiz topic
        num_questions: Number of questions to return
    
    Returns:
        List of question dictionaries
    """
    questions = []
    for i, template in enumerate(FALLBACK_QUESTION_TEMPLATES[:num_questions]):
        question = {
            "question_id": f"q{i + 1}",
            "question_text": template["text"].format(topic=topic),
            "question_type": template["type"],
            "options": [opt.format(topic=topic) for opt in template["options"]] if template["options"] else None,
            "correct_answer": template["answer"].format(topic=topic),
            "explanation": template["explanation"].format(topic=topic),
            "difficulty": "medium",
            "topic": topic
        }
        questions.append(question)
    return questions
