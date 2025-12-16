import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { DEFAULT_BACKEND_URL } from '../config';
import { apiGet } from '../services/http';
import codeQuestService from '../services/codeQuestService';
import '../styles/Quiz.css';
import '../styles/CodeQuest.css';
import { renderPlanMarkdown } from '../utils/planFormatter';

function returnPercent(value, max) {
  const numeric = Number(value) || 0;
  return Math.min(100, Math.max(0, Math.round((numeric / Number(max || 100)) * 100)));
}
// Small reusable stats card with progress bar for percentage-like metrics
function StatsCard({ title, value, max = 100, suffix = '', progress_bar = false }) {
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
const BASIC_CONCEPTS = [
  'Variables',
  'Conditionals',
  'Loops',
  'Functions',
  'Arrays/Lists',
  'Strings',
  'Recursion',
  'OOP',
];

const CHALLENGE_PRESETS = [5, 10, 15];

export default function CodeQuestDashboardPage() {
  const navigate = useNavigate();

  const [tracks, setTracks] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState(null);
  const [savedPlans, setSavedPlans] = useState([]);

  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');

  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [customConcept, setCustomConcept] = useState('');
  const [useCustomLanguage, setUseCustomLanguage] = useState(false);
  const [customLanguageText, setCustomLanguageText] = useState('');

  const [form, setForm] = useState({
    description: '',
    selectedPlan: '',
    language: '',
    difficulty: 'medium',
    selectedConcepts: [],
    challengeCountPreset: 5,
    customNumChallenges: '',
  });

  const trackOptions = useMemo(() => tracks || [], [tracks]);
  const defaultTrack = useMemo(() => (trackOptions[0]?.track || ''), [trackOptions]);
  const resolvedTrack = useMemo(() => {
    if (useCustomLanguage) {
      const typed = String(customLanguageText || '').trim();
      return typed;
    }
    const typed = String(form.language || '').trim();
    return typed || String(defaultTrack || '').trim();
  }, [form.language, defaultTrack, useCustomLanguage, customLanguageText]);
  const selectedPlan = useMemo(
    () => savedPlans.find((p) => p.path === form.selectedPlan),
    [savedPlans, form.selectedPlan]
  );

  useEffect(() => {
    if (!isPlanModalOpen) return;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsPlanModalOpen(false);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isPlanModalOpen]);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [t, s] = await Promise.all([
        codeQuestService.listTracks(),
        codeQuestService.listSessions(),
      ]);
      setTracks(t.tracks || []);
      setSessions(s.sessions || []);
      setStats(s.stats || null);

      // Plans (optional)
      try {
        const plansRes = await apiGet(`${DEFAULT_BACKEND_URL}/saved_plans`);
        if (plansRes.ok) {
          const plans = await plansRes.json();
          setSavedPlans(plans || []);
        }
      } catch (e) {
        // non-fatal
      }
    } catch (e) {
      console.error('Failed to load CodeQuest dashboard', e);
      setError(e?.message || 'Failed to load CodeQuest dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addConcept = (concept) => {
    const cleaned = String(concept || '').trim();
    if (!cleaned) return;
    setForm((prev) => {
      const next = Array.from(new Set([...(prev.selectedConcepts || []), cleaned]));
      return { ...prev, selectedConcepts: next };
    });
  };

  const removeConcept = (concept) => {
    setForm((prev) => ({
      ...prev,
      selectedConcepts: (prev.selectedConcepts || []).filter((c) => c !== concept),
    }));
  };

  const buildConceptList = () => Array.from(new Set(form.selectedConcepts || []));

  const resolveNumChallenges = () => {
    const preset = form.challengeCountPreset;
    if (preset === 'custom') {
      const n = Number(form.customNumChallenges);
      return Number.isFinite(n) && n > 0 ? n : null;
    }
    const n = Number(preset);
    return Number.isFinite(n) && n > 0 ? n : null;
  };

  const startNew = async () => {
    if (!resolvedTrack) {
      setError('No CodeQuest tracks available');
      return;
    }
    if (!String(form.description || '').trim()) {
      setError('Please describe the challenge');
      return;
    }

    setStarting(true);
    setError('');
    try {
      if (useCustomLanguage && !String(customLanguageText || '').trim()) {
        throw new Error('Please type your custom programming language');
      }
      const concepts = buildConceptList();
      const numChallenges = resolveNumChallenges();
      if (!numChallenges) {
        throw new Error('Please select a valid number of challenges');
      }
      if (String(resolvedTrack).trim().toLowerCase() === 'custom') {
        throw new Error('Please type your custom programming language (not "Custom")');
      }
      const created = await codeQuestService.createSession(resolvedTrack, {
        description: form.description,
        difficulty: form.difficulty,
        concepts,
        numChallenges,
        planReference: selectedPlan?.path || null,
        planText: selectedPlan?.plan_text || null,
        useLlmGenerator: true,
      });
      const sessionId = created?.session?.session_id;
      if (!sessionId) throw new Error('Backend did not return a session_id');
      navigate(`/codequest/${sessionId}`);
    } catch (e) {
      setError(e?.message || 'Failed to start CodeQuest');
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="quiz-page dashboard-view">
        <div className="muted" style={{ padding: 16 }}>Loading…</div>
      </div>
    );
  }

  const q = stats?.question_stats || {};
  const totalQuestions = Number(q.total_questions ?? 0);
  const correctAnswers = Number(q.correct_answers ?? 0);
  const incorrectAnswers = Number(q.incorrect_answers ?? 0);
  const answeredQuestions = Number(q.answered_questions ?? (correctAnswers + incorrectAnswers));

  return (
    <div className="quiz-page dashboard-view">
      <div className="quiz-dashboard">
        {/* Left */}
        <div className="dashboard-left">
          <div className="stats-grid">
            <StatsCard title="Total Questions" value={totalQuestions} max={Math.max(totalQuestions, 1)} />
            <StatsCard title="Correct" value={correctAnswers} max={Math.max(totalQuestions, 1)} />
            <StatsCard title="Incorrect" value={incorrectAnswers} max={Math.max(totalQuestions, 1)} />
            <StatsCard title="Answered" value={answeredQuestions} max={Math.max(totalQuestions, 1)} />
            <StatsCard title="Sessions" value={stats?.total_sessions ?? sessions.length} max={Math.max(stats?.total_sessions ?? sessions.length ?? 1, 1)} />
            <StatsCard title="Attempts" value={stats?.total_attempts ?? 0} max={Math.max(stats?.total_attempts ?? 1, 1)} />
          </div>

          <div className="quiz-list-section" style={{ marginTop: '1rem' }}>
            <div className="list-header">
              <h2>Old CodeQuests</h2>
              <button className="btn-icon" type="button" onClick={loadData} title="Refresh">⟳</button>
            </div>

            <div className="quiz-list scroll-pane">
              {error ? <div className="quiz-error inline" style={{ margin: '0.75rem' }}>{error}</div> : null}
              {sessions.length === 0 ? (
                <div className="muted" style={{ padding: '0.75rem 1rem' }}>No past CodeQuests yet.</div>
              ) : (
                <ul className="simple-quest-list">
                  {sessions.map((s) => (
                    <li key={s.session_id} className="simple-quest-item">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 600 }} title={s.title || s.track}>
                            {s.title || s.track} <span className="muted" style={{ fontWeight: 500 }}>({s.language})</span>
                          </div>
                          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                            {s.status} • Attempts: {s.attempt_count} • {s.current_index}/{s.total_challenges}
                          </div>
                        </div>
                        <div style={{ marginLeft: 12 }}>
                          <Link className="btn btn-secondary" to={`/codequest/${s.session_id}`}>Open</Link>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>

        {/* Right */}
        <div className="dashboard-right">
          <div className="quiz-form-container" style={{ flex: 1 }}>
            <div className="quiz-form-header">
              <h3>CodeQuest Creation Form</h3>
            </div>

            <div className="quiz-form scroll-pane">
              <div className="form-group">
                <label>Describe the challenge</label>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                  placeholder="e.g., Practice loops and functions with input/output"
                  disabled={starting}
                />
              </div>

              <div className="form-group">
                <label>Programming Language</label>
                <div className="codequest-row">
                  <select
                    value={useCustomLanguage ? '__custom__' : (form.language || defaultTrack || '')}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v === '__custom__') {
                        setUseCustomLanguage(true);
                        setForm((p) => ({ ...p, language: '' }));
                      } else {
                        setUseCustomLanguage(false);
                        setCustomLanguageText('');
                        setForm((p) => ({ ...p, language: v }));
                      }
                    }}
                    disabled={starting}
                    aria-label="Programming language"
                  >
                    {(trackOptions || []).map((t) => (
                      <option key={t.track} value={t.track}>{t.track}</option>
                    ))}
                    <option value="__custom__">Custom…</option>
                  </select>

                  {useCustomLanguage ? (
                    <input
                      type="text"
                      value={customLanguageText}
                      onChange={(e) => setCustomLanguageText(e.target.value)}
                      placeholder="Type a language"
                      disabled={starting}
                      aria-label="Custom language"
                    />
                  ) : null}
                </div>
                <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                  Selected: <strong>{resolvedTrack || '(none)'}</strong>
                </div>
              </div>

              <div className="form-group">
                <label>Reference Plan (optional)</label>
                <div className="codequest-row">
                  <select value={form.selectedPlan} onChange={(e) => setForm((p) => ({ ...p, selectedPlan: e.target.value }))} disabled={starting}>
                    <option value="">No plan</option>
                    {savedPlans.map((p) => (
                      <option key={p.path} value={p.path}>{p.name || p.path}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={!selectedPlan || starting}
                    onClick={() => setIsPlanModalOpen(true)}
                  >
                    View Plan
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label>Concepts</label>
                <div className="codequest-row" style={{ marginTop: 6 }}>
                  <select
                    value=""
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val) addConcept(val);
                      // reset back to placeholder
                      e.target.value = '';
                    }}
                    disabled={starting}
                  >
                    <option value="">Select a concept to add…</option>
                    {BASIC_CONCEPTS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <div className="codequest-row" style={{ gap: 8 }}>
                    <input
                      type="text"
                      value={customConcept}
                      onChange={(e) => setCustomConcept(e.target.value)}
                      placeholder="Write your own"
                      disabled={starting}
                    />
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => {
                        addConcept(customConcept);
                        setCustomConcept('');
                      }}
                      disabled={starting}
                    >
                      Add
                    </button>
                  </div>
                </div>

                {(form.selectedConcepts || []).length ? (
                  <div className="codequest-tags" aria-label="Selected concepts" style={{ marginTop: 10 }}>
                    {(form.selectedConcepts || []).map((c) => (
                      <span key={c} className="codequest-tag">
                        <span className="codequest-tag-text">{c}</span>
                        <button type="button" className="codequest-tag-remove" onClick={() => removeConcept(c)} aria-label={`Remove ${c}`}>
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
                    No concepts selected.
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>Difficulty & Number of Questions</label>
                <div className="codequest-row">
                  <select
                    value={form.difficulty}
                    onChange={(e) => setForm((p) => ({ ...p, difficulty: e.target.value }))}
                    disabled={starting}
                    aria-label="Difficulty"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>

                  <select
                    value={form.challengeCountPreset}
                    onChange={(e) => {
                      const v = e.target.value;
                      setForm((p) => ({
                        ...p,
                        challengeCountPreset: v === 'custom' ? 'custom' : Number(v),
                        customNumChallenges: v === 'custom' ? p.customNumChallenges : '',
                      }));
                    }}
                    disabled={starting}
                    aria-label="Number of questions"
                  >
                    {CHALLENGE_PRESETS.map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                    <option value="custom">Custom…</option>
                  </select>

                  {form.challengeCountPreset === 'custom' ? (
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={form.customNumChallenges}
                      onChange={(e) => setForm((p) => ({ ...p, customNumChallenges: e.target.value }))}
                      placeholder="Enter number"
                      disabled={starting}
                    />
                  ) : null}
                </div>
              </div>

              <div className="dashboard-actions">
                <button className="btn full-width" type="button" onClick={startNew} disabled={starting || !resolvedTrack}>
                  {starting ? (<><span className="spinner small"></span> Creating…</>) : 'Create CodeQuest Challenges'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {isPlanModalOpen ? (
        <div
          className="codequest-modal-overlay"
          role="dialog"
          aria-modal="true"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setIsPlanModalOpen(false);
          }}
        >
          <div className="codequest-modal" onMouseDown={(e) => e.stopPropagation()}>
            <div className="codequest-modal-header">
              <div style={{ fontWeight: 800 }}>Plan Preview</div>
              <button type="button" className="btn btn-secondary" onClick={() => setIsPlanModalOpen(false)}>
                Close
              </button>
            </div>
            <div className="codequest-modal-body">
              <div
                className="codequest-plan-preview-inner"
                dangerouslySetInnerHTML={{ __html: renderPlanMarkdown(selectedPlan?.plan_text || '') }}
              />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
