import React, { useState } from 'react';
import { DEFAULT_BACKEND_URL } from '../config';

const TOKEN_KEY = 'auth_token';

function AuthPanel({ backendURL = DEFAULT_BACKEND_URL }) {
  const [userId, setUserId] = useState('');
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || '');
  const [msg, setMsg] = useState('');

  const saveToken = (t) => {
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
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
        saveToken(data.token);
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
        saveToken(data.token);
        setMsg('Logged in');
      } else {
        setMsg(data.error || 'Login failed');
      }
    } catch (e) {
      setMsg('Network error');
    }
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken('');
    setMsg('Logged out');
  };

  return (
    <div className="auth-panel">
      <h3>Auth</h3>
      <div>
        <input placeholder="user id" value={userId} onChange={(e) => setUserId(e.target.value)} />
        <button onClick={register}>Register</button>
        <button onClick={login}>Login</button>
        <button onClick={logout}>Logout</button>
      </div>
      <div style={{ marginTop: 8 }}>
        <strong>Token:</strong>
        <div style={{ wordBreak: 'break-all' }}>{token || 'not logged in'}</div>
      </div>
      <div style={{ color: 'green', marginTop: 6 }}>{msg}</div>
    </div>
  );
}

export default AuthPanel;
