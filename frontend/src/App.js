import React, { useEffect, useState } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import RegistrationPage from './pages/RegistrationPage';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import QuizPage from './pages/QuizPage';
import CodeQuestDashboardPage from './pages/CodeQuestDashboardPage';
import CodeQuestSessionPage from './pages/CodeQuestSessionPage';
import CodeQuestFeedbackPage from './pages/CodeQuestFeedbackPage';
import SettingsPage from './pages/SettingsPage';
import AdminPage from './pages/AdminPage';
import ProtectedRoute from './components/ProtectedRoute';
import PlannerPanel from './components/PlannerPanel';
import { authService } from './services/authService';

function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const [effectiveEmail, setEffectiveEmail] = useState(null);
  const [effectiveName, setEffectiveName] = useState(null);
  const [hasToken, setHasToken] = useState(Boolean(authService.getToken()));

  useEffect(() => {
    
    let mounted = true;
    const server = authService.getCurrentUser();
      // console.log('Fetched current user from server:', server.email);
    // console.log('BACKEND_URL=', process.env.REACT_APP_BACKEND_URL);
      if (!mounted) return;
      if (server && server.email) {
        setEffectiveEmail(server.email);
        setEffectiveName(server.name);
        // console.log('Using server user for effectiveEmail:', server);
      } else {
        const localUser = authService.getCurrentUser();
        if (localUser && localUser.email) {
          setEffectiveEmail(localUser.email);
          setEffectiveName(localUser.name);
        } else {
          const dec = authService.decodeToken(authService.getToken());
          setEffectiveEmail(dec ? (dec.sub || dec.email || dec.email) : null);
        }
      }


    const unsub = authService.onAuthChange((t) => {
      setHasToken(Boolean(t));
      // when token is removed, clear the effective email so header hides
      if (!t) setEffectiveEmail(null);
    });
    return () => { unsub(); mounted = false };
  }, []);

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/' || location.pathname === '/home';
    return location.pathname.startsWith(path);
  };

  const logout = () => {
    // clear both local demo service and token
    authService.clearToken();
    try { authService.logout(); } catch (e) {}
    // also clear effectiveEmail state so header hides immediately
    setEffectiveEmail(null);
    navigate('/login');
  };
  // console.log('Using local user for effectiveEmail:', effectiveEmail);

  // Hide header on admin page
  if (location.pathname === '/admin') {
    return null;
  }

  if (!effectiveEmail) return null;

  return (
    <header className="app-header">
      <div className="header-inner" role="banner">
        {/* Logo and Brand */}
        <div className="header-brand">
          <div className="header-logo">
            {/* TAI Logo - warm accent color */}
            <svg viewBox="0 0 841.9 595.3" fill="currentColor" style={{ color: 'var(--color-primary)' }}>
              <g>
                <path d="M666.3 296.5c0-32.5-40.7-63.3-103.1-82.4 14.4-63.6 8-114.2-20.2-130.4-6.5-3.8-14.1-5.6-22.4-5.6v22.3c4.6 0 8.3.9 11.4 2.6 13.6 7.8 19.5 37.5 14.9 75.7-1.1 9.4-2.9 19.3-5.1 29.4-19.6-4.8-41-8.5-63.5-10.9-13.5-18.5-27.5-35.3-41.6-50 32.6-30.3 63.2-46.9 84-46.9V78c-27.5 0-63.5 19.6-99.9 53.6-36.4-33.8-72.4-53.2-99.9-53.2v22.3c20.7 0 51.4 16.5 84 46.6-14 14.7-28 31.4-41.3 49.9-22.6 2.4-44 6.1-63.6 11-2.3-10-4-19.7-5.2-29-4.7-38.2 1.1-67.9 14.6-75.8 3-1.8 6.9-2.6 11.5-2.6V78.5c-8.4 0-16 1.8-22.6 5.6-28.1 16.2-34.4 66.7-19.9 130.1-62.2 19.2-102.7 49.9-102.7 82.3 0 32.5 40.7 63.3 103.1 82.4-14.4 63.6-8 114.2 20.2 130.4 6.5 3.8 14.1 5.6 22.5 5.6 27.5 0 63.5-19.6 99.9-53.6 36.4 33.8 72.4 53.2 99.9 53.2 8.4 0 16-1.8 22.6-5.6 28.1-16.2 34.4-66.7 19.9-130.1 62-19.1 102.5-49.9 102.5-82.3zm-130.2-66.7c-3.7 12.9-8.3 26.2-13.5 39.5-4.1-8-8.4-16-13.1-24-4.6-8-9.5-15.8-14.4-23.4 14.2 2.1 27.9 4.7 41 7.9zm-45.8 106.5c-7.8 13.5-15.8 26.3-24.1 38.2-14.9 1.3-30 2-45.2 2-15.1 0-30.2-.7-45-1.9-8.3-11.9-16.4-24.6-24.2-38-7.6-13.1-14.5-26.4-20.8-39.8 6.2-13.4 13.2-26.8 20.7-39.9 7.8-13.5 15.8-26.3 24.1-38.2 14.9-1.3 30-2 45.2-2 15.1 0 30.2.7 45 1.9 8.3 11.9 16.4 24.6 24.2 38 7.6 13.1 14.5 26.4 20.8 39.8-6.3 13.4-13.2 26.8-20.7 39.9zm32.3-13c5.4 13.4 10 26.8 13.8 39.8-13.1 3.2-26.9 5.9-41.2 8 4.9-7.7 9.8-15.6 14.4-23.7 4.6-8 8.9-16.1 13-24.1zM421.2 430c-9.3-9.6-18.6-20.3-27.8-32 9 .4 18.2.7 27.5.7 9.4 0 18.7-.2 27.8-.7-9 11.7-18.3 22.4-27.5 32zm-74.4-58.9c-14.2-2.1-27.9-4.7-41-7.9 3.7-12.9 8.3-26.2 13.5-39.5 4.1 8 8.4 16 13.1 24 4.7 8 9.5 15.8 14.4 23.4zM420.7 163c9.3 9.6 18.6 20.3 27.8 32-9-.4-18.2-.7-27.5-.7-9.4 0-18.7.2-27.8.7 9-11.7 18.3-22.4 27.5-32zm-74 58.9c-4.9 7.7-9.8 15.6-14.4 23.7-4.6 8-8.9 16-13 24-5.4-13.4-10-26.8-13.8-39.8 13.1-3.1 26.9-5.8 41.2-7.9zm-90.5 125.2c-35.4-15.1-58.3-34.9-58.3-50.6 0-15.7 22.9-35.6 58.3-50.6 8.6-3.7 18-7 27.7-10.1 5.7 19.6 13.2 40 22.5 60.9-9.2 20.8-16.6 41.1-22.2 60.6-9.9-3.1-19.3-6.5-28-10.2zM310 490c-13.6-7.8-19.5-37.5-14.9-75.7 1.1-9.4 2.9-19.3 5.1-29.4 19.6 4.8 41 8.5 63.5 10.9 13.5 18.5 27.5 35.3 41.6 50-32.6 30.3-63.2 46.9-84 46.9-4.5-.1-8.3-1-11.3-2.7zm237.2-76.2c4.7 38.2-1.1 67.9-14.6 75.8-3 1.8-6.9 2.6-11.5 2.6-20.7 0-51.4-16.5-84-46.6 14-14.7 28-31.4 41.3-49.9 22.6-2.4 44-6.1 63.6-11 2.3 10.1 4.1 19.8 5.2 29.1zm38.5-66.7c-8.6 3.7-18 7-27.7 10.1-5.7-19.6-13.2-40-22.5-60.9 9.2-20.8 16.6-41.1 22.2-60.6 9.9 3.1 19.3 6.5 28.1 10.2 35.4 15.1 58.3 34.9 58.3 50.6-.1 15.7-23 35.6-58.4 50.6zM320.8 78.4z"/>
                <circle cx="420.9" cy="296.5" r="45.7"/>
              </g>
            </svg>
          </div>
          <span className="header-title">TAI - <span>Tutor AI</span></span>
        </div>

        {/* Navigation */}
        <nav aria-label="main navigation">
          <ul className="tabs">
            <li>
              <Link to="/home" className={`tab ${isActive('/home') ? 'tab-active' : ''}`}>Home</Link>
            </li>
            <li>
              <Link to="/chat" className={`tab ${isActive('/chat') ? 'tab-active' : ''}`}>Chat</Link>
            </li>
            <li>
              <Link to="/planner" className={`tab ${isActive('/planner') ? 'tab-active' : ''}`}>Planner</Link>
            </li>
            <li>
              <Link to="/quiz" className={`tab ${isActive('/quiz') ? 'tab-active' : ''}`}>Quiz</Link>
            </li>
            <li>
              <Link to="/codequest" className={`tab ${isActive('/codequest') ? 'tab-active' : ''}`}>CodeQuest</Link>
            </li>
            <li>
              <Link to="/settings" className={`tab ${isActive('/settings') ? 'tab-active' : ''}`}>Settings</Link>
            </li>
          </ul>
        </nav>

        {/* User Info */}
        <div className="header-user">
          <span className="welcome-mr">{effectiveName || effectiveEmail}</span>
          <span className={`header-status-dot ${hasToken ? '' : 'offline'}`} title={hasToken ? 'Connected' : 'Offline'} />
          <button type="button" className="btn btn-sm secondary" onClick={logout}>Logout</button>
        </div>
      </div>
    </header>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Header />
        <div className="content">
          <div className="output">
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegistrationPage />} />
              <Route path="/home" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
              <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
              <Route path="/planner" element={<ProtectedRoute><PlannerPanel /></ProtectedRoute>} />
              <Route path="/quiz" element={<ProtectedRoute><QuizPage /></ProtectedRoute>} />
              <Route path="/codequest" element={<ProtectedRoute><CodeQuestDashboardPage /></ProtectedRoute>} />
              <Route path="/codequest/:sessionId" element={<ProtectedRoute><CodeQuestSessionPage /></ProtectedRoute>} />
              <Route path="/codequest/:sessionId/feedback" element={<ProtectedRoute><CodeQuestFeedbackPage /></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
              <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
              <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
            </Routes>
          </div>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
