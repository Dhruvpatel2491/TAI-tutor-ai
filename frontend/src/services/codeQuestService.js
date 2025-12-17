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

export async function createSession(
  track,
  {
    description,
    planReference,
    planText,
    difficulty,
    concepts,
    numChallenges,
    useLlmGenerator = true,
    backendURL = DEFAULT_BACKEND_URL,
  } = {}
) {
  const res = await apiPost(`${backendURL}/codequest/sessions`, {
    track,
    description,
    plan_reference: planReference,
    plan_text: planText,
    difficulty,
    concepts,
    num_challenges: numChallenges,
    use_llm_generator: Boolean(useLlmGenerator),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to create session' }));
    throw new Error(err.error || 'Failed to create session');
  }
  return res.json();
}

export async function saveDraft(sessionId, { challengeId, code, backendURL = DEFAULT_BACKEND_URL } = {}) {
  const res = await apiPost(`${backendURL}/codequest/sessions/${encodeURIComponent(sessionId)}/draft`, {
    challenge_id: challengeId,
    code,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to save draft' }));
    throw new Error(err.error || 'Failed to save draft');
  }
  return res.json();
}

export async function navigateSession(
  sessionId,
  { direction, index, challengeId, backendURL = DEFAULT_BACKEND_URL } = {}
) {
  const res = await apiPost(`${backendURL}/codequest/sessions/${encodeURIComponent(sessionId)}/navigate`, {
    direction,
    index,
    challenge_id: challengeId,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to navigate session' }));
    throw new Error(err.error || 'Failed to navigate session');
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

export async function finishSession(sessionId, { backendURL = DEFAULT_BACKEND_URL } = {}) {
  const res = await apiPost(`${backendURL}/codequest/sessions/${encodeURIComponent(sessionId)}/finish`, {});
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to finish quest' }));
    throw new Error(err.error || 'Failed to finish quest');
  }
  return res.json();
}

export async function exitSession(sessionId, { backendURL = DEFAULT_BACKEND_URL } = {}) {
  const res = await apiPost(`${backendURL}/codequest/sessions/${encodeURIComponent(sessionId)}/exit`, {});
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Failed to exit quest' }));
    throw new Error(err.error || 'Failed to exit quest');
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
  finishSession,
  exitSession,
  navigateSession,
  saveDraft,
};

export default codeQuestService;
