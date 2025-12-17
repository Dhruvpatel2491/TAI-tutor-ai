import React, { useEffect } from 'react';
import { authService } from '../services/authService';
import { Link } from 'react-router-dom';

const HomePage = () => {

  const user = authService.getCurrentUser();

  // Log render-time user synchronously
  // console.log('HomePage rendered (sync) for user:', user);

  // Also fetch the async/minimal profile and log it when available
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
          const profile = await authService.fetchCurrentUser();
          if (mounted) console.info('HomePage fetched async profile:', profile);
        } catch (e) {
        if (mounted) console.error('HomePage: error fetching current user profile', e);
      }
    })();
    return () => { mounted = false; };
  }, []);


  

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="home-hero">
        <div className="hero-content">
          <h1 className="hero-title">Next Level AI Tutoring</h1>
          <p className="hero-subtitle">
            Welcome{user?.email ? `, ${user.email}` : ''}! Create a custom learning pathway, get hints, 
            and practice with interactive exercises. Use the Planner to create goals and the Chat to get guided help.
          </p>
          <div className="hero-actions">
            <Link to="/planner" className="btn">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
              Open Planner
            </Link>
            <Link to="/chat" className="btn btn-secondary">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              Open Chat
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Cards */}
      <section className="features-section">
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
            </div>
            <h3>Personalized Plans</h3>
            <p>Create a study plan tailored to your pace and goals.</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 18 22 12 16 6"></polyline>
                <polyline points="8 6 2 12 8 18"></polyline>
              </svg>
            </div>
            <h3>Interactive Practice</h3>
            <p>Practice problems with step-by-step hints and feedback.</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
              </svg>
            </div>
            <h3>Multimodal Help</h3>
            <p>Get explanations with text, code examples, and course materials.</p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
