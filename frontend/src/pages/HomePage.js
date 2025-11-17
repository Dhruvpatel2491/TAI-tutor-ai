import React, { useState } from 'react';
import { authService } from '../services/authService';
import { planService } from '../services/planService';

const HomePage = () => {
  const user = authService.getCurrentUser();
  const [plan, setPlan] = useState(user ? planService.getCurrentPlan(user.email) : null);
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');

  const openModal = () => {
    setName('');
    setDesc('');
    setShowModal(true);
    // focus handled by autoFocus on input
  };

  const save = () => {
    if (!name.trim()) return;
    const saved = planService.createOrReplacePlan(user.email, { name: name.trim(), description: desc });
    setPlan(saved);
    setShowModal(false);
  };

  const exportPlan = () => {
    const blob = planService.exportPlan(user.email);
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${plan.name || 'plan'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      <h2>Welcome, {user?.email}</h2>

      <section style={{ border: '1px solid #ddd', padding: 12, borderRadius: 6 }}>
        <h3>Current Plan</h3>
        {plan ? (
          <div>
            <strong>{plan.name}</strong>
            <div style={{ fontSize: 12, color: '#666' }}>{new Date(plan.createdAt).toLocaleString()}</div>
            <p>{plan.description}</p>
            <div>
              <button onClick={openModal}>Recreate new plan</button>
              <button onClick={exportPlan} style={{ marginLeft: 8 }}>Export plan</button>
            </div>
          </div>
        ) : (
          <div>
            <p>No current plan</p>
            <button onClick={openModal}>Recreate new plan</button>
          </div>
        )}
      </section>

      {showModal && (
        <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.3)' }}>
          <div style={{ background: '#fff', padding: 16, borderRadius: 8, width: 400 }} onClick={(e) => e.stopPropagation()}>
            <h4>Create a new plan</h4>
            <div>
              <label htmlFor="plan-name">Name</label>
              <input id="plan-name" autoFocus value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div style={{ marginTop: 8 }}>
              <label htmlFor="plan-desc">Description</label>
              <textarea id="plan-desc" rows={4} value={desc} onChange={(e) => setDesc(e.target.value)} />
            </div>
            <div style={{ marginTop: 8 }}>
              <button onClick={save}>Save</button>
              <button onClick={() => setShowModal(false)} style={{ marginLeft: 8 }}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomePage;
