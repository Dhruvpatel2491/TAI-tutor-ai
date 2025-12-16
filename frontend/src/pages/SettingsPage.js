import React, { useEffect, useState } from 'react';
// import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';
import AdminPasswordModal from '../components/AdminPasswordModal';
import '../styles/SettingsPage.css';

const SettingsPage = () => {
  // const navigate = useNavigate();
  const [userStats, setUserStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAdminModal, setShowAdminModal] = useState(false);

  useEffect(() => {
    fetchUserStats();
  }, []);

  const fetchUserStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const stats = await authService.getUserStats();
      setUserStats(stats);
      console.log('Fetched user stats:', stats);
    } catch (err) {
      console.error('Failed to fetch user stats:', err);
      setError('Failed to load user statistics. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-page">
        <div className="settings-container">
          <div className="loading-spinner">
            <div className="spinner"></div>
            <p>Loading your settings...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="settings-page">
        <div className="settings-container">
          <div className="error-message">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <h3>Error Loading Settings</h3>
            <p>{error}</p>
            <button className="btn" onClick={fetchUserStats}>
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const handleAdminClick = () => {
    setShowAdminModal(true);
  };

  return (
    <div className="settings-page">
      <div className="settings-container">
        <div className="settings-header">
          <div className="header-content">
            <div className="header-text">
              <h1>Settings</h1>
              <p className="settings-subtitle">View your profile and activity statistics</p>
            </div>
            <button className="admin-access-btn" onClick={handleAdminClick} title="Admin Access">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                <path d="M12 12c-1.1 0-2-.9-2-2V8c0-1.1.9-2 2-2s2 .9 2 2v2c0 1.1-.9 2-2 2z" opacity="0.5"/>
              </svg>
              <span className="admin-text">Admin</span>
            </button>
          </div>
        </div>

        {/* Profile Section */}
        <section className="settings-section">
          <div className="section-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
            <h2>Profile Information</h2>
          </div>
          
          <div className="settings-grid">
            <div className="settings-field">
              <label>Name</label>
              <div className="field-value">
                <span>{userStats?.name || 'N/A'}</span>
              </div>
            </div>

            <div className="settings-field">
              <label>Email Address</label>
              <div className="field-value">
                <span>{userStats?.email || 'N/A'}</span>
              </div>
            </div>
          </div>
        </section>

        {/* Activity Statistics Section */}
        <section className="settings-section">
          <div className="section-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            <h2>Activity Statistics</h2>
          </div>
          
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon chat-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
              <div className="stat-content">
                <div className="stat-label">Chats Initiated</div>
                <div className="stat-value">{userStats?.chats_count || 0}</div>
                <div className="stat-description">Total chat sessions created</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon plan-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
              </div>
              <div className="stat-content">
                <div className="stat-label">Plans Created</div>
                <div className="stat-value">{userStats?.plans_count || 0}</div>
                <div className="stat-description">Study plans saved</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon quiz-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                  <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
              </div>
              <div className="stat-content">
                <div className="stat-label">Overall Quiz Score</div>
                <div className="stat-value">{userStats?.quiz_score || 0}%</div>
                <div className="stat-description">Average across all quizzes</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon codequest-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="16 18 22 12 16 6"></polyline>
                  <polyline points="8 6 2 12 8 18"></polyline>
                </svg>
              </div>
              <div className="stat-content">
                <div className="stat-label">CodeQuest Score</div>
                <div className="stat-value">{userStats?.codequest_score || 0}%</div>
                <div className="stat-description">Average challenge score</div>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Admin Password Modal */}
      {showAdminModal && (
        <AdminPasswordModal
          onClose={() => setShowAdminModal(false)}
          onSuccess={() => setShowAdminModal(false)}
        />
      )}
    </div>
  );
};

export default SettingsPage;
