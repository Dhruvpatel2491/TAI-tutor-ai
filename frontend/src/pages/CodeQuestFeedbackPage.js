import React, { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import codeQuestService from '../services/codeQuestService';

import '../styles/Quiz.css';
import '../styles/CodeQuestSession.css';

function capitalizeWord(value) {
  const v = String(value || '').trim();
  if (!v) return '';
  return v.charAt(0).toUpperCase() + v.slice(1);
}

function scorePercent(passed, total) {
  const t = Number(total) || 0;
  const p = Number(passed) || 0;
  if (t <= 0) return 0;
  return Math.round((p / t) * 100);
}

function normalizePassed(result) {
  if (!result) return null;
  if (result.passed === true) return true;
  if (result.passed === false) return false;
  const s = String(result.status || '').toLowerCase();
  if (s === 'passed') return true;
  if (s === 'failed') return false;
  return null;
}

function challengeTone(passed) {
  if (passed === true) return 'passed';
  if (passed === false) return 'failed';
  return 'not-started';
}

export default function CodeQuestFeedbackPage() {
  const { sessionId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const stats = location.state?.stats || null;
  const [session, setSession] = useState(location.state?.session || null);
  const [challenges, setChallenges] = useState(location.state?.challenges || null);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    (async () => {
      setError('');
      try {
        if (session && Array.isArray(challenges)) return;

        const data = await codeQuestService.getSession(sessionId);
        if (!mounted) return;
        setSession(data.session);
        setChallenges(Array.isArray(data.challenges) ? data.challenges : []);
      } catch (e) {
        if (!mounted) return;
        setError(e?.message || 'Failed to load feedback');
      }
    })();
    return () => { mounted = false; };
  }, [sessionId, session, challenges]);

  const derivedStats = useMemo(() => {
    if (stats && typeof stats === 'object') return stats;
    const ids = session?.challenge_ids || [];
    const results = session?.results || {};
    const total = ids.length;
    const submitted = ids.filter((cid) => (results?.[cid]?.attempts || 0) > 0).length;
    const passed = ids.filter((cid) => normalizePassed(results?.[cid]) === true).length;
    const failed = submitted - passed;
    return {
      session_id: session?.session_id,
      status: session?.status,
      total_challenges: total,
      submitted,
      passed,
      failed,
      completed: session?.status === 'completed',
    };
  }, [stats, session]);

  const scorePct = scorePercent(derivedStats?.passed, derivedStats?.total_challenges);

  const onBackToSession = () => navigate(`/codequest/${sessionId}`);

  if (error) {
    return (
      <div className="quiz-page" style={{ padding: 16 }}>
        <h2>CodeQuest Feedback</h2>
        <div className="card" style={{ borderLeft: '4px solid var(--color-tertiary)', marginTop: 12 }}>
          <strong>Error</strong>
          <div className="muted text-danger" style={{ marginTop: 6 }}>{error}</div>
        </div>
      </div>
    );
  }

  if (!session || !Array.isArray(challenges)) {
    return (
      <div className="quiz-page" style={{ padding: 16 }}>
        <h2>CodeQuest Feedback</h2>
        <div className="muted">Loading…</div>
      </div>
    );
  }

  const title = session?.title || session?.track || 'CodeQuest';
  const description = String(session?.description || '').trim();
  const difficulty = capitalizeWord(session?.difficulty || 'medium');

  const ids = session?.challenge_ids || [];
  const results = session?.results || {};

  return (
    <div className="quiz-page" style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ margin: 0 }}>Feedback</h2>
          <div className="muted" style={{ marginTop: 6 }}>
            Track: {session.track} · Session: {session.session_id}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary" onClick={onBackToSession}>Back to Session</button>
          <Link className="btn" to="/codequest">Back to Dashboard</Link>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div className="card" style={{ flex: 1, minWidth: 240 }}>
            <h3 style={{ marginTop: 0 }}>Score</h3>
            <div style={{ fontSize: 28, fontWeight: 800, marginTop: 6 }}>
              {scorePct}%
            </div>
            <div className="muted" style={{ marginTop: 6 }}>
              Submitted: {derivedStats.submitted}/{derivedStats.total_challenges} · Passed: {derivedStats.passed} · Failed: {derivedStats.failed}
            </div>
          </div>

          <div className="card" style={{ flex: 1, minWidth: 240 }}>
            <h3 style={{ marginTop: 0 }}>Quest Details</h3>
            <div style={{ marginTop: 8 }}><strong>Name:</strong> <span className="muted">{title}</span></div>
            <div style={{ marginTop: 6 }}><strong>Description:</strong> <span className="muted">{description || '(none)'}</span></div>
            <div style={{ marginTop: 6 }}><strong>Difficulty:</strong> <span className="muted">{difficulty}</span></div>
          </div>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Challenges</h3>
          <div className="codequest-grid" style={{ padding: 0, marginTop: 10 }}>
          {ids.map((cid, idx) => {
            const meta = (challenges || []).find((c) => c.id === cid) || null;
            const r = results?.[cid] || null;
            const passed = normalizePassed(r);
            const tone = challengeTone(passed);
            const label = passed === true ? 'Passed' : (passed === false ? 'Failed' : 'Not submitted');
            const reason = String(r?.reason || '').trim();

            return (
              <div key={cid} className={`codequest-card tone-${tone}`} style={{ cursor: 'default' }}>
                <div className="codequest-card-row">
                  <div className="codequest-card-num">#{idx + 1}</div>
                  <div className="codequest-card-status">{label}</div>
                </div>
                <div className="codequest-card-title" style={{ marginTop: 6 }}>
                  {meta?.title || cid}
                </div>
                {passed === false ? (
                  <div className="muted" style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                    {reason ? `Reason: ${reason}` : 'Reason: (not provided)'}
                  </div>
                ) : null}
              </div>
            );
          })}
          </div>
        </div>
      </div>
    </div>
  );
}
