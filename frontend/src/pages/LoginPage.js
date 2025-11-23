import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost } from '../services/http';
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
    e.preventDefault();
    setError('');
    console.log('[LoginPage] submit triggered for', email, 'remember=', remember);
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
      // Call backend register/login endpoint and store JWT
      console.log("Submitting login for email:", process.env.REACT_APP_BACKEND_URL || '' );
      const base = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/$/, '') || '';
      const res = await apiPost(`${base}/auth/register`, { user_id: email });
      console.log("[LoginPage] Response object from register attempt:", res);
      // If register returns non-OK, try login
      let data = await res.json().catch(() => ({}));
      // console.log('[LoginPage] Parsed body from register attempt:', data);
      if (!res.ok) {
        const res2 = await apiPost(`${base}/auth/login`, { user_id: email });
        data = await res2.json().catch(() => ({}));
        console.log('[LoginPage] Response from login attempt:', res2);
        console.log('[LoginPage] Parsed body from login attempt:', data);
        if (!res2.ok) throw new Error(data.error || 'Login failed');
      }
    const token = data.token;
    console.log('[LoginPage] Received token from server:', token);
    if (!token) throw new Error('No token returned from server');

    // persist token (use remember checkbox) and notify other components
    try {
      authService.setToken(token, remember);
      // ensure token persisted before navigating (read back)
      let persisted = authService.getToken();
      // if token is wrapped object, try to read .token
      const tokenStr = typeof token === 'string' ? token : (token && token.token) ? token.token : null;
      let attempts = 0;
      while ((!persisted || (typeof persisted === 'object' && persisted.token && tokenStr && persisted.token !== tokenStr)) && attempts < 5) {
        // small delay to allow storage to settle in constrained environments
        // eslint-disable-next-line no-await-in-loop
        await new Promise((r) => setTimeout(r, 50));
        persisted = authService.getToken();
        attempts += 1;
      }
      // console.log('[LoginPage] Persisted token after setToken:', persisted);
    } catch (e) { console.log('[LoginPage] Error while saving token locally:', e); }

    // Save a minimal local user profile so HomePage and other components
    // can show a lightweight profile even when server doesn't return one.
    try {
      const users = authService._internal.loadUsers();
      const lower = email.trim().toLowerCase();
      if (!users[lower]) {
        users[lower] = { email: lower, createdAt: new Date().toISOString() };
        authService._internal.saveUsers(users);
        console.log('[LoginPage] Saved local user profile for', lower);
      } else {
        // update last-seen
        users[lower].lastSeen = new Date().toISOString();
        authService._internal.saveUsers(users);
        console.log('[LoginPage] Updated local user lastSeen for', lower);
      }
    } catch (e) {
      console.log('[LoginPage] Failed to save local user profile:', e);
    }

    // Navigate after token is persisted and local user saved
    navigate('/home');
    navigate(0); // force reload to update auth-dependent components
    } catch (err) {
      setError(err.message || 'Login failed');
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

        <div className="form-row">
          <button type="submit" className="btn">Sign in / Register</button>
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
