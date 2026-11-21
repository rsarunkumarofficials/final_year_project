// Relative by default so the same build works behind any host (FastAPI, nginx,
// Render, etc.). Override with VITE_API_BASE_URL only when the API is separate.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export async function predictUrl(url, sessionId, signal) {
  let response;

  try {
    response = await fetch(`${API_BASE}/api/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url_or_prompt: url, session_id: sessionId }),
      signal,
    });
  } catch (requestError) {
    if (requestError.name === 'AbortError') throw requestError;
    throw new Error('Cannot reach the analysis server. Check your connection and try again.');
  }

  // Parse defensively: a proxy or a crashed worker may return HTML/text.
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message =
      payload?.message ||
      payload?.detail ||
      (response.statusText
        ? `Request failed (${response.status} ${response.statusText}).`
        : `Request failed with status ${response.status}.`);
    throw new Error(message);
  }

  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('The server returned an unreadable response. Please try again.');
  }
  if (payload.status === 'error') {
    throw new Error(payload.message || 'The server reported an error. Please try again.');
  }
  if (!payload.ml || typeof payload.ml !== 'object') {
    throw new Error('The model did not return a verdict. Please try again.');
  }

  return payload;
}

export function normalizeUrl(raw) {
  const value = raw.trim();
  if (!value) return null;

  if (/^[a-z][a-z\d+.-]*:/i.test(value) && !/^https?:\/\//i.test(value)) {
    return null;
  }

  const candidate = /^https?:\/\//i.test(value) ? value : `https://${value}`;
  try {
    const parsed = new URL(candidate);
    return parsed.hostname ? candidate : null;
  } catch {
    return null;
  }
}

export function createSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
