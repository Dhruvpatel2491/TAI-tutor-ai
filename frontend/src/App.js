import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import ProtectedRoute from './components/ProtectedRoute';
import PlannerPanel from './components/PlannerPanel';
import { authService } from './services/authService';

function Header() {
  const navigate = useNavigate();
  const user = authService.getCurrentUser();
  const location = useLocation();

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/' || location.pathname === '/home';
    return location.pathname.startsWith(path);
  };

  const logout = () => {
    authService.logout();
    navigate('/login');
  };
  if (!user) return null;

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
          </ul>
        </nav>

        <div>
          <span className="welcome-mr">Welcome, {user.email}</span>
          <button type="button" className="btn" onClick={logout}>Logout</button>
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
              <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
            </Routes>
          </div>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
