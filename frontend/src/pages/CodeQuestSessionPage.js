import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import codeQuestService from '../services/codeQuestService';

function editorLanguage(lang) {
  const l = String(lang || '').toLowerCase();
  if (l.includes('python')) return 'python';
  if (l.includes('javascript') || l.includes('js')) return 'javascript';
  return 'plaintext';
}

export default function CodeQuestSessionPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [challenge, setChallenge] = useState(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const lang = useMemo(() => editorLanguage(challenge?.language || session?.language), [challenge?.language, session?.language]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setError('');
      try {
        const data = await codeQuestService.getSession(sessionId);
        if (!mounted) return;
        setSession(data.session);
        setChallenge(data.current_challenge);
        setCode(data.current_challenge?.starter_code || '');
      } catch (e) {
        if (!mounted) return;
        setError(e?.message || 'Failed to load CodeQuest');
      }
    })();
    return () => { mounted = false; };
  }, [sessionId]);

  const onSubmit = async () => {
    if (!challenge) return;
    setLoading(true);
    setError('');
    try {
      const result = await codeQuestService.submitSolution(sessionId, {
        challengeId: challenge.id,
        code,
      });
      const attemptId = result.attempt_id;
      try {
        sessionStorage.setItem(`codequest_last_result_${sessionId}`, JSON.stringify(result));
      } catch (e) {}
      navigate(`/codequest/${sessionId}/feedback?attempt=${encodeURIComponent(attemptId)}`, { state: { result } });
    } catch (e) {
      setError(e?.message || 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="container" style={{ marginTop: 18 }}>
        <h2>CodeQuest</h2>
        <div className="card" style={{ borderLeft: '4px solid var(--primary)', marginTop: 12 }}>
          <strong>Error</strong>
          <div className="muted text-danger" style={{ marginTop: 6 }}>{error}</div>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="container" style={{ marginTop: 18 }}>
        <h2>CodeQuest</h2>
        <div className="muted">Loading…</div>
      </div>
    );
  }

  const ids = session.challenge_ids || [];
  const currentIndex = Number(session.current_index || 0);
  const results = session.results || {};

  return (
    <div className="container" style={{ marginTop: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>CodeQuest: {session.track}</h2>
          <div className="muted">Language: {session.language} · Status: {session.status}</div>
        </div>
        <div className="muted">Progress: {Math.min(currentIndex, ids.length)}/{ids.length}</div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <h3>Challenges</h3>
        <div className="muted small-text" style={{ marginTop: 6 }}>
          {ids.length === 0 ? 'No challenges in this session.' : 'Current challenge is highlighted by position.'}
        </div>
        {ids.length > 0 ? (
          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            {ids.map((id, i) => {
              const r = results[id];
              const passed = r?.passed;
              const isCurrent = i === currentIndex;
              const label = passed ? 'Passed' : (r ? 'Tried' : 'Not started');
              return (
                <div
                  key={id}
                  className="card"
                  style={{
                    padding: '8px 10px',
                    minWidth: 140,
                    border: isCurrent ? '2px solid var(--primary)' : undefined,
                  }}
                >
                  <div><strong>#{i + 1}</strong> <span className="muted small-text">{label}</span></div>
                  <div className="muted small-text" style={{ wordBreak: 'break-word' }}>{id}</div>
                </div>
              );
            })}
          </div>
        ) : null}
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <h3>{challenge ? challenge.title : 'Finished'}</h3>
        <div className="muted" style={{ whiteSpace: 'pre-wrap', marginTop: 8 }}>
          {challenge ? challenge.prompt : 'You have completed this CodeQuest.'}
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <h3>Solution Submission</h3>
        <div className="muted small-text" style={{ marginTop: 6 }}>
          {challenge ? `Selected challenge: ${challenge.id}` : 'No active challenge.'}
        </div>

        <div style={{ marginTop: 10 }}>
          {challenge ? (
            <Editor
              height="320px"
              language={lang}
              value={code}
              onChange={(v) => setCode(v ?? '')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                tabSize: 2,
                automaticLayout: true,
              }}
            />
          ) : (
            <div className="muted">No editor available.</div>
          )}
        </div>

        <div style={{ marginTop: 12, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <button type="button" className="btn" onClick={onSubmit} disabled={loading || !challenge}>
            {loading ? 'Submitting…' : 'Submit Solution'}
          </button>
          {error ? <span className="muted">{error}</span> : null}
        </div>
      </div>
    </div>
  );
}
