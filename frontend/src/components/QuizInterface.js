/**
 * QuizInterface Component
 * 
 * Handles the actual quiz-taking experience:
 * - Display questions one at a time
 * - Handle answer selection and submission
 * - Show feedback after each answer
 * - Track progress and navigate between questions
 * - Display final results
 */

import React, { useState, useEffect } from 'react';
import quizService from '../services/quizService';
import '../styles/Quiz.css';

function QuizInterface({ quiz, onComplete, onExit }) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [answeredQuestions, setAnsweredQuestions] = useState(new Set());
  const [quizState, setQuizState] = useState(quiz);
  const [showResults, setShowResults] = useState(false);
  const [questionStartTime, setQuestionStartTime] = useState(Date.now());

  const questions = quizState?.questions || [];
  const currentQuestion = questions[currentQuestionIndex];
  const isLastQuestion = currentQuestionIndex === questions.length - 1;
  const isQuizComplete = answeredQuestions.size >= questions.length;

  // Reset question timer when question changes
  useEffect(() => {
    setQuestionStartTime(Date.now());
    setSelectedAnswer('');
    setFeedback(null);
  }, [currentQuestionIndex]);

  // Check if current question was already answered
  useEffect(() => {
    if (quizState?.user_responses) {
      const alreadyAnswered = quizState.user_responses.find(
        r => r.question_id === currentQuestion?.question_id
      );
      if (alreadyAnswered) {
        setAnsweredQuestions(prev => new Set([...prev, currentQuestion.question_id]));
        setSelectedAnswer(alreadyAnswered.user_answer);
        setFeedback({
          isCorrect: alreadyAnswered.is_correct,
          correctAnswer: currentQuestion.correct_answer,
          explanation: currentQuestion.explanation
        });
      }
    }
  }, [currentQuestionIndex, quizState, currentQuestion]);

  const handleAnswerSelect = (answer) => {
    if (answeredQuestions.has(currentQuestion?.question_id)) return;
    setSelectedAnswer(answer);
  };

  const handleSubmitAnswer = async () => {
    if (!selectedAnswer || isSubmitting) return;
    if (answeredQuestions.has(currentQuestion?.question_id)) return;

    setIsSubmitting(true);
    const timeTaken = (Date.now() - questionStartTime) / 1000;

    try {
      const result = await quizService.submitAnswer(
        quizState.quiz_id,
        currentQuestion.question_id,
        selectedAnswer,
        timeTaken
      );

      setFeedback({
        isCorrect: result.is_correct,
        correctAnswer: result.correct_answer,
        explanation: result.explanation
      });

      setAnsweredQuestions(prev => new Set([...prev, currentQuestion.question_id]));

      // Update local quiz state with new score
      setQuizState(prev => ({
        ...prev,
        score: result.current_score,
        correct_answers: result.questions_answered,
        status: result.status
      }));

    } catch (error) {
      console.error('Failed to submit answer:', error);
      setFeedback({
        isCorrect: false,
        error: error.message || 'Failed to submit answer'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  };

  const handleFinishQuiz = async () => {
    try {
      const result = await quizService.completeQuiz(quizState.quiz_id);
      setQuizState(result);
      setShowResults(true);
      if (onComplete) {
        onComplete(result);
      }
    } catch (error) {
      console.error('Failed to complete quiz:', error);
    }
  };

  const getDifficultyClass = (difficulty) => {
    return `difficulty-${(difficulty || 'medium').toLowerCase()}`;
  };

  const getQuestionTypeLabel = (type) => {
    const labels = {
      'multiple_choice': 'Multiple Choice',
      'true_false': 'True/False',
      'short_answer': 'Short Answer'
    };
    return labels[type] || type;
  };

  // Render Results Screen
  if (showResults) {
    const score = quizState.score || 0;
    const correctCount = quizState.correct_answers || 0;
    const totalQuestions = quizState.total_questions || questions.length;
    const incorrectCount = totalQuestions - correctCount;
    const scoreClass = score >= 70 ? 'high-score' : score < 50 ? 'low-score' : '';

    return (
      <div className="quiz-results">
        <div className={`results-score-circle ${scoreClass}`}>
          <span className="score-percentage">{Math.round(score)}%</span>
          <span className="score-label">Score</span>
        </div>

        <div className="results-summary">
          <h2>Quiz Complete!</h2>
          <p className="results-detail">
            You've completed "{quizState.quiz_title}"
          </p>
        </div>

        <div className="results-breakdown">
          <div className="breakdown-item">
            <div className="breakdown-value correct">{correctCount}</div>
            <div className="breakdown-label">Correct</div>
          </div>
          <div className="breakdown-item">
            <div className="breakdown-value incorrect">{incorrectCount}</div>
            <div className="breakdown-label">Incorrect</div>
          </div>
          <div className="breakdown-item">
            <div className="breakdown-value">{totalQuestions}</div>
            <div className="breakdown-label">Total</div>
          </div>
        </div>

        <div className="results-actions">
          <button className="btn btn-secondary" onClick={onExit}>
            Back to Dashboard
          </button>
          <button className="btn btn-primary" onClick={() => {
            setShowResults(false);
            setCurrentQuestionIndex(0);
          }}>
            Review Answers
          </button>
        </div>
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <div className="quiz-loading">
        <div className="spinner"></div>
        <p>Loading question...</p>
      </div>
    );
  }

  const isAnswered = answeredQuestions.has(currentQuestion.question_id);
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100;

  return (
    <div className="quiz-interface two-column">
      <div className="quiz-left scroll-pane">
        {/* Header */}
        <div className="quiz-header">
          <h2 className="quiz-title">{quizState.quiz_title}</h2>
          <div className="quiz-progress">
            <div className="progress-bar">
              <div 
                className="progress-bar-fill" 
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="progress-text">
              {currentQuestionIndex + 1} / {questions.length}
            </span>
          </div>
        </div>

        {/* Question Card */}
        <div className="question-card">
          <div className="question-number">
            Question {currentQuestionIndex + 1}
            <span className="question-type-badge">
              {getQuestionTypeLabel(currentQuestion.question_type)}
            </span>
            <span className={`question-difficulty ${getDifficultyClass(currentQuestion.difficulty)}`}>
              {currentQuestion.difficulty || 'Medium'}
            </span>
          </div>

          <div className="question-text">{currentQuestion.question_text}</div>

          {/* Answer Options based on question type */}
          {currentQuestion.question_type === 'multiple_choice' && (
            <div className="answer-options">
              {currentQuestion.options?.map((option, idx) => {
                const isSelected = selectedAnswer === option;
                const isCorrectAnswer = feedback && option === feedback.correctAnswer;
                const isWrongAnswer = feedback && isSelected && !feedback.isCorrect;
                
                let optionClass = 'answer-option';
                if (isSelected) optionClass += ' selected';
                if (isAnswered) {
                  optionClass += ' disabled';
                  if (isCorrectAnswer) optionClass += ' correct';
                  if (isWrongAnswer) optionClass += ' incorrect';
                }

                return (
                  <label 
                    key={idx} 
                    className={optionClass}
                    onClick={() => !isAnswered && handleAnswerSelect(option)}
                  >
                    <input
                      type="radio"
                      name="answer"
                      checked={isSelected}
                      disabled={isAnswered}
                      onChange={() => {}}
                    />
                    <span className="answer-option-text">{option}</span>
                  </label>
                );
              })}
            </div>
          )}

          {currentQuestion.question_type === 'true_false' && (
            <div className="answer-options true-false-options">
              {['True', 'False'].map((option) => {
                const isSelected = selectedAnswer === option;
                const isCorrectAnswer = feedback && option === feedback.correctAnswer;
                const isWrongAnswer = feedback && isSelected && !feedback.isCorrect;
                
                let optionClass = 'answer-option';
                if (isSelected) optionClass += ' selected';
                if (isAnswered) {
                  optionClass += ' disabled';
                  if (isCorrectAnswer) optionClass += ' correct';
                  if (isWrongAnswer) optionClass += ' incorrect';
                }

                return (
                  <label 
                    key={option} 
                    className={optionClass}
                    onClick={() => !isAnswered && handleAnswerSelect(option)}
                  >
                    <input
                      type="radio"
                      name="answer"
                      checked={isSelected}
                      disabled={isAnswered}
                      onChange={() => {}}
                    />
                    <span className="answer-option-text">{option}</span>
                  </label>
                );
              })}
            </div>
          )}

          {currentQuestion.question_type === 'short_answer' && (
            <div className="short-answer-container">
              <textarea
                className="short-answer-textarea"
                value={selectedAnswer}
                onChange={(e) => !isAnswered && setSelectedAnswer(e.target.value)}
                placeholder="Type your answer here..."
                disabled={isAnswered}
                rows={4}
              />
            </div>
          )}

          {/* Feedback */}
          {feedback && (
            <div className={`answer-feedback ${feedback.isCorrect ? 'correct' : 'incorrect'}`}>
              <div className="feedback-text">
                <span className="feedback-icon">
                  {feedback.isCorrect ? '✓' : '✗'}
                </span>
                {feedback.isCorrect ? 'Correct!' : 'Incorrect'}
              </div>
              {!feedback.isCorrect && (
                <div className="correct-answer-display">
                  <strong>Correct answer:</strong> {feedback.correctAnswer}
                </div>
              )}
              {feedback.explanation && (
                <div className="feedback-explanation">
                  <strong>Explanation:</strong> {feedback.explanation}
                </div>
              )}
              {feedback.error && (
                <div className="feedback-explanation" style={{ color: '#d9534f' }}>
                  {feedback.error}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Navigation (kept near questions for keyboard users) */}
        <div className="question-navigation">
          <button 
            className="btn btn-secondary"
            onClick={handlePreviousQuestion}
            disabled={currentQuestionIndex === 0}
          >
            ← Previous
          </button>

          <div className="navigation-center">
            {!isAnswered && (
              <button
                className="btn btn-primary"
                onClick={handleSubmitAnswer}
                disabled={!selectedAnswer || isSubmitting}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Answer'}
              </button>
            )}
          </div>

          {isAnswered && !isLastQuestion && (
            <button 
              className="btn btn-primary"
              onClick={handleNextQuestion}
            >
              Next →
            </button>
          )}

          {isAnswered && isLastQuestion && (
            <button 
              className="btn btn-success"
              onClick={handleFinishQuiz}
            >
              Finish Quiz
            </button>
          )}

          {!isAnswered && !isLastQuestion && (
            <button 
              className="btn btn-secondary"
              onClick={handleNextQuestion}
            >
              Skip →
            </button>
          )}

          {!isAnswered && isLastQuestion && isQuizComplete && (
            <button 
              className="btn btn-success"
              onClick={handleFinishQuiz}
            >
              Finish Quiz
            </button>
          )}
        </div>
      </div>

      {/* Right column: quiz info and global actions (sticky) */}
      <aside className="quiz-right">
        <div className="quiz-info-panel">
          <h3>Quiz Info</h3>
          <div className="info-row"><strong>Topic:</strong> {quizState.quiz_title}</div>
          <div className="info-row"><strong>Questions:</strong> {questions.length}</div>
          <div className="info-row"><strong>Difficulty:</strong> {quizState.difficulty || 'Medium'}</div>
          <div className="info-row"><strong>Score:</strong> {quizState.score ? `${Math.round(quizState.score)}%` : '—'}</div>

          <div className="panel-actions">
            {!isAnswered && (
              <button
                className="btn btn-primary"
                onClick={handleSubmitAnswer}
                disabled={!selectedAnswer || isSubmitting}
              >
                {isSubmitting ? (<><span className="spinner small"></span> Submitting...</>) : 'Submit Answer'}
              </button>
            )}

            {isAnswered && !isLastQuestion && (
              <button className="btn btn-primary" onClick={handleNextQuestion}>Next →</button>
            )}

            {isAnswered && isLastQuestion && (
              <button className="btn btn-success" onClick={handleFinishQuiz}>Finish Quiz</button>
            )}

            <button className="btn btn-secondary" onClick={onExit}>Exit</button>
          </div>
        </div>
      </aside>
    </div>
  );
}

export default QuizInterface;
