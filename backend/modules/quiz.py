"""
Quiz module for TAI Tutor AI.

This module handles quiz generation, storage, and evaluation using Ollama's
generative capabilities.

Quiz data is stored in: user_data/quiz/{user_id}/{quiz_title}.json
"""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from config import (
    QUIZ_MODEL,
    QUIZ_TEMPERATURE,
    QUIZ_MAX_TOKENS,
    OLLAMA_LLM,
    DEFAULT_TIMEOUT,
    QUIZ_STORE_DIR,
)
from prompts.quiz_prompts import (
    build_quiz_generation_prompt,
    get_fallback_questions,
)

logger = logging.getLogger("backend.modules.quiz")

# Try to import Ollama
try:
    from llama_index.llms.ollama import Ollama
except ImportError:
    Ollama = None


# =============================================================================
# Pydantic Models
# =============================================================================

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


# =============================================================================
# Storage Helpers
# =============================================================================

_ROOT_QUIZ_DIR = Path(QUIZ_STORE_DIR)


def _ensure_quiz_dir(user_id: str) -> Path:
    """Ensure quiz directory exists for user."""
    user_dir = _ROOT_QUIZ_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _safe_filename(title: str) -> str:
    """Convert quiz title to safe filename."""
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
    
    for file_path in user_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("quiz_id") == quiz_id:
                if data.get("date_taken"):
                    data["date_taken"] = datetime.fromisoformat(
                        data["date_taken"].replace("Z", "+00:00")
                    )
                if data.get("date_completed"):
                    data["date_completed"] = datetime.fromisoformat(
                        data["date_completed"].replace("Z", "+00:00")
                    )
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


# =============================================================================
# Quiz Generation
# =============================================================================

def _parse_quiz_response(response_text: str) -> List[Dict[str, Any]]:
    """Parse LLM response into quiz questions."""
    text = response_text.strip()
    
    # Remove markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    
    # Find JSON array
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


def _generate_fallback_questions(
    topic: str,
    num_questions: int,
    question_types: List[str],
    difficulty: str
) -> List[QuizQuestion]:
    """Generate fallback questions when LLM is unavailable."""
    fallback_data = get_fallback_questions(topic, num_questions)
    
    questions = []
    for i, q in enumerate(fallback_data):
        q_type = q.get("question_type", "multiple_choice")
        if q_type not in question_types:
            q_type = question_types[i % len(question_types)]
        
        questions.append(QuizQuestion(
            question_id=q.get("question_id", f"q{i+1}"),
            question_text=q.get("question_text", ""),
            question_type=q_type,
            options=q.get("options"),
            correct_answer=q.get("correct_answer", ""),
            explanation=q.get("explanation"),
            difficulty=difficulty,
            topic=topic
        ))
    
    return questions


def generate_quiz(
    user_id: str,
    topic: str,
    plan_text: Optional[str] = None,
    plan_reference: Optional[str] = None,
    num_questions: int = 5,
    question_types: Optional[List[str]] = None,
    difficulty: str = "medium",
    model: Optional[str] = None,
    temperature: float = QUIZ_TEMPERATURE,
    max_tokens: int = QUIZ_MAX_TOKENS,
    timeout: int = DEFAULT_TIMEOUT
) -> QuizResult:
    """
    Generate a quiz using Ollama's generative mode.
    
    Args:
        user_id: User identifier
        topic: Quiz topic/title
        plan_text: Optional learning plan text for context
        plan_reference: Optional reference to learning plan ID
        num_questions: Number of questions to generate
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
    
    quiz_id = _generate_quiz_id(user_id, topic)
    now = datetime.now(timezone.utc)
    
    prompt = build_quiz_generation_prompt(
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
            model_name = model or QUIZ_MODEL or OLLAMA_LLM
            llm = Ollama(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                request_timeout=timeout
            )
            
            logger.info(f"Generating quiz with model={model_name}, topic={topic}")
            
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
                logger.warning("No questions parsed from LLM, using fallback")
                questions = _generate_fallback_questions(topic, num_questions, question_types, difficulty)
                
        except Exception as e:
            logger.exception(f"Quiz generation failed: {e}")
            questions = _generate_fallback_questions(topic, num_questions, question_types, difficulty)
    
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
    
    save_quiz(user_id, quiz)
    return quiz


# =============================================================================
# Answer Evaluation
# =============================================================================

def _check_answer(question: QuizQuestion, user_answer: str) -> bool:
    """Check if user answer is correct."""
    correct = question.correct_answer.strip().lower()
    answer = user_answer.strip().lower()
    
    if question.question_type == "multiple_choice":
        correct_letter = correct[0] if correct else ""
        answer_letter = answer[0] if answer else ""
        
        if answer_letter == correct_letter:
            return True
        if answer == correct:
            return True
        if "." in correct:
            correct_text = correct.split(".", 1)[1].strip()
            if answer == correct_text:
                return True
    
    elif question.question_type == "true_false":
        return answer in ("true", "false") and answer == correct
    
    elif question.question_type == "short_answer":
        if answer == correct:
            return True
        if correct in answer or answer in correct:
            return True
    
    return answer == correct


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
    
    # Check if complete
    if len(quiz.user_responses) >= quiz.total_questions:
        quiz.status = "completed"
        quiz.date_completed = datetime.now(timezone.utc)
    
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


def complete_quiz(user_id: str, quiz_id: str) -> QuizResult:
    """Mark quiz as completed and return final result."""
    quiz = load_quiz(user_id, quiz_id)
    if not quiz:
        raise ValueError(f"Quiz {quiz_id} not found")
    
    quiz.status = "completed"
    quiz.date_completed = datetime.now(timezone.utc)
    
    save_quiz(user_id, quiz)
    return quiz
