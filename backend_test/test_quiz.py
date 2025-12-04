"""
Tests for quiz module and API endpoints.

Run with: pytest backend_test/test_quiz.py -v
"""

import pytest
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))

# Import quiz module
from backend.quiz import (
    QuizQuestion,
    QuizResult,
    QuizMetadata,
    UserResponse,
    generate_quiz,
    save_quiz,
    load_quiz,
    list_quizzes,
    delete_quiz,
    submit_quiz_answer,
    complete_quiz,
    _generate_fallback_questions,
    _check_answer,
    _safe_filename,
    _generate_quiz_id,
    _ROOT_QUIZ_DIR
)


class TestQuizModels:
    """Test Pydantic models for quiz data."""

    def test_quiz_question_model(self):
        """Test QuizQuestion model creation."""
        question = QuizQuestion(
            question_id="q1",
            question_text="What is Python?",
            question_type="multiple_choice",
            options=["A. A snake", "B. A programming language", "C. A movie", "D. A game"],
            correct_answer="B. A programming language",
            explanation="Python is a popular programming language.",
            difficulty="easy",
            topic="Python Basics"
        )
        
        assert question.question_id == "q1"
        assert question.question_type == "multiple_choice"
        assert len(question.options) == 4
        assert question.difficulty == "easy"

    def test_quiz_question_defaults(self):
        """Test QuizQuestion model with default values."""
        question = QuizQuestion(
            question_id="q1",
            question_text="Is Python easy?",
            correct_answer="True"
        )
        
        assert question.question_type == "multiple_choice"  # default
        assert question.difficulty == "medium"  # default
        assert question.options is None  # default

    def test_user_response_model(self):
        """Test UserResponse model creation."""
        response = UserResponse(
            question_id="q1",
            user_answer="B. A programming language",
            is_correct=True,
            time_taken_seconds=15.5
        )
        
        assert response.question_id == "q1"
        assert response.is_correct is True
        assert response.time_taken_seconds == 15.5

    def test_quiz_result_model(self):
        """Test QuizResult model creation."""
        question = QuizQuestion(
            question_id="q1",
            question_text="Test question",
            correct_answer="Answer"
        )
        
        result = QuizResult(
            quiz_id="quiz_123",
            user_id="test@example.com",
            quiz_title="Test Quiz",
            questions=[question],
            total_questions=1,
            date_taken=datetime.now(timezone.utc)
        )
        
        assert result.quiz_id == "quiz_123"
        assert result.status == "in_progress"  # default
        assert result.score == 0.0  # default
        assert len(result.questions) == 1


class TestQuizHelpers:
    """Test helper functions."""

    def test_safe_filename(self):
        """Test filename sanitization."""
        assert _safe_filename("Python Basics") == "Python_Basics"
        assert _safe_filename("Test/Quiz\\Name") == "Test_Quiz_Name"
        assert _safe_filename("Special@#$%Chars") == "SpecialChars"
        
        # Test truncation
        long_name = "a" * 150
        assert len(_safe_filename(long_name)) == 100

    def test_generate_quiz_id(self):
        """Test quiz ID generation."""
        quiz_id = _generate_quiz_id("user1", "Test Quiz")
        assert quiz_id.startswith("quiz_")
        assert len(quiz_id) > 20  # timestamp + hash

    def test_check_answer_multiple_choice(self):
        """Test answer checking for multiple choice."""
        question = QuizQuestion(
            question_id="q1",
            question_text="Test",
            question_type="multiple_choice",
            options=["A. Option1", "B. Option2"],
            correct_answer="A. Option1"
        )
        
        assert _check_answer(question, "A. Option1") is True
        assert _check_answer(question, "a. option1") is True  # case insensitive
        assert _check_answer(question, "A") is True  # letter only
        assert _check_answer(question, "B. Option2") is False

    def test_check_answer_true_false(self):
        """Test answer checking for true/false."""
        question = QuizQuestion(
            question_id="q1",
            question_text="Test",
            question_type="true_false",
            options=["True", "False"],
            correct_answer="True"
        )
        
        assert _check_answer(question, "True") is True
        assert _check_answer(question, "true") is True
        assert _check_answer(question, "False") is False

    def test_check_answer_short_answer(self):
        """Test answer checking for short answer."""
        question = QuizQuestion(
            question_id="q1",
            question_text="Test",
            question_type="short_answer",
            correct_answer="Python"
        )
        
        assert _check_answer(question, "Python") is True
        assert _check_answer(question, "python") is True
        assert _check_answer(question, "Java") is False


