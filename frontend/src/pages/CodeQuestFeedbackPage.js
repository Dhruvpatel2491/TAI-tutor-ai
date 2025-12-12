import React, { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import codeQuestService from '../services/codeQuestService';

function pickLastAttempt(session, attemptId) {
  const attempts = session?.attempts || [];
  if (attemptId) {
    const found = attempts.find((a) => a.attempt_id === attemptId);
    if (found) return found;
  }
  return attempts.length ? attempts[attempts.length - 1] : null;
}

export default function CodeQuestFeedbackPage() {
  const { sessionId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [search] = useSearchParams();

  const [result, setResult] = useState(location.state?.result || null);
  const [session, setSession] = useState(null);
  const [challengeMeta, setChallengeMeta] = useState(null);
  const [error, setError] = useState('');

  const attemptId = search.get('attempt') || (result?.attempt_id || null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setError('');
      try {
        if (!result) {
          const raw = sessionStorage.getItem(`codequest_last_result_${sessionId}`);
          if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed && parsed.session_id === sessionId) setResult(parsed);
          }
        }
        const data = await codeQuestService.getSession(sessionId);
        if (!mounted) return;
        setSession(data.session);
        setChallengeMeta(data.current_challenge);
      } catch (e) {
        if (!mounted) return;
        setError(e?.message || 'Failed to load feedback');
      }
    })();
    return () => { mounted = false; };
  }, [sessionId]);

  const attempt = useMemo(() => pickLastAttempt(session, attemptId), [session, attemptId]);

  const onNext = () => {
    navigate(`/codequest/${sessionId}`);
  };

  if (error) {
    return (
      <div className="container" style={{ marginTop: 18 }}>
        <h2>CodeQuest Feedback</h2>
        <div className="card" style={{ borderLeft: '4px solid var(--primary)', marginTop: 12 }}>
          <strong>Error</strong>
          <div className="muted text-danger" style={{ marginTop: 6 }}>{error}</div>
        </div>
      </div>
    );
  }

  if (!session || !attempt) {
    return (
      <div className="container" style={{ marginTop: 18 }}>
        <h2>CodeQuest Feedback</h2>
        <div className="muted">Loading…</div>
      </div>
    );
  }

  const passed = Boolean(result?.passed ?? attempt.passed);
  const finished = Boolean(result?.finished) || session.status === 'completed';

  return (
    <div className="container" style={{ marginTop: 18 }}>
      <h2>Feedback</h2>
      <div className="muted">Track: {session.track} · Session: {session.session_id}</div>

      <div className="card" style={{ marginTop: 12 }}>
        <h3>Selected Challenge</h3>
        <div className="muted small-text" style={{ marginTop: 6 }}>{attempt.challenge_id}</div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <h3>Result</h3>
        <div style={{ marginTop: 8 }}>
          <strong>{passed ? 'Passed' : 'Not passed yet'}</strong>
        </div>
        <div className="muted" style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
          {passed
            ? 'Nice work — the tests passed.'
            : 'Some tests failed. Review the errors and try again.'}
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <h3>Output</h3>
        <div className="muted small-text" style={{ marginTop: 6 }}>stdout</div>
        <pre style={{ whiteSpace: 'pre-wrap', marginTop: 6 }}>{(result?.stdout ?? attempt.stdout) || '(empty)'}</pre>
        <div className="muted small-text" style={{ marginTop: 10 }}>stderr</div>
        <pre style={{ whiteSpace: 'pre-wrap', marginTop: 6 }}>{(result?.stderr ?? attempt.stderr) || '(empty)'}</pre>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <h3>Next</h3>
        {finished ? (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <div className="muted">You finished this CodeQuest.</div>
            <Link className="btn" to="/codequest">Back to Dashboard</Link>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <button type="button" className="btn" onClick={onNext}>Next Challenge</button>
            <span className="muted">Or keep iterating from the session page.</span>
          </div>
        )}
      </div>

      {challengeMeta ? (
        <div className="muted small-text" style={{ marginTop: 10 }}>
          Current challenge (after submission): {challengeMeta.id}
        </div>
      ) : null}
    </div>
  );
}
