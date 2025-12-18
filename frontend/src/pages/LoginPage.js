import React, { useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
// backend HTTP helpers are used by authService; no direct apiPost usage here
import { authService } from '../services/authService';

// Token key is managed by services/auth

function validateEmail(email) {
  return /\S+@\S+\.\S+/.test(email);
}

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const errorRef = useRef(null);

  const submit = async (e) => {
    // Submit handles explicit login (form submit)
    e.preventDefault();
    setError('');
    
    if (!validateEmail(email)) {
      setError('Please enter a valid email.');
      errorRef.current?.focus();
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      errorRef.current?.focus();
      return;
    }

    setLoading(true);

    try {
      // Explicit login flow
      const token = await authService.login(email, password, remember);
      if (!token) throw new Error('No token returned from server');
      // Ensure persisted
      try { if (!authService.getToken()) authService.setToken(token, remember); } catch (e) {}

    // Save a minimal local user profile so HomePage and other components
    // can show a lightweight profile even when server doesn't return one.
    try {
      const users = authService._internal.loadUsers();
      const lower = email.trim().toLowerCase();
      if (!users[lower]) {
        users[lower] = { email: lower, createdAt: new Date().toISOString() };
        authService._internal.saveUsers(users);
      } else {
        // update last-seen
        users[lower].lastSeen = new Date().toISOString();
        authService._internal.saveUsers(users);
      }
    } catch (e) {
      // Non-fatal: continue even if local profile save fails
    }

    // Navigate after token is persisted and local user saved
    navigate('/home');
    navigate(0); // force reload to update auth-dependent components
    } catch (err) {
      setError(err.message || 'Login failed');
      errorRef.current?.focus();
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="auth-card">
        {/* Logo */}
        <div className="auth-logo">
          <img 
            src="/img/tai-logo-main.png" 
            alt="TAI Tutor Logo" 
            style={{ 
              width: '80px', 
              height: '80px', 
              borderRadius: '50%', 
              objectFit: 'cover' 
            }} 
          />
        </div>

        <h1 className="auth-title">TAI - Tutor AI</h1>
        <p className="auth-subtitle">Sign in to continue learning</p>

        <form onSubmit={submit} aria-describedby="login-error" noValidate>
          {error && (
            <div role="alert" id="login-error" tabIndex={-1} ref={errorRef} className="auth-error">
              {error}
            </div>
          )}

          <div className="form-row">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              aria-required="true"
              autoFocus
              disabled={loading}
            />
          </div>

          <div className="form-row">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              required
              aria-required="true"
              disabled={loading}
            />
          </div>

          <div className="form-row checkbox-row">
            <label>
              <input 
                type="checkbox" 
                checked={remember} 
                onChange={(e) => setRemember(e.target.checked)}
                disabled={loading}
              />
              <span>Remember me</span>
            </label>
          </div>

          <div className="auth-buttons">
            <button type="submit" className="btn" disabled={loading}>
              {loading ? 'Logging in...' : 'Log in'}
            </button>
          </div>
        </form>

        <p className="auth-footer">
          Don't have an account? <Link to="/register" className="auth-link">Register here</Link>
        </p>

        <p className="auth-footer">
          New users: a local account will be created and stored in your browser. 
          Do not use production passwords here.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
