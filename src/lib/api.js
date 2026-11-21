export async function predictUrl(url, sessionId, signal) {
  const response = await fetch('/api/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url_or_prompt: url, session_id: sessionId }),
    signal,
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error('The server returned an unreadable response. Please try again.');
  }

  if (!response.ok || payload.status === 'error') {
    throw new Error(payload.message || `Request failed with status ${response.status}.`);
  }
  if (!payload.ml) {
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
