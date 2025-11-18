import React from 'react';
import { authService } from '../services/authService';
import { Link } from 'react-router-dom';

const HomePage = () => {
  const user = authService.getCurrentUser();

  return (
  <div className="container home-hero">
      <h2>Next Level AI Tutoring</h2>
      <p>
        Welcome{user?.email ? `, ${user.email}` : ''}! Create a custom learning pathway, get hints, and practice with
        interactive exercises. Use the Planner to create goals and the Chat to get guided help.
      </p>

      <div className="card" style={{ marginTop: 20 }}>
        <h3>Get started</h3>
        <p className="muted">Quick links to help you begin:</p>
        <div style={{ display: 'flex', gap: 12, marginTop: 12, flexWrap: 'wrap' }}>
          <Link to="/planner" className="btn">Open Planner</Link>
          <Link to="/chat" className="btn secondary">Open Chat</Link>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12, marginTop: 18 }}>
        <div className="card">
          <h4>Personalized Plans</h4>
          <p className="muted small-text">Create a study plan tailored to your pace and goals.</p>
        </div>
        <div className="card">
          <h4>Interactive Practice</h4>
          <p className="muted small-text">Practice problems with step-by-step hints and feedback.</p>
        </div>
        <div className="card">
          <h4>Multimodal Help</h4>
          <p className="muted small-text">Get explanations with text, code examples, and examples from your course materials.</p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
