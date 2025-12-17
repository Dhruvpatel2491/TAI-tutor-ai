/**
 * QuizPage Component
 * 
 * Main page for the Quiz Section including:
 * - Quiz Dashboard: Stats and list of past quizzes
 * - New Quiz Form: Create a quiz from learning plan topics
 * - Quiz Interface: Take a quiz
 */

import React, { useState, useEffect } from 'react';
import { DEFAULT_BACKEND_URL } from '../config';
import { apiGet } from '../services/http';
import quizService from '../services/quizService';
import QuizInterface from '../components/QuizInterface';
import '../styles/Quiz.css';
import { renderPlanMarkdown } from "../utils/planFormatter";

function returnPercent(value, max) {
  const numeric = Number(value) || 0;
  return Math.min(100, Math.max(0, Math.round((numeric / Number(max || 100)) * 100)));
}
// Small reusable stats card with progress bar for percentage-like metrics
function StatsCard({ title, value, max = 100, suffix = '', progress_bar = true }) {
  let percent = returnPercent(value, max);

  return (
    <div className="stat-card enhanced">
      <div className="stat-value">{value}{suffix}</div>
      <div className="stat-label">{title}</div>
      {progress_bar !== false && (
      <div className="stat-bar" aria-hidden>
        <div className="stat-bar-fill" style={{ width: `${percent}%` }}></div>
      </div>)}
    </div>
  );
}

