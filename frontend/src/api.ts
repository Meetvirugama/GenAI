const API_BASE = 'http://localhost:7860/api';

export const sendChatMessage = async (
  message: string, 
  sessionId: string, 
  history: Array<{user: string, assistant: string}> = [],
  imagePath?: string
) => {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      message,
      session_id: sessionId,
      history,
      image_path: imagePath
    }),
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }

  return response.json();
};

export const uploadFiles = async (files: FileList | File[], sessionId: string) => {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }
  formData.append('session_id', sessionId);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload Error: ${response.statusText}`);
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
  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }
  return response.json();
};

export const getSessionMessages = async (sessionId: string) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }
  return response.json();
};

export const deleteSession = async (sessionId: string) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`, { 
    method: 'DELETE',
    credentials: 'include' 
  });
  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }
  return response.json();
};

export const sendFeedback = async (messageId: number, feedback: number) => {
  const response = await fetch(`${API_BASE}/messages/${messageId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ feedback })
  });
  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }
  return response.json();
};
