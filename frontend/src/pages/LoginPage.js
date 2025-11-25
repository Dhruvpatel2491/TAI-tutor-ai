import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();
  const errorRef = useRef(null);

  const submit = async (e) => {
    // Submit handles explicit login (form submit)
    e.preventDefault();
    setError('');
    //console.log('[LoginPage] submit triggered for', email, 'remember=', remember);
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
        //console.log('[LoginPage] Saved local user profile for', lower);
      } else {
        // update last-seen
        users[lower].lastSeen = new Date().toISOString();
        authService._internal.saveUsers(users);
        //console.log('[LoginPage] Updated local user lastSeen for', lower);
      }
    } catch (e) {
      //console.log('[LoginPage] Failed to save local user profile:', e);
    }

    // Navigate after token is persisted and local user saved
    navigate('/home');
    navigate(0); // force reload to update auth-dependent components
    } catch (err) {
      setError(err.message || 'Login failed');
      errorRef.current?.focus();
    }
  };

  const handleRegister = async (e) => {
    // separate register action
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
    try {
      const token = await authService.register(email, password, remember);
      if (!token) throw new Error('No token returned from server');
      try { if (!authService.getToken()) authService.setToken(token, remember); } catch (e) {}

      // Save minimal local profile
      try {
        const users = authService._internal.loadUsers();
        const lower = email.trim().toLowerCase();
        if (!users[lower]) {
          users[lower] = { email: lower, createdAt: new Date().toISOString() };
          authService._internal.saveUsers(users);
        } else {
          users[lower].lastSeen = new Date().toISOString();
          authService._internal.saveUsers(users);
        }
      } catch (e) {}

      navigate('/home');
      navigate(0);
    } catch (err) {
      setError(err.message || 'Register failed');
      errorRef.current?.focus();
    }
  };

  return (
  <div className="container max-w-520">
      <h2>Login</h2>
      <form onSubmit={submit} aria-describedby="login-error" noValidate>
        {error && (
          <div role="alert" id="login-error" tabIndex={-1} ref={errorRef} className="message text-danger">
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
            required
            aria-required="true"
            autoFocus
          />
        </div>

        <div className="form-row">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            aria-required="true"
          />
        </div>

        <div className="form-row">
          <label>
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember me
          </label>
        </div>

        <div className="form-row" style={{ display: 'flex', gap: '8px' }}>
          <button type="submit" className="btn">Log in</button>
          <button type="button" className="btn btn-secondary" onClick={handleRegister}>Register</button>
        </div>
      </form>

      <p className="muted mt-12">
        New users: a local account will be created and stored in your browser. Do not use
        production passwords here.
      </p>
    </div>
  );
};

export default LoginPage;