class TestFallbackQuestions:
    """Test fallback question generation."""

    def test_generate_fallback_questions(self):
        """Test fallback question generation."""
        questions = _generate_fallback_questions(
            topic="Python",
            num_questions=3,
            question_types=["multiple_choice", "true_false"],
            difficulty="easy"
        )
        
        assert len(questions) == 3
        assert all(isinstance(q, QuizQuestion) for q in questions)
        assert all(q.topic == "Python" for q in questions)

    def test_generate_fallback_questions_all_types(self):
        """Test fallback with all question types."""
        questions = _generate_fallback_questions(
            topic="Data Structures",
            num_questions=5,
            question_types=["multiple_choice", "true_false", "short_answer"],
            difficulty="medium"
        )
        
        assert len(questions) == 5
        assert all(q.difficulty == "medium" for q in questions)


class TestQuizStorage:
    """Test quiz storage functions."""

    @pytest.fixture
    def test_user_id(self):
        return "test_quiz_user@example.com"

    @pytest.fixture
    def sample_quiz(self, test_user_id):
        """Create a sample quiz for testing."""
        question = QuizQuestion(
            question_id="q1",
            question_text="What is 2 + 2?",
            question_type="multiple_choice",
            options=["A. 3", "B. 4", "C. 5", "D. 6"],
            correct_answer="B. 4",
            explanation="Basic arithmetic",
            difficulty="easy",
            topic="Math"
        )
        
        return QuizResult(
            quiz_id="test_quiz_001",
            user_id=test_user_id,
            quiz_title="Math Quiz",
            questions=[question],
            total_questions=1,
            date_taken=datetime.now(timezone.utc),
            status="in_progress"
        )

    def test_save_and_load_quiz(self, test_user_id, sample_quiz):
        """Test saving and loading a quiz."""
        # Save
        file_path = save_quiz(test_user_id, sample_quiz)
        assert file_path.exists()
        
        # Load
        loaded = load_quiz(test_user_id, sample_quiz.quiz_id)
        assert loaded is not None
        assert loaded.quiz_id == sample_quiz.quiz_id
        assert loaded.quiz_title == sample_quiz.quiz_title
        assert len(loaded.questions) == 1
        
        # Cleanup
        file_path.unlink()

    def test_list_quizzes(self, test_user_id, sample_quiz):
        """Test listing quizzes."""
        # Save a quiz
        file_path = save_quiz(test_user_id, sample_quiz)
        
        # List
        quizzes = list_quizzes(test_user_id)
        assert len(quizzes) >= 1
        
        quiz_ids = [q.quiz_id for q in quizzes]
        assert sample_quiz.quiz_id in quiz_ids
        
        # Cleanup
        file_path.unlink()

    def test_delete_quiz(self, test_user_id, sample_quiz):
        """Test deleting a quiz."""
        # Save
        file_path = save_quiz(test_user_id, sample_quiz)
        assert file_path.exists()
        
        # Delete
        deleted = delete_quiz(test_user_id, sample_quiz.quiz_id)
        assert deleted is True
        assert not file_path.exists()

    def test_load_nonexistent_quiz(self, test_user_id):
        """Test loading a quiz that doesn't exist."""
        loaded = load_quiz(test_user_id, "nonexistent_quiz_id")
        assert loaded is None


