import React, { useState } from 'react';
import { DEFAULT_BACKEND_URL } from '../config';
import { authService } from '../services/authService';

function AuthPanel({ backendURL = DEFAULT_BACKEND_URL }) {
  const [userId, setUserId] = useState('');
  const [token, setToken] = useState(() => {
    try { return authService.getToken() || ''; } catch (e) { return ''; }
  });
  const [msg, setMsg] = useState('');

  const saveToken = (t, remember = true) => {
    try { authService.setToken(t, remember); } catch (e) {}
    setToken(typeof t === 'object' ? (t.token || JSON.stringify(t)) : t);
  };

  const register = async () => {
    setMsg('');
    try {
      const res = await fetch(`${backendURL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      const data = await res.json();
      if (res.ok) {
        saveToken(data.token, true);
        setMsg('Registered and logged in');
      } else {
        setMsg(data.error || 'Registration failed');
      }
    } catch (e) {
      setMsg('Network error');
    }
  };

  const login = async () => {
    setMsg('');
    try {
      const res = await fetch(`${backendURL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      const data = await res.json();
      if (res.ok) {
        saveToken(data.token, true);
        setMsg('Logged in');
      } else {
        setMsg(data.error || 'Login failed');
      }
    } catch (e) {
      setMsg('Network error');
    }
  };

  const logout = () => {
    try { authService.clearToken(); } catch (e) {}
    setToken('');
    setMsg('Logged out');
  };

  return (
    <div className="auth-panel card">
      <h3>Auth</h3>
      <div className="form-row">
        <input placeholder="user id" value={userId} onChange={(e) => setUserId(e.target.value)} aria-label="user id" />
  <button type="button" className="btn ml-8" onClick={register}>Register</button>
  <button type="button" className="btn ml-8" onClick={login}>Login</button>
  <button type="button" className="btn secondary ml-8" onClick={logout}>Logout</button>
      </div>
      <div className="form-row">
        <strong>Token:</strong>
  <div className="word-break">{token || 'not logged in'}</div>
      </div>
  <div className="message text-success mt-6" aria-live="polite">{msg}</div>
    </div>
  );
}

export default AuthPanel;
