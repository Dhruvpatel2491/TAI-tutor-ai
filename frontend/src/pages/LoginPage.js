import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';

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
      await authService.registerOrLogin(email, password, remember);
      navigate('/home');
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
