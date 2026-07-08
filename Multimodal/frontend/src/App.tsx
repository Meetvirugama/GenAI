import React, { useState, useRef, useEffect } from 'react';
import styles from './styles/layout.module.css';
import { sendChatMessage, uploadFiles, getMe, getSessions, getSessionMessages, deleteSession } from './api';

type User = { id: number, name: string, email: string };
type SessionData = { id: string, title: string, created_at: string };

const GlobalHeader = ({ user }: { user: User | null }) => (
  <header className={`${styles.header} ${styles.glass}`}>
    <div style={{ fontWeight: 'bold', fontSize: '1.2rem' }}>ScriptAI Enterprise</div>
    <div>{user ? `Welcome, ${user.name || user.email}` : 'Current Session'}</div>
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      {user ? (
        <a href="http://localhost:7860/logout" style={{ color: 'white', textDecoration: 'none', cursor: 'pointer', padding: '0.5rem 1rem', background: 'rgba(255,0,0,0.2)', borderRadius: '4px' }}>Logout</a>
      ) : (
        <a href="http://localhost:7860/login/google" style={{ color: 'white', textDecoration: 'none', cursor: 'pointer', padding: '0.5rem 1rem', background: 'rgba(59, 130, 246, 0.8)', borderRadius: '4px' }}>Login with Google</a>
      )}
    </div>
  </header>
);

