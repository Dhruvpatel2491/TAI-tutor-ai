/**
 * Quiz Service for TAI-tutor-ai
 * 
 * Handles all quiz-related API calls including:
 * - Quiz generation from learning plans
 * - Quiz listing and retrieval
 * - Answer submission and scoring
 */

import { DEFAULT_BACKEND_URL } from '../config';
import { apiGet, apiPost, apiRequest } from './http';

/**
 * Generate a new quiz based on topic and optionally a learning plan
 * @param {Object} options - Quiz generation options
 * @param {string} options.topic - Quiz topic/title (required)
 * @param {string} [options.planText] - Learning plan text for context
 * @param {string} [options.planReference] - Reference to a learning plan ID
 * @param {number} [options.numQuestions=5] - Number of questions to generate
 * @param {string[]} [options.questionTypes] - Types of questions to include
 * @param {string} [options.difficulty='medium'] - Difficulty level
 * @param {string} [options.model] - Ollama model to use
 * @returns {Promise<Object>} Generated quiz with questions
 */
export async function generateQuiz({
  topic,
  planText,
  planReference,
  numQuestions = 5,
  questionTypes = ['multiple_choice', 'true_false', 'short_answer'],
  difficulty = 'medium',
  model
} = {}) {
  if (!topic) {
    throw new Error('Quiz topic is required');
  }

  const body = {
    topic,
    plan_text: planText,
    plan_reference: planReference,
    num_questions: numQuestions,
    question_types: questionTypes,
    difficulty
  };

  if (model) {
    body.model = model;
  }

  const response = await apiPost(`${DEFAULT_BACKEND_URL}/quiz/generate`, body);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to generate quiz' }));
    throw new Error(error.error || 'Failed to generate quiz');
  }

  return response.json();
}

/**
 * List all quizzes for the current user
 * @returns {Promise<Array>} List of quiz metadata
 */
export async function listQuizzes() {
  const response = await apiGet(`${DEFAULT_BACKEND_URL}/quiz/list`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to list quizzes' }));
    throw new Error(error.error || 'Failed to list quizzes');
  }

  return response.json();
}

/**
 * Get a specific quiz by ID
 * @param {string} quizId - Quiz ID
 * @returns {Promise<Object>} Full quiz with questions and responses
 */
export async function getQuiz(quizId) {
  if (!quizId) {
    throw new Error('Quiz ID is required');
  }

  const response = await apiGet(`${DEFAULT_BACKEND_URL}/quiz/${quizId}`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to get quiz' }));
    throw new Error(error.error || 'Failed to get quiz');
  }

  return response.json();
}

/**
 * Submit an answer for a quiz question
 * @param {string} quizId - Quiz ID
 * @param {string} questionId - Question ID
 * @param {string} userAnswer - User's answer
 * @param {number} [timeTakenSeconds] - Time taken to answer in seconds
 * @returns {Promise<Object>} Result with correctness, explanation, and updated score
 */
export async function submitAnswer(quizId, questionId, userAnswer, timeTakenSeconds) {
  if (!quizId || !questionId || userAnswer === undefined) {
    throw new Error('Quiz ID, question ID, and answer are required');
  }

  const body = {
    question_id: questionId,
    user_answer: userAnswer
  };

  if (timeTakenSeconds !== undefined) {
    body.time_taken_seconds = timeTakenSeconds;
  }

  const response = await apiPost(`${DEFAULT_BACKEND_URL}/quiz/${quizId}/answer`, body);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to submit answer' }));
    throw new Error(error.error || 'Failed to submit answer');
  }

  return response.json();
}

/**
 * Mark a quiz as completed
 * @param {string} quizId - Quiz ID
 * @returns {Promise<Object>} Final quiz result with score
 */
export async function completeQuiz(quizId) {
  if (!quizId) {
    throw new Error('Quiz ID is required');
  }

  const response = await apiPost(`${DEFAULT_BACKEND_URL}/quiz/${quizId}/complete`, {});
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to complete quiz' }));
    throw new Error(error.error || 'Failed to complete quiz');
  }

  return response.json();
}

