import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import codeQuestService from '../services/codeQuestService';
import ConfirmModal from '../components/ConfirmModal';
import '../styles/Quiz.css';
import '../styles/CodeQuestSession.css';

function capitalizeWord(value) {
  const v = String(value || '').trim();
  if (!v) return '';
  return v.charAt(0).toUpperCase() + v.slice(1);
}

function editorLanguage(lang) {
  const l = String(lang || '').toLowerCase();
  if (l.includes('python')) return 'python';
  if (l.includes('javascript') || l === 'js') return 'javascript';
  if (l.includes('typescript') || l === 'ts') return 'typescript';
  if (l.includes('java')) return 'java';
  if (l.includes('c++') || l === 'cpp') return 'cpp';
  if (l === 'c') return 'c';
  return 'plaintext';
}

function statusLabel(result) {
  if (!result) return 'Not started';
  const s = String(result.status || '').toLowerCase();
  if (s === 'passed') return 'Passed';
  if (s === 'failed') return 'Fail';
  if (s) return capitalizeWord(s);
  if (result.passed === true) return 'Passed';
  if (result.passed === false) return 'Fail';
  return 'Submitted';
}

function challengeCardTone(label) {
  const norm = String(label || '').toLowerCase();
  if (norm.includes('passed')) return 'passed';
  if (norm.includes('fail')) return 'failed';
  if (norm.includes('tried') || norm.includes('started') || norm.includes('submitted')) return 'started';
  return 'not-started';
}

function CollapsiblePanel({ title, collapsed, onToggle, children }) {
  return (
    <div className={`codequest-panel ${collapsed ? 'collapsed' : ''}`}>
      <div className="codequest-panel-title-row">
        <div className="codequest-panel-title">{title}</div>
        <button
          type="button"
          className="codequest-collapse-arrow"
          onClick={onToggle}
          aria-label={collapsed ? `Expand ${title}` : `Collapse ${title}`}
        >
          <span className="codequest-collapse-icon" aria-hidden>{collapsed ? '▸' : '▾'}</span>
        </button>
      </div>
      {collapsed ? null : children}
    </div>
  );
}

function attemptSummary(result) {
  if (!result) return null;
  if (result.passed === true) return 'Successful submission.';
  if (result.passed === false) return result.reason ? `Failed: ${result.reason}` : 'Failed.';
  return 'Submitted.';
}

function planNameFromReference(ref) {
  const raw = String(ref || '').trim();
  if (!raw) return '';
  const parts = raw.split(/[/\\]/g);
  const base = parts[parts.length - 1] || '';
  return base.replace(/\.json$/i, '').trim();
}

