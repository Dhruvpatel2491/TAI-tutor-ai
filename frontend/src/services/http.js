// Centralized HTTP helper that attaches Authorization header when a token
// is present in the app's session storage and sets JSON Content-Type for object bodies.
// Prefer using the demo authService (which stores session objects) so tokens
// created by the demo login/register flow are discovered correctly.
import authService from './authService';
export async function apiRequest(url, { method = 'GET', body = undefined, headers = {}, signal = undefined, mode = undefined } = {}) {
  // authService.getToken() handles either string tokens or session objects
  const token = (authService && typeof authService.getToken === 'function') ? (authService.getToken() || '') : '';
  const h = { ...(headers || {}) };

  // If body is provided and not a FormData, default to JSON
  const isForm = (typeof FormData !== 'undefined') && (body instanceof FormData);
  if (body !== undefined && !isForm) {
    if (!Object.keys(h).some(k => k.toLowerCase() === 'content-type')) {
      h['Content-Type'] = 'application/json';
    }
  }

  if (token) {
    // console.log("Attaching token to request:", token);
    h['Authorization'] = `Bearer ${token}`;
  }

  const init = { method, headers: h };
  if (signal) init.signal = signal;
  if (mode) init.mode = mode;
  if (body !== undefined) {
    init.body = (isForm || typeof body === 'string') ? body : JSON.stringify(body);
  }

  return fetch(url, init);
}

export const apiGet = (url) => apiRequest(url, { method: 'GET' });
export const apiPost = (url, body) => {

  return apiRequest(url, { method: 'POST', body });
};

const http = { apiRequest, apiGet, apiPost };
export default http;