class TestQuizSubmission:
    """Test quiz answer submission and scoring."""

    @pytest.fixture
    def test_user_id(self):
        return "test_submit_user@example.com"

    @pytest.fixture
    def quiz_with_questions(self, test_user_id):
        """Create a quiz with multiple questions."""
        questions = [
            QuizQuestion(
                question_id="q1",
                question_text="What is 1 + 1?",
                question_type="multiple_choice",
                options=["A. 1", "B. 2", "C. 3", "D. 4"],
                correct_answer="B. 2",
                explanation="Basic addition",
                difficulty="easy",
                topic="Math"
            ),
            QuizQuestion(
                question_id="q2",
                question_text="Is 5 > 3?",
                question_type="true_false",
                options=["True", "False"],
                correct_answer="True",
                explanation="5 is greater than 3",
                difficulty="easy",
                topic="Math"
            )
        ]
        
        quiz = QuizResult(
            quiz_id="submit_test_quiz",
            user_id=test_user_id,
            quiz_title="Submission Test Quiz",
            questions=questions,
            total_questions=2,
            date_taken=datetime.now(timezone.utc),
            status="in_progress"
        )
        
        # Save quiz
        save_quiz(test_user_id, quiz)
        return quiz

    def test_submit_correct_answer(self, test_user_id, quiz_with_questions):
        """Test submitting a correct answer."""
        result = submit_quiz_answer(
            user_id=test_user_id,
            quiz_id=quiz_with_questions.quiz_id,
            question_id="q1",
            user_answer="B. 2",
            time_taken_seconds=10.0
        )
        
        assert result["is_correct"] is True
        assert result["correct_answer"] == "B. 2"
        assert result["questions_answered"] == 1
        
        # Cleanup
        delete_quiz(test_user_id, quiz_with_questions.quiz_id)

    def test_submit_incorrect_answer(self, test_user_id, quiz_with_questions):
        """Test submitting an incorrect answer."""
        result = submit_quiz_answer(
            user_id=test_user_id,
            quiz_id=quiz_with_questions.quiz_id,
            question_id="q1",
            user_answer="A. 1",
            time_taken_seconds=5.0
        )
        
        assert result["is_correct"] is False
        assert result["correct_answer"] == "B. 2"
        
        # Cleanup
        delete_quiz(test_user_id, quiz_with_questions.quiz_id)

    def test_complete_quiz(self, test_user_id, quiz_with_questions):
        """Test completing a quiz."""
        # Submit all answers
        submit_quiz_answer(test_user_id, quiz_with_questions.quiz_id, "q1", "B. 2")
        submit_quiz_answer(test_user_id, quiz_with_questions.quiz_id, "q2", "True")
        
        # Complete
        result = complete_quiz(test_user_id, quiz_with_questions.quiz_id)
        
        assert result.status == "completed"
        assert result.date_completed is not None
        assert result.score == 100.0  # Both correct
        
        # Cleanup
        delete_quiz(test_user_id, quiz_with_questions.quiz_id)


class TestQuizGeneration:
    """Test quiz generation (uses fallback when LLM not available)."""

    def test_generate_quiz_fallback(self):
        """Test quiz generation with fallback."""
        # This will use fallback since Ollama likely not available in tests
        quiz = generate_quiz(
            user_id="test_gen@example.com",
            topic="Python Programming",
            num_questions=3,
            question_types=["multiple_choice", "true_false"],
            difficulty="medium"
        )
        
        assert quiz is not None
        assert quiz.quiz_title == "Python Programming"
        assert len(quiz.questions) > 0
        assert quiz.status == "in_progress"
        
        # Cleanup
        delete_quiz("test_gen@example.com", quiz.quiz_id)


# ============================================================================
# API Endpoint Tests (requires running server)
# ============================================================================

class TestQuizAPI:
    """
    Integration tests for quiz API endpoints.
    
    These tests require the backend server to be running.
    Skip with: pytest backend_test/test_quiz.py -v -k "not API"
    """

    @pytest.fixture
    def base_url(self):
        return os.environ.get("BACKEND_URL", "http://localhost:5000")

    @pytest.fixture
    def auth_headers(self):
        """Get auth headers. Assumes DISABLE_AUTH=true or valid token."""
        # For testing with auth disabled
        return {"Content-Type": "application/json"}

    @pytest.mark.skip(reason="Requires running server")
    def test_generate_quiz_endpoint(self, base_url, auth_headers):
        """Test POST /quiz/generate endpoint."""
        import requests
        
        response = requests.post(
            f"{base_url}/quiz/generate",
            headers=auth_headers,
            json={
                "topic": "Test Topic",
                "num_questions": 3,
                "difficulty": "easy",
                "user_id": "api_test@example.com"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "quiz_id" in data
        assert data["quiz_title"] == "Test Topic"

    @pytest.mark.skip(reason="Requires running server")
    def test_list_quizzes_endpoint(self, base_url, auth_headers):
        """Test GET /quiz/list endpoint."""
        import requests
        
        response = requests.get(
            f"{base_url}/quiz/list?user_id=api_test@example.com",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
