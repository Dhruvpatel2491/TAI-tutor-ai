/* Jest tests for authService storage behavior */

describe('authService storage', () => {
  const TOKEN_KEY = 'tutor_token_v1';

  beforeEach(() => {
    // Clear storages and reset module cache so authService re-initializes
    try { localStorage.clear(); } catch (e) {}
    try { sessionStorage.clear(); } catch (e) {}
    jest.resetModules();
  });

  test('setToken with remember=false stores token in sessionStorage only', () => {
    const { authService } = require('../authService');
    authService.setToken({ token: 'sess-123', email: 'me@test.local', issuedAt: 'now' }, false);

    const sessRaw = sessionStorage.getItem(TOKEN_KEY);
    const localRaw = localStorage.getItem(TOKEN_KEY);

    expect(sessRaw).toBeTruthy();
    expect(localRaw).toBeNull();

    const parsed = JSON.parse(sessRaw);
    expect(parsed.token).toBe('sess-123');
    // getToken should return string token when possible
    expect(authService.getToken()).toBe('sess-123');

    // clear and ensure removed
    authService.clearToken();
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(authService.getToken()).toBeNull();
  });

  test('setToken with remember=true stores token in localStorage only', () => {
    const { authService } = require('../authService');
    authService.setToken({ token: 'persist-456', email: 'you@test.local', issuedAt: 'now' }, true);

    const localRaw = localStorage.getItem(TOKEN_KEY);
    const sessRaw = sessionStorage.getItem(TOKEN_KEY);

    expect(localRaw).toBeTruthy();
    expect(sessRaw).toBeNull();

    const parsed = JSON.parse(localRaw);
    expect(parsed.token).toBe('persist-456');
    expect(authService.getToken()).toBe('persist-456');

    // clear
    authService.clearToken();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  test('setToken accepts string token and wraps it', () => {
    const { authService } = require('../authService');
    authService.setToken('just-a-string', true);
    expect(localStorage.getItem(TOKEN_KEY)).toBeTruthy();
    expect(authService.getToken()).toBe('just-a-string');
    authService.clearToken();
  });

  test('initializes from storage on module load (localStorage)', () => {
    // Put token in localStorage before requiring module so init reads it
    const sample = { token: 'preload-999', email: 'pre@load', issuedAt: 'now' };
    localStorage.setItem(TOKEN_KEY, JSON.stringify(sample));
    jest.resetModules();
    const { authService } = require('../authService');
    expect(authService.getToken()).toBe('preload-999');
    // cleanup
    authService.clearToken();
  });
});
