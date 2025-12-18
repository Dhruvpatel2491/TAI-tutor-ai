"""
Quiz-related prompts for TAI Tutor AI.

This module contains prompt templates for quiz generation and evaluation.
All prompts include guardrails for educational quality and appropriate content.
"""

from typing import List, Optional


# Quiz Quality and Safety Guidelines
QUIZ_GUIDELINES = """
QUIZ QUALITY STANDARDS:
- Generate educationally valid questions that test genuine understanding
- Ensure questions are clear, unambiguous, and at the appropriate difficulty level
- Include plausible distractors in multiple-choice questions (not obviously wrong)
- Provide accurate, helpful explanations that teach the concept
- Avoid trick questions or unnecessarily confusing wording
- Test conceptual understanding, not just memorization
- Ensure cultural sensitivity and inclusive language

CONTENT SAFETY:
- Generate questions only on legitimate educational topics
- Do NOT create quiz content for harmful, inappropriate, or unethical subjects
- Avoid questions that could facilitate academic dishonesty if shared
- Ensure all content is age-appropriate and professional
- Maintain academic integrity in question design
"""


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
    
    prompt = f"""You are an expert educational assessment designer with expertise in creating fair, valid, 
and pedagogically sound quiz questions. Your quizzes help students learn and instructors assess understanding effectively.

{QUIZ_GUIDELINES}

REQUIREMENTS FOR THIS QUIZ:
Topic: {topic}
Number of questions: {num_questions}
Question types to include: {types_desc}
Difficulty level: {difficulty}
{plan_context}

SPECIFIC INSTRUCTIONS:
- Generate exactly {num_questions} well-crafted questions that test different aspects of {topic}
- Ensure questions progress logically and cover key concepts comprehensively
- For multiple-choice questions: create plausible distractors that represent common misconceptions
- For true/false questions: avoid absolute statements (always, never) unless technically accurate
- For short-answer questions: expect answers that demonstrate understanding, not just memorization
- Write clear explanations that would help a student learn from their mistakes

OUTPUT FORMAT: Return ONLY a valid JSON array with no additional text, markdown fences, or commentary.

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
    return f"""You are a fair and encouraging educational assessment evaluator. Your role is to determine if the 
student's answer demonstrates sufficient understanding of the concept being tested.

EVALUATION CONTEXT:
Question: {question_text}
Expected Answer: {correct_answer}
Student's Answer: {user_answer}
Question Type: {question_type}

EVALUATION CRITERIA:
- For short answers: Accept semantically equivalent answers, reasonable paraphrasing, and minor variations
- Focus on conceptual understanding, not exact wording
- Be lenient with spelling variations or minor grammatical differences
- Consider if the student demonstrates understanding of the core concept
- Mark as correct if the answer is substantially correct, even if incomplete in minor details

FEEDBACK GUIDELINES:
- Be encouraging and constructive
- If correct: Acknowledge what they got right
- If incorrect: Point out what was missing or misunderstood, and provide a brief learning hint
- Keep feedback concise (1-2 sentences)

OUTPUT FORMAT: Return ONLY a valid JSON object with these exact fields:
- "is_correct": boolean (true if answer demonstrates sufficient understanding, false otherwise)
- "feedback": string (brief, constructive feedback)

Example:
{{"is_correct": true, "feedback": "Correct! Your answer captures the key concept effectively."}}
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
