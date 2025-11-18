import React, { useState, useEffect, useCallback } from 'react';
import { DEFAULT_BACKEND_URL } from '../config';

const TOKEN_KEY = 'auth_token';

function PlannerPanel({ backendURL = DEFAULT_BACKEND_URL }) {
  const [token] = useState(localStorage.getItem(TOKEN_KEY) || '');
  const [plans, setPlans] = useState([]);
  const [topicsText, setTopicsText] = useState('');
  const [notes, setNotes] = useState('');
  const [msg, setMsg] = useState('');

  const fetchPlans = useCallback(async () => {
    setMsg('');
    try {
      const res = await fetch(`${backendURL}/plans`, {
        method: 'GET',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPlans(data || []);
      } else {
        setMsg('Failed to load plans');
      }
    } catch (e) {
      setMsg('Network error');
    }
  }, [backendURL, token]);

  useEffect(() => {
    if (token) fetchPlans();
  }, [token, fetchPlans]);

  const createPlan = async () => {
    setMsg('');
    const topics = topicsText.split(',').map(s => s.trim()).filter(Boolean);
    try {
      const res = await fetch(`${backendURL}/plans`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ topics, notes })
      });
      const data = await res.json();
      if (res.ok) {
        setMsg('Plan created');
        setTopicsText('');
        setNotes('');
        fetchPlans();
      } else {
        setMsg(data.error || 'Failed to create plan');
      }
    } catch (e) {
      setMsg('Network error');
    }
  };

  if (!token) {
    return <div className="planner-panel">Please login to manage plans.</div>;
  }

  return (
    <div className="planner-panel card">
      <h3>Planner</h3>
      <div className="form-row">
        <input placeholder="topics (comma separated)" value={topicsText} onChange={(e) => setTopicsText(e.target.value)} />
      </div>
      <div className="form-row">
        <textarea placeholder="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      <div className="form-row">
        <button type="button" className="btn" onClick={createPlan}>Create Plan</button>
  <button type="button" className="btn secondary ml-8" onClick={fetchPlans}>Refresh</button>
      </div>
  <div className="message text-success" aria-live="polite">{msg}</div>

  <div className="mt-12">
        <h4>Your Plans</h4>
        {plans.length === 0 && <div>No plans yet</div>}
        <ul>
          {plans.map(p => (
            <li key={p.id}>
              <strong>{p.id}</strong> — topics: {Array.isArray(p.topics) ? p.topics.join(', ') : ''}
              <div className="muted small-text">{p.notes}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default PlannerPanel;
