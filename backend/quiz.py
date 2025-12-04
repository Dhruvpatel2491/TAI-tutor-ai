"""
Quiz module for TAI-tutor-ai.

This module handles quiz generation, storage, and retrieval using Ollama's 
generative capabilities (not retrieved embeddings).

Quiz data is stored in: user_data/quiz/{user_id}/{quiz_title}.json

References:
- https://docs.ollama.com/capabilities/thinking
- https://docs.ollama.com/capabilities/structured-outputs
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import os
import json
import hashlib
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from llama_index.llms.ollama import Ollama
except ImportError:
    Ollama = None


# ============================================================================
# Pydantic Models for Quiz Data
# ============================================================================

class QuizQuestion(BaseModel):
    """A single quiz question."""
    question_id: str
    question_text: str
    question_type: str = Field(
        default="multiple_choice",
        description="Type: multiple_choice, true_false, short_answer"
    )
    options: Optional[List[str]] = Field(
        default=None,
        description="Options for multiple choice questions"
    )
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: str = Field(
        default="medium",
        description="Difficulty: easy, medium, hard"
    )
    topic: Optional[str] = None


class UserResponse(BaseModel):
    """User's response to a quiz question."""
    question_id: str
    user_answer: str
    is_correct: bool
    time_taken_seconds: Optional[float] = None


class QuizResult(BaseModel):
    """Complete quiz result with user performance."""
    quiz_id: str
    user_id: str
    quiz_title: str
    questions: List[QuizQuestion]
    user_responses: List[UserResponse] = Field(default_factory=list)
    score: float = 0.0
    total_questions: int = 0
    correct_answers: int = 0
    date_taken: datetime
    date_completed: Optional[datetime] = None
    learning_plan_reference: Optional[str] = None
    status: str = Field(
        default="in_progress",
        description="Status: in_progress, completed, abandoned"
    )


class QuizMetadata(BaseModel):
    """Lightweight quiz metadata for listing."""
    quiz_id: str
    quiz_title: str
    topic: str
    total_questions: int
    score: Optional[float] = None
    status: str
    date_taken: datetime
    date_completed: Optional[datetime] = None


# ============================================================================
# Quiz Storage Helpers
# ============================================================================

# Base directory for quiz data
_ROOT_QUIZ_DIR = Path(__file__).resolve().parent.parent / "user_data" / "quiz"


def _ensure_quiz_dir(user_id: str) -> Path:
    """Ensure quiz directory exists for user."""
    user_dir = _ROOT_QUIZ_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _safe_filename(title: str) -> str:
    """Convert quiz title to safe filename."""
    # Replace unsafe characters
    safe = title.replace(" ", "_").replace("/", "_").replace("\\", "_")
    safe = "".join(c for c in safe if c.isalnum() or c in "_-.")
    return safe[:100] if len(safe) > 100 else safe


