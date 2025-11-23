// Consolidated auth wrapper: delegate to authService so there's a single
// source-of-truth for session/token storage and change events.
import authService from './authService';

// Re-export the core helpers expected by other modules in the app.
export function getToken() {
  try {
    return (authService && typeof authService.getToken === 'function') ? authService.getToken() : null;
  } catch (e) {
    return null;
  }
}

export function setToken(token, remember = true) {
  try {
    if (authService && typeof authService.setToken === 'function') {
      return authService.setToken(token, remember);
    }
  } catch (e) {
    // ignore
  }
}

export function clearToken() {
  try { if (authService && typeof authService.clearToken === 'function') authService.clearToken(); } catch (e) {}
}

export function decodeToken(token) {
  try {
    if (authService && typeof authService.decodeToken === 'function') return authService.decodeToken(token);
    // fallback: attempt a simple JWT-like decode
    if (!token) return null;
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const payload = parts[1];
    const padded = payload + '='.repeat((-payload.length) % 4);
    const json = JSON.parse(atob(padded.replace(/-/g, '+').replace(/_/g, '/')));
    return json;
  } catch (e) {
    return null;
  }
}

export async function fetchCurrentUser() {
  // Do not expose server-side user_id/default_dev_user to the app UI. Prefer
  // the local authService profile which no longer returns an email-based id.
  try {
    if (authService && typeof authService.fetchCurrentUser === 'function') return authService.fetchCurrentUser();
  } catch (e) {}
  return null;
}

export function onAuthChange(cb) {
  try {
    if (authService && typeof authService.onAuthChange === 'function') return authService.onAuthChange(cb);
    const handler = (e) => cb(e.detail && e.detail.token ? e.detail.token : null);
    window.addEventListener('auth_token_changed', handler);
    return () => window.removeEventListener('auth_token_changed', handler);
  } catch (e) {
    return () => {};
  }
}

const auth = { getToken, setToken, clearToken, decodeToken, fetchCurrentUser, onAuthChange };
export default auth;