export default function CodeQuestSessionPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [challengeList, setChallengeList] = useState([]);
  const [activeIndex, setActiveIndex] = useState(0);

  const [codeDrafts, setCodeDrafts] = useState({});
  const [code, setCode] = useState('');

  const [submitResult, setSubmitResult] = useState(null);

  // Confirm Modal State
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: null,
    variant: "warning",
    confirmText: "Confirm",
    cancelText: "Cancel"
  });
  const [finalStats, setFinalStats] = useState(null);

  const [solutions, setSolutions] = useState({});
  const [viewMode, setViewMode] = useState(false);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [error, setError] = useState('');

  const [collapsed, setCollapsed] = useState({
    description: false,
    editor: false,
    result: true,
  });

  const draftSaveTimerRef = useRef(null);

  // Helper to show confirmation modal
  const showConfirmModal = (title, message, onConfirm, variant = "warning", confirmText = "Confirm", cancelText = "Cancel") => {
    setConfirmModal({
      isOpen: true,
      title,
      message,
      onConfirm,
      variant,
      confirmText,
      cancelText
    });
  };

  // Helper to close confirmation modal
  const closeConfirmModal = () => {
    setConfirmModal({
      isOpen: false,
      title: "",
      message: "",
      onConfirm: null,
      variant: "warning",
      confirmText: "Confirm",
      cancelText: "Cancel"
    });
  };

  const ids = session?.challenge_ids || [];
  const results = useMemo(() => (session?.results || {}), [session?.results]);
  const currentId = ids[activeIndex];
  const currentChallenge = useMemo(
    () => (challengeList || []).find((c) => c.id === currentId) || null,
    [challengeList, currentId]
  );

  const lang = useMemo(
    () => editorLanguage(currentChallenge?.language || session?.language),
    [currentChallenge?.language, session?.language]
  );

  const busy = submitting || finishing;
  const isSubmitted = Boolean(currentId && results?.[currentId] && (results[currentId].attempts || 0) > 0);
  const canSubmit = Boolean(currentId) && !busy && !viewMode && !isSubmitted;

  const currentResult = useMemo(() => {
    if (!currentId) return null;

    if (submitResult && submitResult.challenge_id === currentId) {
      return {
        challenge_id: currentId,
        passed: Boolean(submitResult.passed),
        reason: submitResult.reason || null,
        feedback: submitResult.feedback || null,
        solution: submitResult.solution || solutions?.[currentId] || '',
      };
    }

    const r = results?.[currentId] || null;
    if (!r) return null;
    const passed = r.passed === true || String(r.status || '').toLowerCase() === 'passed';
    return {
      challenge_id: currentId,
      passed,
      reason: r.reason || null,
      feedback: r.feedback || null,
      solution: solutions?.[currentId] || '',
    };
  }, [currentId, results, submitResult, solutions]);

  const refresh = async ({ keepIndex } = {}) => {
    const data = await codeQuestService.getSession(sessionId);
    setSession(data.session);
    setCodeDrafts(data.session?.drafts || {});
    setSolutions(data.solutions || {});
    setViewMode(Boolean(data.view_mode));
    setChallengeList(Array.isArray(data.challenges) ? data.challenges : []);

    const idx = keepIndex != null ? keepIndex : Number(data.session?.current_index || 0);
    setActiveIndex(idx);
  };

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setError('');
      try {
        await refresh({ keepIndex: null });
        if (!mounted) return;
      } catch (e) {
        if (!mounted) return;
        setError(e?.message || 'Failed to load CodeQuest');
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    return () => {
      if (draftSaveTimerRef.current) clearTimeout(draftSaveTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!ids.length) return;
    const id = ids[activeIndex];
    const meta = (challengeList || []).find((c) => c.id === id) || null;
    const draft = codeDrafts?.[id];
    setCode(typeof draft === 'string' ? draft : (meta?.starter_code || ''));
    setSubmitResult(null);
    setFinalStats(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIndex, ids.length, challengeList, codeDrafts]);

  const selectIndex = async (idx) => {
    if (!ids.length) return;
    const clamped = Math.max(0, Math.min(ids.length - 1, idx));
    setActiveIndex(clamped);
    try {
      await codeQuestService.navigateSession(sessionId, { index: clamped });
    } catch (e) {
      // non-fatal
    }
  };

  const persistDraft = (newCode) => {
    if (!currentId || viewMode) return;
    setCodeDrafts((prev) => ({ ...prev, [currentId]: newCode }));

    if (draftSaveTimerRef.current) clearTimeout(draftSaveTimerRef.current);
    draftSaveTimerRef.current = setTimeout(async () => {
      try {
        await codeQuestService.saveDraft(sessionId, { challengeId: currentId, code: newCode });
      } catch (e) {
        // non-fatal
      }
    }, 500);
  };

  const onSubmit = async () => {
    if (!currentId) return;
    setSubmitting(true);
    setError('');
    try {
      const out = await codeQuestService.submitSolution(sessionId, { challengeId: currentId, code });
      setSubmitResult(out);
      setFinalStats(null);
      setCollapsed((p) => ({ ...p, result: false }));
      await refresh({ keepIndex: Number(out?.current_index ?? activeIndex) });
    } catch (e) {
      setError(e?.message || 'Failed to submit code');
    } finally {
      setSubmitting(false);
    }
  };

  const onFinish = async () => {
    setFinishing(true);
    setError('');
    try {
      const out = await codeQuestService.finishSession(sessionId);
      navigate(`/codequest/${sessionId}/feedback`, {
        state: {
          stats: out?.stats || null,
          session: out?.session || null,
          challenges: out?.challenges || null,
        },
      });
    } catch (e) {
      setError(e?.message || 'Failed to finish quest');
    } finally {
      setFinishing(false);
    }
  };

  const onExit = async () => {
    showConfirmModal(
      "Exit CodeQuest Session",
      "Are you sure you want to exit this CodeQuest session? Your progress will be saved.",
      async () => {
        try {
          await codeQuestService.exitSession(sessionId);
        } catch (e) {
          // non-fatal
        }
        navigate('/codequest');
      },
      "warning",
      "Exit",
      "Stay"
    );
  };

  if (loading) {
    return (
      <div className="quiz-page">
        <div className="muted" style={{ padding: 16 }}>Loading…</div>
      </div>
    );
  }

  if (error && !session) {
    return (
      <div className="quiz-page">
        <div className="quiz-error inline" style={{ margin: 16 }}>{error}</div>
      </div>
    );
  }

  const title = session?.title || session?.track || 'CodeQuest';
  const difficulty = capitalizeWord(session?.difficulty || 'medium');
  const language = session?.language || 'Unknown';
  const planName = planNameFromReference(session?.plan_reference);

  return (
    <div className="quiz-page codequest-session">
      {error ? <div className="quiz-error inline" style={{ margin: '0.5rem 0' }}>{error}</div> : null}

      <div className="codequest-body">
        <div className="codequest-left">
          <div className="codequest-panel" style={{ flex: 1, minHeight: 0 }}>
            <div className="codequest-left-header" title={`${title} • ${language} • ${difficulty}${planName ? ` • ${planName}` : ''}`}>
              <div className="codequest-left-header-line">
                <span className="codequest-left-header-title">{title}</span>
                <span className="codequest-left-header-sep">•</span>
                <span className="codequest-left-header-meta">{language}</span>
                <span className="codequest-left-header-sep">•</span>
                <span className="codequest-left-header-meta">{difficulty}</span>
                {planName ? (
                  <>
                    <span className="codequest-left-header-sep">•</span>
                    <span className="codequest-left-header-meta">{planName}</span>
                  </>
                ) : null}
              </div>
            </div>

            <div className="codequest-grid">
              {ids.map((id, i) => {
                const meta = (challengeList || []).find((c) => c.id === id);
                const r = results?.[id];
                const label = statusLabel(r);
                const tone = challengeCardTone(label);
                const isActive = i === activeIndex;
                return (
                  <button
                    key={id}
                    type="button"
                    className={`codequest-card ${isActive ? 'active' : ''} tone-${tone}`}
                    onClick={() => selectIndex(i)}
                    disabled={busy}
                  >
                    <div className="codequest-card-row">
                      <div className="codequest-card-num">#{i + 1}</div>
                      <div className="codequest-card-status">{label}</div>
                    </div>
                    <div className="codequest-card-title">{meta?.title || id}</div>
                  </button>
                );
              })}
            </div>

            <div className="codequest-left-actions">
              <div className="codequest-nav">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => selectIndex(activeIndex - 1)}
                  disabled={busy || activeIndex <= 0}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => selectIndex(activeIndex + 1)}
                  disabled={busy || activeIndex >= ids.length - 1}
                >
                  Next
                </button>
              </div>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={onSubmit}
                disabled={!canSubmit}
                title={viewMode ? 'View mode' : (isSubmitted ? 'Already submitted' : '')}
              >
                {submitting ? 'Submitting…' : (isSubmitted ? 'Submitted' : 'Submit Code')}
              </button>
              {isSubmitted ? <div className="muted small-text">This challenge is already submitted.</div> : null}

              <button type="button" className="btn btn-secondary" onClick={onFinish} disabled={busy || viewMode}>
                {finishing ? 'Finishing…' : 'Finish Quest'}
              </button>

              <button type="button" className="btn btn-secondary" onClick={onExit} disabled={busy}>Exit</button>
            </div>
          </div>
        </div>

        <div className="codequest-right">
          <CollapsiblePanel
            title="Challenge Description"
            collapsed={collapsed.description}
            onToggle={() => setCollapsed((p) => ({ ...p, description: !p.description }))}
          >
            <div className="codequest-description">
              <div className="codequest-desc-title">{currentChallenge?.title || 'Challenge'}</div>
              <div className="codequest-desc-text">{currentChallenge?.prompt || 'No description available.'}</div>
              {/* <div className="muted small-text" style={{ marginTop: 8 }}>Status: {currentStatus}</div> */}
            </div>
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Code Editor"
            collapsed={collapsed.editor}
            onToggle={() => setCollapsed((p) => ({ ...p, editor: !p.editor }))}
          >
            <div className="codequest-editor">
              <Editor
                height="320px"
                language={lang}
                value={code}
                onChange={(v) => {
                  if (busy || isSubmitted || viewMode) return;
                  const next = v ?? '';
                  setCode(next);
                  persistDraft(next);
                }}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  tabSize: 2,
                  automaticLayout: true,
                  suggestOnTriggerCharacters: true,
                  quickSuggestions: true,
                  readOnly: busy || isSubmitted || viewMode,
                }}
              />
            </div>

            {currentResult ? (
              <div className="muted" style={{ padding: '0 0.75rem 0.75rem' }}>
                <strong>{currentResult.passed ? 'Successful' : 'Failed'}</strong>
                <span style={{ marginLeft: 8 }}>{attemptSummary(currentResult)}</span>
              </div>
            ) : null}
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Result"
            collapsed={collapsed.result}
            onToggle={() => setCollapsed((p) => ({ ...p, result: !p.result }))}
          >
            <div className="codequest-description">
              {finalStats ? (
                <>
                  <div className="codequest-desc-title">Final Statistics</div>
                  <div className="muted" style={{ marginTop: 6 }}>
                    Submitted: {finalStats.submitted}/{finalStats.total_challenges} • Passed: {finalStats.passed} • Failed: {finalStats.failed}
                  </div>
                </>
              ) : null}

              {currentResult ? (
                <>
                  <div className="codequest-desc-title" style={{ marginTop: finalStats ? 12 : 0 }}>
                    {currentResult.passed ? 'Passed' : 'Failed'}
                  </div>

                  {!currentResult.passed ? (
                    <div className="muted" style={{ whiteSpace: 'pre-wrap', marginTop: 6 }}>
                      {currentResult.reason ? `Reason: ${currentResult.reason}` : 'Reason: (not provided)'}
                    </div>
                  ) : null}

                  {!currentResult.passed && String(currentResult.solution || '').trim() ? (
                    <div style={{ marginTop: 10 }}>
                      <div className="muted" style={{ fontWeight: 700, marginBottom: 6 }}>Correct solution</div>
                      <pre className="codequest-pre" style={{ maxHeight: 260 }}>{currentResult.solution}</pre>
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="muted">No results yet for this challenge.</div>
              )}

              {viewMode ? (
                <div className="muted small-text" style={{ marginTop: 10 }}>
                  View mode: submissions are disabled for this session.
                </div>
              ) : null}
            </div>
          </CollapsiblePanel>
        </div>
      </div>

      {/* Custom Confirmation Modal */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        onClose={closeConfirmModal}
        onConfirm={confirmModal.onConfirm}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
        variant={confirmModal.variant}
      />
    </div>
  );
}
