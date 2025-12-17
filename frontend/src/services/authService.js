// Lightweight auth service for demo purposes.
// Security note: This is for local demo only. Storing credentials in localStorage
// is NOT secure for production. The Web Crypto operations here reduce plain-text
// exposure but don't replace a secure backend with proper authentication.

const USERS_KEY = 'tutor_users_v1';
const TOKEN_KEY = 'tutor_token_v1';
// NOTE: tokens/sessions are now managed in-memory by this service to avoid
// storing auth sessions in localStorage/sessionStorage. Components should use
// authService.getToken()/setToken()/clearToken() to interact with the session.

let _currentSession = null;
let _userSession = null;

// Initialize session from sessionStorage (prefer) then localStorage
function _initSessionFromStorage() {
  try {
    const sessRaw = sessionStorage.getItem(TOKEN_KEY);
    const userRaw = sessionStorage.getItem(USERS_KEY);
    if (sessRaw) {
      _currentSession = JSON.parse(sessRaw);
      _userSession=JSON.parse(userRaw);
      return;
    }
  } catch (e) { console.error('Error initializing session from storage:', e); }

  try {
    const localRaw = localStorage.getItem(TOKEN_KEY);
    const localUserRaw = localStorage.getItem(USERS_KEY);
    if (localRaw) {
      _currentSession = JSON.parse(localRaw);
      _userSession = JSON.parse(localUserRaw);
      return;
    }
  } catch (e) { /* ignore */ }
}

_initSessionFromStorage();

function b64encode(buf) {
  return btoa(String.fromCharCode(...new Uint8Array(buf)));
}

function b64decode(str) {
  const bin = atob(str);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr.buffer;
}

