import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import codeQuestService from '../services/codeQuestService';

export default function CodeQuestDashboardPage() {
  const navigate = useNavigate();
  const [tracks, setTracks] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedTrack, setSelectedTrack] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const trackOptions = useMemo(() => tracks || [], [tracks]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setError('');
      try {
        const [t, s] = await Promise.all([
          codeQuestService.listTracks(),
          codeQuestService.listSessions(),
        ]);
        if (!mounted) return;
        setTracks(t.tracks || []);
        setSessions(s.sessions || []);
        setStats(s.stats || null);
        if (!selectedTrack && (t.tracks || []).length > 0) {
          setSelectedTrack(t.tracks[0].track);
        }
      } catch (e) {
        if (!mounted) return;
        setError(e?.message || 'Failed to load CodeQuest dashboard');
      }
    })();
    return () => { mounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startNew = async () => {
    setLoading(true);
    setError('');
    try {
      const created = await codeQuestService.createSession(selectedTrack);
      const sessionId = created?.session?.session_id;
      if (!sessionId) throw new Error('Backend did not return a session_id');
      navigate(`/codequest/${sessionId}`);
    } catch (e) {
      setError(e?.message || 'Failed to start CodeQuest');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ marginTop: 18 }}>
      <h2>CodeQuest</h2>
      <p className="muted">Test your coding skills by track and get feedback.</p>

      {error ? (
        <div className="card" style={{ borderLeft: '4px solid var(--primary)', marginTop: 12 }}>
          <strong>Error</strong>
          <div className="muted text-danger" style={{ marginTop: 6 }}>{error}</div>
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: 12, marginTop: 14, flexWrap: 'wrap' }}>
        <div className="card" style={{ flex: 1, minWidth: 320 }}>
          <h3>Dashboard</h3>
          <div className="muted" style={{ marginTop: 6 }}>
            {stats ? (
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div><strong>Total</strong>: {stats.total_sessions}</div>
                <div><strong>Completed</strong>: {stats.completed_sessions}</div>
                <div><strong>Active</strong>: {stats.active_sessions}</div>
                <div><strong>Attempts</strong>: {stats.total_attempts}</div>
              </div>
            ) : (
              <div>Loading stats…</div>
            )}
          </div>

          <div style={{ marginTop: 14 }}>
            <h4 style={{ marginBottom: 8 }}>Old CodeQuests</h4>
            {sessions.length === 0 ? (
              <div className="muted">No past CodeQuests yet.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {sessions.map((s) => (
                  <div key={s.session_id} className="card" style={{ padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                      <div>
                        <div><strong>{s.track}</strong> <span className="muted">({s.language})</span></div>
                        <div className="muted small-text">Status: {s.status} · Attempts: {s.attempt_count} · Progress: {s.current_index}/{s.total_challenges}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <Link className="btn secondary" to={`/codequest/${s.session_id}`}>Open</Link>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ flex: 1.5, minWidth: 280 }}>
          <h3>Start New CodeQuest</h3>
          <div className="muted" style={{ marginTop: 6 }}>Choose a programming language/framework track.</div>

          <div style={{ marginTop: 12 }}>
            <label className="muted" htmlFor="trackSelect">Track</label>
            <select
              id="trackSelect"
              value={selectedTrack}
              onChange={(e) => setSelectedTrack(e.target.value)}
              style={{ width: '100%', padding: 10, marginTop: 6 }}
            >
              {trackOptions.map((t) => (
                <option key={t.track} value={t.track}>
                  {t.track} ({t.challenge_count} challenges)
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginTop: 12 }}>
            <button type="button" className="btn" onClick={startNew} disabled={loading || !selectedTrack}>
              {loading ? 'Starting…' : 'Start CodeQuest'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
