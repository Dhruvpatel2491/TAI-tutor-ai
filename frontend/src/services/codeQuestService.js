/**
 * CodeQuest Service
 *
 * API calls for CodeQuest (tracks, challenges, sessions, submissions).
 */

import { apiGet, apiPost } from './http';
import { DEFAULT_BACKEND_URL } from '../config';

export async function listTracks({ backendURL = DEFAULT_BACKEND_URL } = {}) {
  const res = await apiGet(`${backendURL}/codequest/tracks`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to list tracks' }));
    throw new Error(err.error || 'Failed to list tracks');
  }
  return res.json();
}

export async function listChallenges(track, { backendURL = DEFAULT_BACKEND_URL } = {}) {
  const params = new URLSearchParams({ track: String(track || '') });
  const res = await apiGet(`${backendURL}/codequest/challenges?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to list challenges' }));
    throw new Error(err.error || 'Failed to list challenges');
  }
  return res.json();
}

export async function createSession(track, { backendURL = DEFAULT_BACKEND_URL } = {}) {
  const res = await apiPost(`${backendURL}/codequest/sessions`, { track });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to create session' }));
    throw new Error(err.error || 'Failed to create session');
  }
  return res.json();
}

export async function listSessions({ backendURL = DEFAULT_BACKEND_URL } = {}) {
  const res = await apiGet(`${backendURL}/codequest/sessions`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to list sessions' }));
    throw new Error(err.error || 'Failed to list sessions');
  }
  return res.json();
}

export async function getSession(sessionId, { backendURL = DEFAULT_BACKEND_URL } = {}) {
  const res = await apiGet(`${backendURL}/codequest/sessions/${sessionId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to get session' }));
    throw new Error(err.error || 'Failed to get session');
  }
  return res.json();
}

export async function submitSolution(sessionId, { challengeId, code, backendURL = DEFAULT_BACKEND_URL } = {}) {
  const res = await apiPost(`${backendURL}/codequest/sessions/${sessionId}/submit`, {
    challenge_id: challengeId,
    code,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to submit solution' }));
    throw new Error(err.error || 'Failed to submit solution');
  }
  return res.json();
}

const codeQuestService = {
  listTracks,
  listChallenges,
  createSession,
  listSessions,
  getSession,
  submitSolution,
};

export default codeQuestService;
