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
// import PlannerPanel from './components/PlannerPanel';
import PlannerPage from './pages/PlannerPage';
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
            {/* TAI Logo */}
            <img 
              src="/img/tai-logo-main.png" 
              alt="TAI Tutor Logo" 
              style={{ 
                width: '36px', 
                height: '36px', 
                borderRadius: '50%', 
                objectFit: 'cover' 
              }} 
            />
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
              <Route path="/planner" element={<ProtectedRoute><PlannerPage /></ProtectedRoute>} />
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
