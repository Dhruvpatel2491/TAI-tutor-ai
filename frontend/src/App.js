import React, { useEffect, useState } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import QuizPage from './pages/QuizPage';
import ProtectedRoute from './components/ProtectedRoute';
import PlannerPanel from './components/PlannerPanel';
import { authService } from './services/authService';

function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const [effectiveEmail, setEffectiveEmail] = useState(null);
  const [hasToken, setHasToken] = useState(Boolean(authService.getToken()));

  useEffect(() => {
    
    let mounted = true;
    const server = authService.getCurrentUser();
      // console.log('Fetched current user from server:', server.email);
    // console.log('BACKEND_URL=', process.env.REACT_APP_BACKEND_URL);
      if (!mounted) return;
      if (server && server.email) {
        setEffectiveEmail(server.email);
      } else {
        const localUser = authService.getCurrentUser();
        if (localUser && localUser.email) setEffectiveEmail(localUser.email);
        else {
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

  if (!effectiveEmail) return null;

  return (
    <header className="app-header header-flex">
      <div className="header-inner container" role="banner">
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
          </ul>
        </nav>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span className="welcome-mr">Welcome, {effectiveEmail}</span>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: 6, background: hasToken ? 'green' : 'gray', display: 'inline-block' }} title={hasToken ? 'Token present' : 'No token'} />
            <button type="button" className="btn" onClick={logout}>Logout</button>
          </div>
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
              <Route path="/home" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
              <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
              <Route path="/planner" element={<ProtectedRoute><PlannerPanel /></ProtectedRoute>} />
              <Route path="/quiz" element={<ProtectedRoute><QuizPage /></ProtectedRoute>} />
              <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
            </Routes>
          </div>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