async function derivePasswordHash(password, saltBase64) {
  // PBKDF2 with SHA-256
  // Use Web Crypto if available (browser). In Node test env, fall back to crypto.pbkdf2Sync.
  // Determine TextEncoder implementation without causing bundlers to include Node polyfills.
  let TextEncoderImpl = (typeof TextEncoder !== 'undefined') ? TextEncoder : undefined;
  if (!TextEncoderImpl) {
    try {
      // Use eval to avoid static require resolution by webpack in the browser build.
      // In Node test environments this will load util.TextEncoder.
      // eslint-disable-next-line no-eval
      const util = eval("require")('util');
      TextEncoderImpl = util && util.TextEncoder;
    } catch (e) {
      TextEncoderImpl = undefined;
    }
  }
  if (!TextEncoderImpl) throw new Error('TextEncoder not available in this environment');
  const enc = new TextEncoderImpl();
  const salt = b64decode(saltBase64);

  const webcrypto = (typeof window !== 'undefined' && window.crypto) ? window.crypto : (typeof global !== 'undefined' && global.crypto ? global.crypto : null);
  if (webcrypto && webcrypto.subtle) {
    const keyMaterial = await webcrypto.subtle.importKey(
      'raw',
      enc.encode(password),
      { name: 'PBKDF2' },
      false,
      ['deriveBits', 'deriveKey']
    );
    const derived = await webcrypto.subtle.deriveBits(
      { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
      keyMaterial,
      256
    );
    return b64encode(derived);
  }

  // Node fallback using dynamic require to avoid bundler polyfills in the browser build
  try {
    // eslint-disable-next-line no-eval
    const nodeCrypto = eval("require")('crypto');
    const derived = nodeCrypto.pbkdf2Sync(password, new Uint8Array(salt), 100000, 32, 'sha256');
    return b64encode(derived.buffer);
  } catch (e) {
    throw new Error('No suitable crypto available');
  }
}

function makeSalt() {
  const arr = window.crypto.getRandomValues(new Uint8Array(16));
  return b64encode(arr.buffer);
}

function loadUsers() {
  try {
    const raw = localStorage.getItem(USERS_KEY);
    _userSession = raw ? JSON.parse(raw) : {};
    return _userSession;
  } catch (e) {
    return {};
  }
}

function saveUsers(users) {
  try { localStorage.setItem(USERS_KEY, JSON.stringify(users)); } catch (e) { /* ignore */ }
}

function saveSession(token, remember = true) {
  // persist to storage based on remember flag and also keep in-memory
  _currentSession = token || null;
  try {
    if (!token) {
      sessionStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(TOKEN_KEY);
      return;
    }
    const raw = JSON.stringify(token);
    if (remember) {
      // persistent across browser restarts
      localStorage.setItem(TOKEN_KEY, raw);
      // ensure sessionStorage doesn't hold a stale copy
      try { sessionStorage.removeItem(TOKEN_KEY); } catch (e) {}
    } else {
      // session-only
      sessionStorage.setItem(TOKEN_KEY, raw);
      try { localStorage.removeItem(TOKEN_KEY); } catch (e) {}
    }
  } catch (e) {
    // storage might be unavailable (privacy mode) — fall back to in-memory
  }
}

function clearSession() {
  _currentSession = null;
  try { sessionStorage.removeItem(TOKEN_KEY); } catch (e) {}
  try { localStorage.removeItem(TOKEN_KEY); } catch (e) {}

  _userSession = null;
  try { sessionStorage.removeItem(USERS_KEY); } catch (e) {}
  try { localStorage.removeItem(USERS_KEY); } catch (e) {}
}

function getSession() {
  return _currentSession;
}

function uuidv4() {
  // small UUID v4 generator using crypto.getRandomValues
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  // Per RFC4122 v4: set version and clockseq
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const toHex = (b) => b.toString(16).padStart(2, '0');
  let i = 0;
  return `${toHex(bytes[i++])}${toHex(bytes[i++])}${toHex(bytes[i++])}${toHex(bytes[i++])}-${toHex(bytes[i++])}${toHex(bytes[i++])}-${toHex(bytes[i++])}${toHex(bytes[i++])}-${toHex(bytes[i++])}${toHex(bytes[i++])}-${toHex(bytes[i++])}${toHex(bytes[i++])}${toHex(bytes[i++])}${toHex(bytes[i++])}${toHex(bytes[i++])}${toHex(bytes[i++])}`;
}

export const authService = {
  async register(email, password, name = '', remember = false) {
    // Try backend register first (if backend URL configured). If backend not
    // available, fall back to local demo storage behavior.
    const base = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/$/, '') || '';
    const payload = { email: email.trim().toLowerCase(), password, name: name.trim() };
    if (base) {
      try {
        const res = await fetch(`${base}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          const token = data.token;
          saveSession(token, remember);
          try { window.dispatchEvent(new CustomEvent('auth_token_changed', { detail: { token } })); } catch (e) {}
          return token;
        }
        throw new Error(data.error || 'Register failed');
      } catch (err) {
        // fallthrough to local fallback below
        console.warn('Backend register failed, falling back to local demo store:', err);
      }
    }

    // Local fallback registration (existing behavior)
    const users = loadUsers();
    const now = new Date().toISOString();
    const lower = email.trim().toLowerCase();
    if (!users[lower]) {
      const salt = makeSalt();
      const passwordHash = await derivePasswordHash(password, salt);
      users[lower] = { name: name.trim(), email: lower, salt, passwordHash, createdAt: now };
      saveUsers(users);
    } else {
      throw new Error('User already exists (local)');
    }
    const token = { token: uuidv4(), email: lower, issuedAt: now };
    saveSession(token, remember);
    try { window.dispatchEvent(new CustomEvent('auth_token_changed', { detail: { token } })); } catch (e) {}
    return token;
  },

  async login(email, password, remember = false) {
    const base = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/$/, '') || '';
    const payload = { email: email.trim().toLowerCase(), password };
    if (base) {
      try {
        const res = await fetch(`${base}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          const token = data.token;
          saveSession(token, remember);
          try { window.dispatchEvent(new CustomEvent('auth_token_changed', { detail: { token } })); } catch (e) {}
          return token;
        }
        throw new Error(data.error || 'Login failed');
      } catch (err) {
        console.warn('Backend login failed, falling back to local demo store:', err);
      }
    }

    // Local fallback login (existing behavior)
    const users = loadUsers();
    const lower = email.trim().toLowerCase();
    const user = users[lower];
    if (!user) throw new Error('Unknown user');
    const derived = await derivePasswordHash(password, user.salt);
    if (derived !== user.passwordHash) throw new Error('Invalid credentials');
    const now = new Date().toISOString();
    const token = { token: uuidv4(), email: lower, issuedAt: now };
    saveSession(token, remember);
    try { window.dispatchEvent(new CustomEvent('auth_token_changed', { detail: { token } })); } catch (e) {}
    return token;
  },

  logout() {
    // ensure listeners are notified
    authService.clearToken();
  },

  getCurrentUser() {
    const session = getSession();
    if (!session) return null;
    const users = loadUsers();
    // console.log('authService.getCurrentUser: users[session.email]', Object.values(users)[0]);
    const u = Object.values(users)[0];
    // console.table('authService.getCurrentUser: u', u);
    return u ? { email: u.email, createdAt: u.createdAt , name: u?.name } : null;
  },

  getSessionToken() {
    return getSession();
  },

  // Compatibility helpers so components that used `auth` can be switched to
  // `authService` without changing call sites everywhere.
  // getToken: return a simple token string when possible (for legacy checks)
  getToken() {
    const s = getSession();
    if (!s) return null;
    if (typeof s === 'string') return s;
    if (s && s.token) return s.token;
    return s;
  },

  // setToken: accept either a token string or a token object and persist it
  setToken(token, remember = true) {
    try {
      if (!token) {
        clearSession();
        try { window.dispatchEvent(new CustomEvent('auth_token_changed', { detail: { token: null } })); } catch (e) {}
        return;
      }
      // if token is a string, wrap it
      const toSave = (typeof token === 'string') ? { token } : token;
      saveSession(toSave, remember);
      try { window.dispatchEvent(new CustomEvent('auth_token_changed', { detail: { token: toSave } })); } catch (e) {}
    } catch (e) {
      // ignore
    }
  },

  clearToken() {
    clearSession();
    try { window.dispatchEvent(new CustomEvent('auth_token_changed', { detail: { token: null } })); } catch (e) {}
  },

  // decodeToken: attempt to decode a JWT-like token, but also accept the
  // session object produced by this demo (returns that object if present).
  decodeToken(token) {
    try {
      if (!token) return null;
      // if a session object was passed, try to return it
      if (typeof token === 'object') return token;
      // otherwise try JWT decode
      const parts = token.split('.');
      if (parts.length < 2) return null;
      const payload = parts[1];
      const padded = payload + '='.repeat((-payload.length) % 4);
      const json = JSON.parse(atob(padded.replace(/-/g, '+').replace(/_/g, '/')));
      return json;
    } catch (e) {
      return null;
    }
  },

  // fetchCurrentUser: for the local/demo authService return the local user
  async fetchCurrentUser() {
    try {
      // For privacy and to remove email-as-user-id flows, do not expose
      // user_id here. Return minimal profile information if available.
      const u = authService.getCurrentUser();
      //console.log('authService.fetchCurrentUser: u', u);
      if (!u) return null;
      return u || {};
    } catch (e) {
      return null;
    }
  },

  onAuthChange(cb) {
    const handler = (e) => cb(e.detail && e.detail.token ? e.detail.token : null);
    window.addEventListener('auth_token_changed', handler);
    return () => window.removeEventListener('auth_token_changed', handler);
  },

  // Get user statistics from backend
  async getUserStats() {
    const base = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/$/, '') || '';
    if (!base) {
      throw new Error('Backend URL not configured');
    }
    
    const token = authService.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      const res = await fetch(`${base}/auth/user/stats`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to fetch user stats');
      }
      let response = await res.json();
      return response;
    } catch (err) {
      console.error('Error fetching user stats:', err);
      throw err;
    }
  },

  // Expose derive for tests
  derivePasswordHash,
  _internal: { loadUsers, saveUsers }
};

export default authService;
