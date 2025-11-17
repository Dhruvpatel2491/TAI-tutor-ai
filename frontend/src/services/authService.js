// Lightweight auth service for demo purposes.
// Security note: This is for local demo only. Storing credentials in localStorage
// is NOT secure for production. The Web Crypto operations here reduce plain-text
// exposure but don't replace a secure backend with proper authentication.

const USERS_KEY = 'tutor_users_v1';
const SESSION_KEY = 'tutor_session_v1';

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
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
}

function saveUsers(users) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

function saveSession(token, remember) {
  if (remember) localStorage.setItem(SESSION_KEY, JSON.stringify(token));
  else sessionStorage.setItem(SESSION_KEY, JSON.stringify(token));
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(SESSION_KEY);
}

function getSession() {
  const s = sessionStorage.getItem(SESSION_KEY) || localStorage.getItem(SESSION_KEY);
  return s ? JSON.parse(s) : null;
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
  async registerOrLogin(email, password, remember = false) {
    const users = loadUsers();
    const now = new Date().toISOString();
    const lower = email.trim().toLowerCase();

    if (!users[lower]) {
      // register
      const salt = makeSalt();
      const passwordHash = await derivePasswordHash(password, salt);
      users[lower] = { email: lower, salt, passwordHash, createdAt: now };
      saveUsers(users);
    }

    // verify
    const user = users[lower];
    const derived = await derivePasswordHash(password, user.salt);
    if (derived !== user.passwordHash) {
      throw new Error('Invalid credentials');
    }

    const token = { token: uuidv4(), email: lower, issuedAt: now };
    saveSession(token, remember);
    return token;
  },

  logout() {
    clearSession();
  },

  getCurrentUser() {
    const session = getSession();
    if (!session) return null;
    const users = loadUsers();
    const u = users[session.email];
    return u ? { email: u.email, createdAt: u.createdAt } : null;
  },

  getSessionToken() {
    return getSession();
  },

  // Expose derive for tests
  derivePasswordHash,
  _internal: { loadUsers, saveUsers }
};

export default authService;