/**
 * Delete a quiz by ID
 * @param {string} quizId - Quiz ID
 * @returns {Promise<Object>} Deletion confirmation
 */
export async function deleteQuiz(quizId) {
  if (!quizId) {
    throw new Error('Quiz ID is required');
  }

  const response = await apiRequest(`${DEFAULT_BACKEND_URL}/quiz/${quizId}`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to delete quiz' }));
    throw new Error(error.error || 'Failed to delete quiz');
  }

  return response.json();
}

/**
 * Calculate quiz statistics from a list of quizzes
 * @param {Array} quizzes - List of quiz metadata
 * @returns {Object} Statistics including total, completed, average score, avgTimePerQuestion, totalQuestionsAnswered
 */
export function calculateQuizStats(quizzes) {
  if (!quizzes || !quizzes.length) {
    return {
      total: 0,
      completed: 0,
      inProgress: 0,
      averageScore: 0,
      bestScore: 0,
      avgTimePerQuestion: 0,
      totalQuestionsAnswered: 0,
      topics: []
    };
  }

  const completed = quizzes.filter(q => q.status === 'completed');
  const inProgress = quizzes.filter(q => q.status === 'in_progress');
  const scores = completed.map(q => q.score || 0);
  const topics = [...new Set(quizzes.map(q => q.topic))];

  // Calculate total questions answered across all quizzes
  const totalQuestionsAnswered = quizzes.reduce((sum, q) => {
    // count from user_responses length if available, else fall back to correct_answers or 0
    return sum + (q.questions_answered ?? q.correct_answers ?? 0);
  }, 0);

  // Calculate average time per question (sum of avg times / number of quizzes that have time data)
  let totalTime = 0;
  let timeCount = 0;
  quizzes.forEach(q => {
    if (q.avg_time_per_question != null) {
      totalTime += q.avg_time_per_question;
      timeCount += 1;
    }
  });
  const avgTimePerQuestion = timeCount > 0 ? totalTime / timeCount : 0;

  return {
    total: quizzes.length,
    completed: completed.length,
    inProgress: inProgress.length,
    averageScore: scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0,
    bestScore: scores.length ? Math.max(...scores) : 0,
    avgTimePerQuestion,
    totalQuestionsAnswered,
    topics
  };
}

/**
 * Format quiz date for display
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
export function formatQuizDate(dateString) {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return dateString;
  }
}

/**
 * Get status display text and color
 * @param {string} status - Quiz status
 * @returns {Object} Display text and color class
 */
export function getStatusDisplay(status) {
  const statusMap = {
    'in_progress': { text: 'In Progress', colorClass: 'status-in-progress', color: '#f0ad4e' },
    'completed': { text: 'Completed', colorClass: 'status-completed', color: '#5cb85c' },
    'abandoned': { text: 'Abandoned', colorClass: 'status-abandoned', color: '#d9534f' }
  };
  return statusMap[status] || { text: status, colorClass: 'status-unknown', color: '#777' };
}

/**
 * Get difficulty display text and color
 * @param {string} difficulty - Question difficulty
 * @returns {Object} Display text and color class
 */
export function getDifficultyDisplay(difficulty) {
  const difficultyMap = {
    'easy': { text: 'Easy', colorClass: 'difficulty-easy', color: '#5cb85c' },
    'medium': { text: 'Medium', colorClass: 'difficulty-medium', color: '#f0ad4e' },
    'hard': { text: 'Hard', colorClass: 'difficulty-hard', color: '#d9534f' }
  };
  return difficultyMap[difficulty] || { text: difficulty, colorClass: 'difficulty-unknown', color: '#777' };
}

// Export as default object for compatibility with existing service patterns
const quizService = {
  generateQuiz,
  listQuizzes,
  getQuiz,
  submitAnswer,
  completeQuiz,
  deleteQuiz,
  calculateQuizStats,
  formatQuizDate,
  getStatusDisplay,
  getDifficultyDisplay
};

export default quizService;