function QuizPage() {
  // View states: 'dashboard', 'new', 'taking'
  const [view, setView] = useState('dashboard');
  const [quizzes, setQuizzes] = useState([]);
  const [savedPlans, setSavedPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [stats, setStats] = useState(null);

  // New quiz form state
  const [newQuizForm, setNewQuizForm] = useState({
    topic: '',
    selectedPlan: '',
    numQuestions: 5,
    difficulty: 'medium',
    questionTypes: {
      multiple_choice: true,
      true_false: true,
      short_answer: false
    }
  });
  const [isGenerating, setIsGenerating] = useState(false);

  // Load quizzes and plans on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Load quizzes
      const quizList = await quizService.listQuizzes();
      setQuizzes(quizList || []);
      setStats(quizService.calculateQuizStats(quizList || []));

      // Load saved plans for dropdown
      try {
        const plansRes = await apiGet(`${DEFAULT_BACKEND_URL}/saved_plans`);
        if (plansRes.ok) {
          const plans = await plansRes.json();
          setSavedPlans(plans || []);
        }
      } catch (e) {
        console.warn('Could not load saved plans:', e);
      }
    } catch (err) {
      console.error('Failed to load quizzes:', err);
      setError(err.message || 'Failed to load quizzes');
    } finally {
      setLoading(false);
    }
  };

  const handleNewQuiz = () => {
    setView('new');
    setNewQuizForm({
      topic: '',
      selectedPlan: '',
      numQuestions: 5,
      difficulty: 'medium',
      questionTypes: {
        multiple_choice: true,
        true_false: true,
        short_answer: false
      }
    });
  };

  const handleFormChange = (field, value) => {
    setNewQuizForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleQuestionTypeChange = (type) => {
    setNewQuizForm(prev => ({
      ...prev,
      questionTypes: {
        ...prev.questionTypes,
        [type]: !prev.questionTypes[type]
      }
    }));
  };

  const handlePlanSelect = (planPath) => {
    setNewQuizForm(prev => ({ ...prev, selectedPlan: planPath }));
    
    // Auto-fill topic from plan name if topic is empty
    if (!newQuizForm.topic && planPath) {
      const plan = savedPlans.find(p => p.path === planPath);
      if (plan) {
        setNewQuizForm(prev => ({ ...prev, topic: plan.name || '' }));
      }
    }
  };

  const handleGenerateQuiz = async () => {
    if (!newQuizForm.topic.trim()) {
      setError('Please enter a quiz topic');
      return;
    }

    const selectedTypes = Object.entries(newQuizForm.questionTypes)
      .filter(([_, enabled]) => enabled)
      .map(([type]) => type);

    if (selectedTypes.length === 0) {
      setError('Please select at least one question type');
      return;
    }

    setIsGenerating(true);
    setError('');

    try {
      // Get plan text if a plan is selected
      let planText = null;
      let planReference = null;
      if (newQuizForm.selectedPlan) {
        const plan = savedPlans.find(p => p.path === newQuizForm.selectedPlan);
        if (plan) {
          planText = plan.plan_text;
          planReference = plan.path;
        }
      }

      const quiz = await quizService.generateQuiz({
        topic: newQuizForm.topic,
        planText,
        planReference,
        numQuestions: newQuizForm.numQuestions,
        questionTypes: selectedTypes,
        difficulty: newQuizForm.difficulty
      });

      setActiveQuiz(quiz);
      setView('taking');
      
      // Refresh quiz list
      loadData();
    } catch (err) {
      console.error('Failed to generate quiz:', err);
      setError(err.message || 'Failed to generate quiz');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleStartQuiz = async (quizId) => {
    setLoading(true);
    try {
      const quiz = await quizService.getQuiz(quizId);
      setActiveQuiz(quiz);
      setView('taking');
    } catch (err) {
      console.error('Failed to load quiz:', err);
      setError(err.message || 'Failed to load quiz');
    } finally {
      setLoading(false);
    }
  };

  const handleQuizComplete = (result) => {
    console.log('Quiz completed:', result);
    loadData(); // Refresh stats
  };

  const handleExitQuiz = () => {
    setActiveQuiz(null);
    setView('dashboard');
    loadData();
  };

  const handleDeleteQuiz = async (quizId, e) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this quiz?')) return;

    try {
      await quizService.deleteQuiz(quizId);
      loadData();
    } catch (err) {
      console.error('Failed to delete quiz:', err);
      setError(err.message || 'Failed to delete quiz');
    }
  };

  // Render Quiz Taking View
  if (view === 'taking' && activeQuiz) {
    return (
      <div className={`quiz-page ${isGenerating ? 'generating' : ''}`}>
        <QuizInterface 
          quiz={activeQuiz}
          onComplete={handleQuizComplete}
          onExit={handleExitQuiz}
        />
      </div>
    );
  }

  // Render New Quiz Form
  if (view === 'new') {
    // Find selected plan for preview
    const selectedPlan = savedPlans.find(p => p.path === newQuizForm.selectedPlan);

    return (
      <div className={`quiz-page new-quiz-view ${isGenerating ? 'generating' : ''}`}>
        {/* Top Metadata Bar */}
        <div className="new-quiz-topbar">
          <button
            className="btn btn-secondary btn-back"
            onClick={() => setView('dashboard')}
          >
            ←
          </button>
          <div className="topbar-meta">
            <h2 className="topbar-title">Create New Quiz</h2>
            <span className="topbar-detail">{newQuizForm.numQuestions} Questions • {newQuizForm.difficulty}</span>
          </div>
        </div>

        {error && <div className="quiz-error inline">{error}</div>}

        {/* Two-column body */}
        <div className="new-quiz-body">
          {/* Left column — Topic + Plan selection + preview (scrollable) */}
          <div className="new-quiz-left scroll-pane">
            <div className="form-group">
              <label htmlFor="topic">Quiz Topic *</label>
              <input
                id="topic"
                type="text"
                value={newQuizForm.topic}
                onChange={(e) => handleFormChange('topic', e.target.value)}
                placeholder="e.g., Python Basics, Data Structures"
              />
              <div className="form-hint">Enter the topic you want to be quizzed on</div>
            </div>

            <div className="form-group">
              <label htmlFor="plan">Learning Plan (Optional)</label>
              <select
                id="plan"
                value={newQuizForm.selectedPlan}
                onChange={(e) => handlePlanSelect(e.target.value)}
              >
                <option value="">-- No plan selected --</option>
                {savedPlans.map((plan, idx) => (
                  <option key={plan.path || idx} value={plan.path}>
                    {plan.name || plan.path}
                  </option>
                ))}
              </select>
              <div className="form-hint">
                Select a learning plan to generate questions based on its content
              </div>
            </div>

            <div className="plan-preview">
              <h3>Plan Preview</h3>

              <div className={`plan-preview-body scroll-pane ${selectedPlan ? '' : 'empty'}`}>
                {selectedPlan ? (
                  <div
                    className="plan-markdown-preview"
                    dangerouslySetInnerHTML={{ __html: renderPlanMarkdown(selectedPlan.plan_text || '') }}
                  />
                ) : (
                  'No plan selected'
                )}
              </div>
            </div>
          </div>

          {/* Right column — Quiz settings panel (sticky) */}
          <aside className="new-quiz-right">
            <div className="settings-panel">
              <div className="form-group">
                <label htmlFor="numQuestions">Number of Questions</label>
                <select
                  id="numQuestions"
                  value={newQuizForm.numQuestions}
                  onChange={(e) => handleFormChange('numQuestions', parseInt(e.target.value))}
                >
                  <option value={3}>3 Questions</option>
                  <option value={5}>5 Questions</option>
                  <option value={10}>10 Questions</option>
                  <option value={15}>15 Questions</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="difficulty">Difficulty Level</label>
                <select
                  id="difficulty"
                  value={newQuizForm.difficulty}
                  onChange={(e) => handleFormChange('difficulty', e.target.value)}
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <div className="form-group">
                <label>Question Types</label>
                <div className="checkbox-group vertical">
                  <label>
                    <input
                      type="checkbox"
                      checked={newQuizForm.questionTypes.multiple_choice}
                      onChange={() => handleQuestionTypeChange('multiple_choice')}
                    />
                    Multiple Choice
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={newQuizForm.questionTypes.true_false}
                      onChange={() => handleQuestionTypeChange('true_false')}
                    />
                    True/False
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={newQuizForm.questionTypes.short_answer}
                      onChange={() => handleQuestionTypeChange('short_answer')}
                    />
                    Short Answer
                  </label>
                </div>
              </div>

              <div className="panel-actions">
                <button
                  className="btn btn-secondary"
                  onClick={() => setView('dashboard')}
                  disabled={isGenerating}
                >
                  Cancel
                </button>
                <button
                  className={`btn btn-generate ${isGenerating ? 'loading' : ''}`}
                  onClick={handleGenerateQuiz}
                  disabled={isGenerating || !newQuizForm.topic.trim()}
                >
                  {isGenerating ? (
                    <>
                      <span className="spinner small"></span> Generating...
                    </>
                  ) : (
                    'Generate Quiz'
                  )}
                </button>
              </div>
            </div>
          </aside>
        </div>

        {isGenerating && (
          <div className="page-overlay">
            <div className="overlay-spinner">
              <div className="spinner large"></div>
              <div>Generating quiz…</div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Render Dashboard
  const recentScores = (quizzes || [])
    .slice()
    .filter(q => q.score != null)
    .sort((a, b) => {
      const da = a.date_taken ? new Date(a.date_taken).getTime() : 0;
      const db = b.date_taken ? new Date(b.date_taken).getTime() : 0;
      return db - da;
    })
    .slice(0, 3);
  return (
    <div className="quiz-page dashboard-view">
      <h1>Quiz Section</h1>

      {error && (
        <div className="quiz-error">
          {error}
          <button className="btn btn-sm" onClick={() => setError('')}>
            Dismiss
          </button>
        </div>
      )}

      {loading ? (
        <div className="quiz-loading">
          <div className="spinner"></div>
          <p>Loading quizzes...</p>
        </div>
      ) : (
        <div className="quiz-dashboard">
          {/* Left Column — Stats Grid */}
          <div className="dashboard-left">
            <div className="stats-grid">
              <StatsCard title="Overall Score" value={stats?.averageScore?.toFixed(0) ?? 0} suffix="%" max={100} />
              <StatsCard title="Best Score" value={stats?.bestScore?.toFixed(0) ?? 0} suffix="%" max={100} />
              <StatsCard title="Questions Answered" value={stats?.totalQuestionsAnswered ?? 0} progress_bar={false} />
              <StatsCard title="Total Quizzes" value={stats?.total ?? 0} progress_bar={false} />
              <StatsCard title="Completed" value={stats?.completed ?? 0} progress_bar={false} />
            </div>
          </div>

          {/* Right Column — Actions + Quiz List */}
          <div className="dashboard-right">
            <div className="dashboard-actions">
              <button className="btn btn-primary full-width" onClick={handleNewQuiz}>
                + Create New Quiz
              </button>
            </div>

            <div className="recent-scores">
              <h3>Recent Scores</h3>
              <ul>
                {recentScores.length === 0 ? (
                  <li className="empty">No recent scores</li>
                ) : (
                  recentScores.map(q => (
                    <li key={q.quiz_id} className="rs-item">
                      <span className="rs-title">{q.quiz_title}</span>
                      <span className="rs-score">{q.score != null ? Math.round(q.score) + '%' : '—'}</span>
                    </li>
                  ))
                )}
              </ul>
            </div>

            <div className="quiz-list-section">
              <div className="list-header">
                <h2>Past Quizzes</h2>
                <button
                  className="btn-icon"
                  onClick={loadData}
                  title="Refresh"
                  aria-label="Refresh quiz list"
                >
                  ↻
                </button>
              </div>
              {quizzes.length === 0 ? (
                <div className="quiz-empty-state">
                  <p>No quizzes yet. Create your first quiz to get started!</p>
                </div>
              ) : (
                <ul className="quiz-list scroll-pane">
                  {quizzes.map((quiz) => {
                    const statusDisplay = quizService.getStatusDisplay(quiz.status);
                    return (
                      <li
                        key={quiz.quiz_id}
                        className="quiz-list-item"
                        onClick={() => handleStartQuiz(quiz.quiz_id)}
                      >
                        <div className="quiz-item-info">
                          <div className="quiz-item-title">{quiz.quiz_title}</div>
                          <div className="quiz-item-meta">
                            <span className={`status-badge ${statusDisplay.colorClass}`}>
                              {statusDisplay.text}
                            </span>
                            <span>{quiz.total_questions} Qs</span>
                            {quiz.score != null && (
                              <span>Score: {Math.round(quiz.score)}%</span>
                            )}
                            <span>{quizService.formatQuizDate(quiz.date_taken)}</span>
                          </div>
                        </div>
                        <div className="quiz-item-actions">
                          <button
                            className="btn btn-sm btn-primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStartQuiz(quiz.quiz_id);
                            }}
                          >
                            {quiz.status === 'in_progress' ? 'Continue' : 'Review'}
                          </button>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={(e) => handleDeleteQuiz(quiz.quiz_id, e)}
                          >
                            Delete
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default QuizPage;