const Sidebar = ({ sessions, onSelectSession, onNewChat, onDeleteSession }: { sessions: SessionData[], onSelectSession: (id: string) => void, onNewChat: () => void, onDeleteSession: (id: string) => void }) => (
  <nav className={`${styles.sidebar} ${styles.glass}`}>
    <ul style={{ listStyle: 'none', padding: 0 }}>
      <li onClick={onNewChat} style={{ padding: '1rem', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.1)', fontWeight: 'bold', background: 'rgba(59, 130, 246, 0.2)' }}>+ New Chat</li>
      {sessions.map(s => (
        <li key={s.id} style={{ padding: '1rem', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between' }}>
          <span onClick={() => onSelectSession(s.id)} style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.title}</span>
          <span onClick={() => onDeleteSession(s.id)} style={{ color: '#ef4444', marginLeft: '10px' }}>×</span>
        </li>
      ))}
    </ul>
  </nav>
);

// Define chat message type
type Message = {
  role: 'user' | 'assistant';
  content: string;
};

const App = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => 'sess_' + Math.random().toString(36).substring(7));
  const [sources, setSources] = useState<string[]>([]);
  const [lastImagePath, setLastImagePath] = useState<string | undefined>(undefined);
  const [user, setUser] = useState<User | null>(null);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Check if logged in
    getMe().then(u => {
      setUser(u);
      if (u) {
        refreshSessions();
      }
    }).catch(console.error);
  }, []);

  const refreshSessions = async () => {
    try {
      const sess = await getSessions();
      setSessions(sess);
    } catch (e) { console.error(e); }
  };

  const handleNewChat = () => {
    setSessionId('sess_' + Math.random().toString(36).substring(7));
    setMessages([]);
    setSources([]);
    setLastImagePath(undefined);
  };

  const handleSelectSession = async (id: string) => {
    try {
      setIsLoading(true);
      const msgs = await getSessionMessages(id);
      setSessionId(id);
      setMessages(msgs.map((m: any) => ({ role: m.role, content: m.content })));
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      if (sessionId === id) handleNewChat();
      refreshSessions();
    } catch (e) { console.error(e); }
  };

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      // Build history payload for the API
      const history = [];
      for (let i = 0; i < messages.length; i+=2) {
        if (messages[i].role === 'user' && messages[i+1]?.role === 'assistant') {
          history.push({ user: messages[i].content, assistant: messages[i+1].content });
        }
      }

      const response = await sendChatMessage(userMsg, sessionId, history, lastImagePath);
      setMessages(prev => [...prev, { role: 'assistant', content: response.answer }]);
      if (user) refreshSessions();
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error connecting to the server." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    
    const files = Array.from(e.target.files);
    setIsLoading(true);
    try {
      const res = await uploadFiles(e.target.files, sessionId);
      setSources(prev => [...prev, ...files.map(f => f.name)]);
      
      const uploadedImageFiles = res.files?.filter((f: string) => f.match(/\.(png|jpe?g)$/i)) || [];
      if (uploadedImageFiles.length > 0) {
        setLastImagePath(uploadedImageFiles[uploadedImageFiles.length - 1]);
      }

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Successfully uploaded and processed ${res.pdfs_processed} PDFs and ${res.images_processed} images.` 
      }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'assistant', content: "Error uploading files." }]);
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className={styles.appContainer}>
      <GlobalHeader user={user} />
      <Sidebar sessions={sessions} onSelectSession={handleSelectSession} onNewChat={handleNewChat} onDeleteSession={handleDeleteSession} />
      
      <main className={styles.chatArea}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', opacity: 0.5, marginTop: '20vh' }}>
            <h2>Welcome to ScriptAI Enterprise</h2>
            <p>Upload a document or ask a question to begin.</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div 
              key={idx} 
              style={{ 
                padding: '1.5rem', 
                background: msg.role === 'user' ? 'rgba(255,255,255,0.05)' : 'rgba(59, 130, 246, 0.1)', 
                borderRadius: '8px', 
                marginBottom: '1rem',
                borderLeft: msg.role === 'assistant' ? '4px solid #3b82f6' : 'none',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                animation: 'fadeIn 0.3s ease-in-out'
              }}
            >
              <strong style={{ color: msg.role === 'assistant' ? '#60a5fa' : 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                {msg.role === 'user' ? '👤 You' : '🤖 ScriptAI'}
              </strong>
              <div style={{ marginTop: '0.8rem', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{msg.content}</div>
            </div>
          ))
        )}
        {isLoading && (
          <div style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '8px', opacity: 0.8 }}>
            <div className={styles.spinner} style={{ width: '16px', height: '16px', border: '2px solid #3b82f6', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            ScriptAI is thinking...
          </div>
        )}
        <div ref={chatEndRef} />
      </main>

      <aside className={`${styles.rightPanel} ${styles.glass}`}>
        <h3 style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>Knowledge Base</h3>
        {sources.length === 0 ? (
          <p style={{ opacity: 0.5, fontSize: '0.9rem' }}>No documents uploaded for this session.</p>
        ) : (
          sources.map((src, i) => (
            <div key={i} style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
              📄 {src}
            </div>
          ))
        )}
      </aside>

      <div className={`${styles.contextChips} ${styles.glass}`}>
        <span style={{ opacity: 0.7, fontSize: '0.8rem', marginRight: '1rem' }}>Active Context:</span>
        {sources.slice(0, 3).map((src, i) => (
          <span key={i} style={{ padding: '0.3rem 0.8rem', background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', borderRadius: '16px', fontSize: '0.8rem' }}>
            {src}
          </span>
        ))}
        {sources.length > 3 && (
          <span style={{ fontSize: '0.8rem', opacity: 0.5 }}>+{sources.length - 3} more</span>
        )}
      </div>

      <div className={`${styles.promptBar} ${styles.glass}`}>
        <div style={{ display: 'flex', width: '100%', gap: '1rem', alignItems: 'center' }}>
          <input 
            type="file" 
            multiple 
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileUpload}
            accept=".pdf,.png,.jpg,.jpeg"
          />
          <button 
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            style={{ padding: '1rem', background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer' }}
          >
            📎 Upload
          </button>
          
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask anything..." 
            disabled={isLoading}
            style={{ flex: 1, padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(0,0,0,0.5)', color: 'white' }}
          />
          
          <button 
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            style={{ padding: '1rem 2rem', background: '#3b82f6', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default App;
