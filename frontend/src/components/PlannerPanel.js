import React, { useState, useEffect, useCallback } from 'react';
import { DEFAULT_BACKEND_URL } from '../config';

const TOKEN_KEY = 'auth_token';

function PlannerPanel({ backendURL = DEFAULT_BACKEND_URL }) {
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || '');
  const [plans, setPlans] = useState([]);
  const [savedPlansError, setSavedPlansError] = useState('');
  const [savedPlansLoading, setSavedPlansLoading] = useState(false);
  const [filterText, setFilterText] = useState('');
  const [requirements, setRequirements] = useState('');
  const [msg, setMsg] = useState('');
  const [viewMode, setViewMode] = useState('list'); // 'list' | 'create' | 'edit'
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [planText, setPlanText] = useState('');
  const [userId, setUserId] = useState(''); // dev-mode user id when no auth
  const [authDisabled, setAuthDisabled] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState('');

  useEffect(() => {
    // fetch backend auth status and then load plans if possible
    (async () => {
      try {
        const res = await fetch(`${backendURL}/auth/status`);
        if (res.ok) {
          const js = await res.json();
          if (js && js.auth_disabled) {
            setAuthDisabled(true);
            // auto-fill dev user if provided by server or default to 'dev'
            setUserId(js.default_dev_user || 'dev');
          }
        }
      } catch (e) {
        // ignore -- proceed with existing behavior
      }
      // then load plans (always trigger GET on page load)
      try {
        fetchPlans();
        refreshSavedPlans();
      } catch (e) {
        // ignore fetch errors here; fetchPlans sets error state
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleInvalidToken = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken('');
    setMsg('Session expired or invalid token. Please login again.');
  };

  const fetchPlans = useCallback(async () => {
    setMsg('');
    try {
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  // Use saved_plans endpoint (filesystem persisted plans). When auth is enabled
  // call without query params so server uses token-subject; when running in
  // dev-mode (no token) pass user_id as query param.
  const url = token ? `${backendURL}/saved_plans` : `${backendURL}/saved_plans?user_id=${encodeURIComponent(userId)}`;
  const res = await fetch(url, { method: 'GET', headers });
      if (res.ok) {
        const data = await res.json();
        setPlans(data || []);
      } else if (res.status === 401) {
        const body = await res.json().catch(() => ({}));
        if (body && (body.error && body.error.toLowerCase().includes('token'))) {
          handleInvalidToken();
        } else {
          setMsg('Unauthorized');
        }
      } else {
        const body = await res.json().catch(() => ({}));
        setMsg(body.error || 'Failed to load plans');
      }
    } catch (e) {
      setMsg('Network error');
    }
  }, [backendURL, token, userId]);

  // wrapper to expose a refresh helper that mirrors HomePage behavior
  const refreshSavedPlans = useCallback(async () => {
    setSavedPlansError('');
    setSavedPlansLoading(true);
    try {
      await fetchPlans();
    } catch (e) {
      console.error('Failed to refresh saved plans', e);
      setSavedPlansError('Failed to load saved plans');
    } finally {
      setSavedPlansLoading(false);
    }
  }, [fetchPlans]);

  // Create Plan: generate a plan from requirements (shows "Generating plan…")
  const createPlan = async () => {
    if (!requirements.trim()) {
      setMsg('Please enter plan requirements');
      return;
    }
    if (!token && !userId) {
      setMsg('Please login or provide a user id for dev mode');
      return;
    }
    setIsGenerating(true);
    setMsg('Generating plan…');
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const body = { topics: [requirements] };
      if (!token && userId) body.user_id = userId;
      const res = await fetch(`${backendURL}/plans`, { method: 'POST', headers, body: JSON.stringify(body) });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        const planText = data.notes || data.plan_text || data.answer || '';
        // load into generated plan and switch to create/edit view for review
        setGeneratedPlan(planText || '');
        setSelectedPlan({ name: data.name || '', owner: data.user_id || data.owner || userId, created_at: data.created_at || new Date().toISOString(), text: planText });
        setViewMode('create');
        setMsg('Plan generated');
        // refresh saved plans list in case server persisted a draft
        fetchPlans();
      } else if (res.status === 401) {
        if (data && (data.error && data.error.toLowerCase().includes('token'))) {
          handleInvalidToken();
        } else {
          setMsg(data.error || 'Unauthorized');
        }
      } else {
        setMsg(data.error || 'Failed to generate plan');
      }
    } catch (e) {
      setMsg('Network error');
    } finally {
      setIsGenerating(false);
    }
  };

  const savePlan = async () => {
    // allow saving either the explicitly edited planText or the last generatedPlan
    const finalText = planText || generatedPlan;
    if (!finalText) {
      setMsg('No plan text to save');
      return;
    }
  const finalName = window.prompt('Enter a name for this plan (ascii only):') || '';
  if (!finalName) return;
    setMsg('Saving plan…');
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const body = { plan_name: finalName, plan_text: finalText };
      if (!token && userId) body.user_id = userId;
      const res = await fetch(`${backendURL}/saved_plans`, { method: 'POST', headers, body: JSON.stringify(body) });
      const data = await res.json().catch(() => ({}));
      if (res.ok || res.status === 201) {
        setMsg('Plan saved');
        // refresh the user's plans list so the new plan appears
        try { fetchPlans(); } catch (e) { /* ignore */ }
        // reload to ensure caller sees fresh data (per UX requirement)
        window.location.reload();
      } else if (res.status === 401) {
        if (data && (data.error && data.error.toLowerCase().includes('token'))) {
          handleInvalidToken();
        } else {
          setMsg(data.error || 'Unauthorized');
        }
      } else {
        setMsg(data.error || 'Failed to save plan');
      }
    } catch (e) {
      setMsg('Network error');
    }
  };

  const containerStyle = { width: '100%', margin: '0 auto' };

  return (
    <div className="planner-panel card" style={containerStyle}>
      <h3>Planner</h3>

      {!token && !authDisabled && (
        <div className="form-row">
          <label className="small-text muted">No auth token detected. If your backend runs with DISABLE_AUTH=true, enter a user id to proceed:</label>
          <input placeholder="user id (dev only)" value={userId} onChange={(e) => setUserId(e.target.value)} />
        </div>
      )}

      {/* Create / Edit view: only sdatetimehown when user requests to create or edit */}
      {viewMode === 'create' && (
        <div className="form-row" style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: 5 }}>
          <input
            placeholder="Enter learning goal / plan requirements"
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
            style={{ flex: 1 }}
            aria-label="plan-requirements"
          />
          <textarea hidden
            placeholder="Optional: edit generated plan text here"
            value={planText || generatedPlan}
            onChange={(e) => setPlanText(e.target.value)}
            style={{ flex: 1, minHeight: 80 }}
          />
          <button type="button" className="btn" onClick={createPlan} disabled={isGenerating || !requirements.trim()}>
            {isGenerating ? 'Generating…' : 'Create Plan'}
          </button>
          <button type="button" className="btn secondary" onClick={() => { setViewMode('list'); setGeneratedPlan(''); setSelectedPlan(null); }}>
            Delete Current View
          </button>
          <button type="button" className="btn" onClick={savePlan} disabled={!generatedPlan}>
            Save Plan
          </button>
        </div>
      )}

      {viewMode === 'edit' && selectedPlan && (
        <div className="card" style={{ padding: 12, marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <strong>{selectedPlan.name || 'Untitled plan'}</strong>
              <div className="muted small-text">Owner: {selectedPlan.owner || 'unknown'}</div>
              <div className="muted small-text">Created: {selectedPlan.created_at || ''}</div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn" onClick={() => { setViewMode('list'); setSelectedPlan(null); }}>Close</button>
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <pre style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12 }}>{selectedPlan.text || 'No plan loaded'}</pre>
          </div>
        </div>
      )}

      

      <div className="message text-success" aria-live="polite">{msg}</div>

      

      {/* Newly generated plan section (appears below the generator and list) */}
      {generatedPlan && (
        <div className="card" style={{ padding: 12, marginTop: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4 style={{ margin: 0 }}>Generated Plan Preview</h4>
            <div>
              <button className="btn secondary" onClick={() => { setGeneratedPlan(''); }}>Clear</button>
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <pre style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12 }}>{generatedPlan}</pre>
          </div>
          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <button className="btn" onClick={() => { setPlanText(generatedPlan); setViewMode('create'); }}>Edit / Save</button>
            <button className="btn" onClick={savePlan}>Save</button>
          </div>
        </div>
      )}

      <div className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h3 style={{ margin: 0 }}>Saved Plan List</h3>
            <span className="muted small-text">{plans.length} total</span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input placeholder="Filter plans" value={filterText} onChange={(e) => setFilterText(e.target.value)} style={{ padding: '6px 8px' }} />
            <button className="btn secondary" onClick={refreshSavedPlans}>Refresh</button>
            <button className="btn" onClick={() => { setViewMode('create'); setGeneratedPlan(''); setSelectedPlan(null); setRequirements(''); }}>Generate New Plan</button>
          </div>
        </div>
        {savedPlansError && <p className="muted" style={{color: 'crimson'}}>{savedPlansError}</p>}
        {!savedPlansError && savedPlansLoading && <p className="muted">Loading saved plans…</p>}
        {!savedPlansError && !savedPlansLoading && plans.length === 0 && <p className="muted">No plans yet</p>}
        <ul>
          {plans.filter(p => (filterText ? (p.name || p.filename || p.id || '').toLowerCase().includes(filterText.toLowerCase()) : true)).map((p, idx) => (
            <li key={p.path || p.filename || p.id || idx} style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{p.name || p.id || p.filename || `plan-${idx+1}`}</strong>
                <div className="muted small-text">Owner: {p.owner || p.user_id || p.owner_id || 'unknown'} • Created: {p.created_at || p.created || ''}</div>
                <div className="muted small-text" style={{ fontSize: 11 }}>{p.path || p.notes || (Array.isArray(p.topics) ? p.topics.join(', ') : '')}</div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn" onClick={() => { navigator.clipboard && navigator.clipboard.writeText(p.path || ''); }}>Copy path</button>
                <button className="btn" onClick={() => { setSelectedPlan({ name: p.name || p.filename || '', owner: p.owner || p.user_id || p.owner_id || 'unknown', created_at: p.created_at || p.created || '', text: p.plan_text || p.text || p.notes || '' }); setViewMode('edit'); }}>Edit</button>
                <button className="btn secondary" onClick={(e) => { e.preventDefault(); /* future: open/preview */ }}>Open</button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default PlannerPanel;
