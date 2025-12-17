import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// Clear previous session/local storage when running the dev server (npm start)
// This ensures stale sessions don't persist between dev server restarts.
try {
  if (process && process.env && process.env.NODE_ENV === 'development') {
    // Best-effort: clear both sessionStorage and localStorage
    try {
      sessionStorage.clear();
    } catch (e) {
      // ignore (e.g., SSR or restricted environments)
    }
    try {
      localStorage.clear();
    } catch (e) {
      // ignore
    }
    // small debug message to make behavior visible during dev
    // eslint-disable-next-line no-console
    console.info('Development start: cleared sessionStorage and localStorage');
  }
} catch (e) {
  // ignore any errors accessing process in some environments
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