def _generate_quiz_id(user_id: str, title: str) -> str:
    """Generate unique quiz ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    hash_input = f"{user_id}_{title}_{timestamp}"
    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"quiz_{timestamp}_{short_hash}"


def save_quiz(user_id: str, quiz: QuizResult) -> Path:
    """Save quiz result to disk."""
    user_dir = _ensure_quiz_dir(user_id)
    filename = f"{_safe_filename(quiz.quiz_title)}_{quiz.quiz_id}.json"
    file_path = user_dir / filename
    
    try:
        data = quiz.model_dump()
        # Convert datetime to ISO strings
        if isinstance(data.get("date_taken"), datetime):
            data["date_taken"] = data["date_taken"].isoformat()
        if isinstance(data.get("date_completed"), datetime):
            data["date_completed"] = data["date_completed"].isoformat()
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Saved quiz to {file_path}")
        return file_path
    except Exception as e:
        logger.exception(f"Failed to save quiz: {e}")
        raise


def load_quiz(user_id: str, quiz_id: str) -> Optional[QuizResult]:
    """Load quiz by ID."""
    user_dir = _ROOT_QUIZ_DIR / str(user_id)
    if not user_dir.exists():
        return None
    
    # Search for file containing quiz_id
    for file_path in user_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("quiz_id") == quiz_id:
                # Parse dates
                if data.get("date_taken"):
                    data["date_taken"] = datetime.fromisoformat(data["date_taken"].replace("Z", "+00:00"))
                if data.get("date_completed"):
                    data["date_completed"] = datetime.fromisoformat(data["date_completed"].replace("Z", "+00:00"))
                return QuizResult(**data)
        except Exception as e:
            logger.warning(f"Failed to load quiz from {file_path}: {e}")
            continue
    
    return None


def list_quizzes(user_id: str) -> List[QuizMetadata]:
    """List all quizzes for a user."""
    user_dir = _ROOT_QUIZ_DIR / str(user_id)
    if not user_dir.exists():
        return []
    
    results = []
    for file_path in sorted(user_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Parse date
            date_taken = data.get("date_taken", "")
            if date_taken:
                try:
                    date_taken = datetime.fromisoformat(date_taken.replace("Z", "+00:00"))
                except Exception:
                    date_taken = datetime.now(timezone.utc)
            else:
                date_taken = datetime.now(timezone.utc)
            
            date_completed = data.get("date_completed")
            if date_completed:
                try:
                    date_completed = datetime.fromisoformat(date_completed.replace("Z", "+00:00"))
                except Exception:
                    date_completed = None
            
            # Extract topic from first question or use title
            topic = data.get("quiz_title", "General")
            questions = data.get("questions", [])
            if questions and isinstance(questions[0], dict):
                topic = questions[0].get("topic", topic)
            
            metadata = QuizMetadata(
                quiz_id=data.get("quiz_id", file_path.stem),
                quiz_title=data.get("quiz_title", file_path.stem),
                topic=topic,
                total_questions=data.get("total_questions", len(questions)),
                score=data.get("score"),
                status=data.get("status", "unknown"),
                date_taken=date_taken,
                date_completed=date_completed
            )
            results.append(metadata)
        except Exception as e:
            logger.warning(f"Failed to read quiz metadata from {file_path}: {e}")
            continue
    
    return results


def delete_quiz(user_id: str, quiz_id: str) -> bool:
    """Delete a quiz by ID."""
    user_dir = _ROOT_QUIZ_DIR / str(user_id)
    if not user_dir.exists():
        return False
    
    for file_path in user_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("quiz_id") == quiz_id:
                file_path.unlink()
                logger.info(f"Deleted quiz {quiz_id} from {file_path}")
                return True
        except Exception:
            continue
    
    return False


# ============================================================================
# Quiz Generation Prompts
# ============================================================================

def _build_quiz_generation_prompt(
    topic: str,
    plan_text: Optional[str] = None,
    num_questions: int = 5,
    question_types: Optional[List[str]] = None,
    difficulty: str = "medium"
) -> str:
    """Build prompt for quiz generation."""
    
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


def _parse_quiz_response(response_text: str) -> List[Dict[str, Any]]:
    """Parse LLM response into quiz questions."""
    # Clean the response
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's just ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    
    # Try to find JSON array
    start_idx = text.find("[")
    end_idx = text.rfind("]")
    
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx:end_idx + 1]
    
    try:
        questions = json.loads(text)
        if isinstance(questions, list):
            return questions
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse quiz JSON: {e}")
    
    return []


# ============================================================================
# Quiz Generation Function
# ============================================================================

def generate_quiz(
    user_id: str,
    topic: str,
    plan_text: Optional[str] = None,
    plan_reference: Optional[str] = None,
    num_questions: int = 5,
    question_types: Optional[List[str]] = None,
    difficulty: str = "medium",
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    timeout: int = 300
) -> QuizResult:
    """
    Generate a quiz using Ollama's generative mode.
    
    Args:
        user_id: User identifier
        topic: Quiz topic/title
        plan_text: Optional learning plan text for context
        plan_reference: Optional reference to learning plan ID
        num_questions: Number of questions to generate (default 5)
        question_types: List of question types to include
        difficulty: easy, medium, or hard
        model: Ollama model to use
        temperature: Generation temperature
        max_tokens: Max tokens for generation
        timeout: Request timeout in seconds
    
    Returns:
        QuizResult with generated questions
    """
    if question_types is None:
        question_types = ["multiple_choice", "true_false", "short_answer"]
    
    # Generate quiz ID and metadata
    quiz_id = _generate_quiz_id(user_id, topic)
    now = datetime.now(timezone.utc)
    
    # Build generation prompt
    prompt = _build_quiz_generation_prompt(
        topic=topic,
        plan_text=plan_text,
        num_questions=num_questions,
        question_types=question_types,
        difficulty=difficulty
    )
    
    questions = []
    
    if Ollama is None:
        logger.warning("Ollama not available, using fallback quiz generation")
        questions = _generate_fallback_questions(topic, num_questions, question_types, difficulty)
    else:
        try:
            model_name = model or os.environ.get("QUIZ_MODEL") or os.environ.get("OLLAMA_LLM") or "llama3:8b"
            llm = Ollama(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                request_timeout=timeout
            )
            
            logger.info(f"Generating quiz with model={model_name}, topic={topic}, num_questions={num_questions}")
            
            # Call LLM
            if hasattr(llm, "complete"):
                response = llm.complete(prompt)
                response_text = str(response)
            elif hasattr(llm, "generate"):
                response = llm.generate(prompt)
                response_text = str(response)
            elif callable(llm):
                response_text = str(llm(prompt))
            else:
                response_text = ""
            
            # Parse response
            parsed = _parse_quiz_response(response_text)
            
            if parsed:
                for i, q in enumerate(parsed):
                    try:
                        question = QuizQuestion(
                            question_id=q.get("question_id", f"q{i+1}"),
                            question_text=q.get("question_text", ""),
                            question_type=q.get("question_type", "multiple_choice"),
                            options=q.get("options"),
                            correct_answer=q.get("correct_answer", ""),
                            explanation=q.get("explanation"),
                            difficulty=q.get("difficulty", difficulty),
                            topic=q.get("topic", topic)
                        )
                        questions.append(question)
                    except Exception as e:
                        logger.warning(f"Failed to parse question {i}: {e}")
                        continue
            
            if not questions:
                logger.warning("No questions parsed from LLM response, using fallback")
                questions = _generate_fallback_questions(topic, num_questions, question_types, difficulty)
                
        except Exception as e:
            logger.exception(f"Quiz generation failed: {e}")
            questions = _generate_fallback_questions(topic, num_questions, question_types, difficulty)
    
    # Create quiz result
    quiz = QuizResult(
        quiz_id=quiz_id,
        user_id=user_id,
        quiz_title=topic,
        questions=questions,
        total_questions=len(questions),
        date_taken=now,
        learning_plan_reference=plan_reference,
        status="in_progress"
    )
    
    # Save to disk
    save_quiz(user_id, quiz)
    
    return quiz


def _generate_fallback_questions(
    topic: str,
    num_questions: int,
    question_types: List[str],
    difficulty: str
) -> List[QuizQuestion]:
    """Generate fallback questions when LLM is unavailable."""
    questions = []
    
    # Simple fallback questions based on topic
    templates = [
        {
            "type": "multiple_choice",
            "text": f"What is the primary concept behind {topic}?",
            "options": [
                f"A. Understanding {topic} fundamentals",
                "B. Avoiding all related concepts",
                "C. Ignoring best practices",
                "D. None of the above"
            ],
            "answer": f"A. Understanding {topic} fundamentals",
            "explanation": f"The primary concept is to understand {topic} fundamentals."
        },
        {
            "type": "true_false",
            "text": f"Learning {topic} requires practice and understanding.",
            "options": ["True", "False"],
            "answer": "True",
            "explanation": "Practice and understanding are essential for learning any topic."
        },
        {
            "type": "short_answer",
            "text": f"Name one key aspect of {topic}.",
            "options": None,
            "answer": "Practice",
            "explanation": f"Practice is a key aspect of mastering {topic}."
        },
        {
            "type": "multiple_choice",
            "text": f"Which approach is best for learning {topic}?",
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
            "text": f"{topic} is a topic that can be learned in isolation without any context.",
            "options": ["True", "False"],
            "answer": "False",
            "explanation": "Context and connections to other concepts are important for learning."
        }
    ]
    
    for i in range(min(num_questions, len(templates))):
        t = templates[i]
        q_type = t["type"]
        if q_type not in question_types:
            # Find a matching type
            q_type = question_types[i % len(question_types)]
        
        questions.append(QuizQuestion(
            question_id=f"q{i+1}",
            question_text=t["text"],
            question_type=q_type,
            options=t["options"],
            correct_answer=t["answer"],
            explanation=t["explanation"],
            difficulty=difficulty,
            topic=topic
        ))
    
    return questions


# ============================================================================
# Quiz Submission and Scoring
# ============================================================================

def submit_quiz_answer(
    user_id: str,
    quiz_id: str,
    question_id: str,
    user_answer: str,
    time_taken_seconds: Optional[float] = None
) -> Dict[str, Any]:
    """
    Submit an answer for a quiz question.
    
    Returns dict with is_correct, correct_answer, explanation, and updated score.
    """
    quiz = load_quiz(user_id, quiz_id)
    if not quiz:
        raise ValueError(f"Quiz {quiz_id} not found")
    
    # Find the question
    question = None
    for q in quiz.questions:
        if q.question_id == question_id:
            question = q
            break
    
    if not question:
        raise ValueError(f"Question {question_id} not found in quiz")
    
    # Check if already answered
    for resp in quiz.user_responses:
        if resp.question_id == question_id:
            raise ValueError(f"Question {question_id} already answered")
    
    # Evaluate answer
    is_correct = _check_answer(question, user_answer)
    
    # Record response
    response = UserResponse(
        question_id=question_id,
        user_answer=user_answer,
        is_correct=is_correct,
        time_taken_seconds=time_taken_seconds
    )
    quiz.user_responses.append(response)
    
    # Update score
    quiz.correct_answers = sum(1 for r in quiz.user_responses if r.is_correct)
    quiz.score = (quiz.correct_answers / quiz.total_questions) * 100 if quiz.total_questions > 0 else 0
    
    # Check if quiz is complete
    if len(quiz.user_responses) >= quiz.total_questions:
        quiz.status = "completed"
        quiz.date_completed = datetime.now(timezone.utc)
    
    # Save updated quiz
    save_quiz(user_id, quiz)
    
    return {
        "is_correct": is_correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "current_score": quiz.score,
        "questions_answered": len(quiz.user_responses),
        "total_questions": quiz.total_questions,
        "status": quiz.status
    }


def _check_answer(question: QuizQuestion, user_answer: str) -> bool:
    """Check if user answer is correct."""
    correct = question.correct_answer.strip().lower()
    answer = user_answer.strip().lower()
    
    if question.question_type == "multiple_choice":
        # Match by letter or full option text
        correct_letter = correct[0] if correct else ""
        answer_letter = answer[0] if answer else ""
        
        if answer_letter == correct_letter:
            return True
        if answer == correct:
            return True
        # Also check if answer matches the text after letter prefix
        if "." in correct:
            correct_text = correct.split(".", 1)[1].strip()
            if answer == correct_text:
                return True
    
    elif question.question_type == "true_false":
        return answer in ("true", "false") and answer == correct
    
    elif question.question_type == "short_answer":
        # More lenient matching for short answers
        if answer == correct:
            return True
        # Check if answer contains the key words
        if correct in answer or answer in correct:
            return True
    
    return answer == correct


def complete_quiz(user_id: str, quiz_id: str) -> QuizResult:
    """Mark quiz as completed and return final result."""
    quiz = load_quiz(user_id, quiz_id)
    if not quiz:
        raise ValueError(f"Quiz {quiz_id} not found")
    
    quiz.status = "completed"
    quiz.date_completed = datetime.now(timezone.utc)
    
    save_quiz(user_id, quiz)
    return quiz
