import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Link, useNavigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import ProtectedRoute from './components/ProtectedRoute';
import { authService } from './services/authService';

function Header() {
  const navigate = useNavigate();
  const user = authService.getCurrentUser();

  const logout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <header className="app-header" style={{ display: 'flex', justifyContent: 'space-between', padding: 12 }}>
      <div>
        <Link to="/home" style={{ marginRight: 12 }}>Home</Link>
        <Link to="/chat">Chat</Link>
      </div>
      <div>
        {user ? (
          <>
            <span style={{ marginRight: 12 }}>Welcome, {user.email}</span>
            <button onClick={logout}>Logout</button>
          </>
        ) : (
          <Link to="/login">Login</Link>
        )}
      </div>
    </header>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Header />
      <main style={{ padding: 12 }}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/home" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
          <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
          <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
