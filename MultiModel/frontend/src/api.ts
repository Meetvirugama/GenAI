const API_BASE = 'http://localhost:7860/api';

export const sendChatMessage = async (
  message: string,
  sessionId: string,
  history: Array<{user: string, assistant: string}> = [],
  imagePath?: string
) => {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ message, session_id: sessionId, history, image_path: imagePath }),
  });
  if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
  return response.json();
};

// #13 Streaming: reads an SSE stream and calls callbacks for each event
export type StreamCallbacks = {
  onToken: (token: string) => void;
  onDone: (meta: { message_id: number | null; confidence: { level: string; label: string } }) => void;
  onError: (err: string) => void;
};

export const sendChatStream = async (
  message: string,
  sessionId: string,
  history: Array<{user: string, assistant: string}> = [],
  imagePath?: string,
  callbacks?: StreamCallbacks
): Promise<void> => {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ message, session_id: sessionId, history, image_path: imagePath }),
  });

  if (!response.ok) throw new Error(`Stream API Error: ${response.statusText}`);
  if (!response.body) throw new Error('No response body');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = line.slice(6).trim();
      if (data === '[DONE]') return;
      try {
        const parsed = JSON.parse(data);
        if (parsed.token !== undefined) callbacks?.onToken(parsed.token);
        else if (parsed.done) callbacks?.onDone({ message_id: parsed.message_id, confidence: parsed.confidence });
        else if (parsed.error) callbacks?.onError(parsed.error);
      } catch {}
    }
  }
};

export const uploadFiles = async (files: FileList | File[], sessionId: string) => {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) formData.append('files', files[i]);
  formData.append('session_id', sessionId);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || `Upload Error: ${response.statusText}`);
  }
  return response.json();
};

export const getMe = async () => {
  const response = await fetch(`${API_BASE}/me`, { credentials: 'include' });
  if (!response.ok) {
    if (response.status === 401) return null;
    throw new Error(`API Error: ${response.statusText}`);
  }
  return response.json();
};

export const getSessions = async () => {
  const response = await fetch(`${API_BASE}/sessions`, { credentials: 'include' });
  if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
  return response.json();
};

export const getSessionMessages = async (sessionId: string) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, { credentials: 'include' });
  if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
  return response.json();
};

export const deleteSession = async (sessionId: string) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'DELETE',
    credentials: 'include'
  });
  if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
  return response.json();
};

export const sendFeedback = async (messageId: number, feedback: number) => {
  const response = await fetch(`${API_BASE}/messages/${messageId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ feedback })
  });
  if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
  return response.json();
};

export const searchMessages = async (q: string) => {
  const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(q)}`, {
    credentials: 'include'
  });
  if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
  return response.json();
};
