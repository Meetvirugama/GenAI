import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import styles from './styles/layout.module.css';
import { sendChatMessage, uploadFiles, getMe, getSessions, getSessionMessages, deleteSession } from './api';

type User = { id: number, name: string, email: string };
type SessionData = { id: string, title: string, created_at: string };
type Message = { id?: number; role: 'user' | 'assistant'; content: string; feedback?: number; trace?: string; };

// --- SVGs ---
const PaperclipIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
);
const ChevronDownIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
);
const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
);
const LogoIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2c-.65 2-.8 3.5-1 4.5C9 7 7 9 7 13c0 4.5 2.5 8 5 8s5-3.5 5-8c0-4-2-6-4-6.5-.2-1-.35-2.5-1-4.5" />
    <path d="M12 2s3-1 4 2" />
  </svg>
);

// --- Components ---
const Sidebar = ({ sessions, activeSessionId, sources, onSelectSession, onNewChat }: { sessions: SessionData[], activeSessionId: string, sources: string[], onSelectSession: (id: string) => void, onNewChat: () => void }) => {
  const [isSourcesExpanded, setIsSourcesExpanded] = React.useState(false);

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logoArea}>
        <div style={{ color: '#2563eb', display: 'flex' }}><LogoIcon /></div>
        <span>NexusIQ</span>
      </div>
      
      <button className={styles.newChatBtn} onClick={onNewChat}>
        + New Chat
      </button>
      
      <div style={{ flex: 1, overflowY: 'auto', marginTop: '1rem' }}>
        {sessions.length > 0 && (
          <>
            <div className={styles.historyGroupTitle}>Recent</div>
            {sessions.map(s => (
              <div 
                key={s.id} 
                className={`${styles.historyItem} ${s.id === activeSessionId ? styles.active : ''}`}
                onClick={() => onSelectSession(s.id)}
              >
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.title}</span>
                {s.id === activeSessionId && <span style={{ width: 8, height: 8, background: '#2563eb', borderRadius: '50%' }} />}
              </div>
            ))}
          </>
        )}
      </div>

      <div 
        className={styles.sourcesCard} 
        style={{ cursor: 'pointer', flexDirection: 'column', alignItems: 'stretch' }}
        onClick={() => setIsSourcesExpanded(!isSourcesExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Sources</span>
            <span className={styles.sourcesBadge}>{sources.length}</span>
          </div>
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            width="16" height="16" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="#9ca3af" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
            style={{ transform: isSourcesExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }}
          >
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>
        
        {isSourcesExpanded && sources.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '12px' }}>
            {sources.map((src, i) => (
              <div key={i} style={{ fontSize: '0.75rem', color: '#6b7280', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', background: '#f3f4f6', padding: '4px 8px', borderRadius: '4px' }}>
                {src}
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
};


const App = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => 'sess_' + Math.random().toString(36).substring(7));
  const [sources, setSources] = useState<string[]>([]);
  const [lastImagePath, setLastImagePath] = useState<string | undefined>(undefined);
  const [user, setUser] = useState<User | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [isTitleMenuOpen, setIsTitleMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getMe().then(u => {
      setUser(u);
      if (u) refreshSessions();
    }).catch(console.error).finally(() => setIsAuthLoading(false));
  }, []);

  const refreshSessions = async () => {
    try {
      const res = await getSessions();
      setSessions(res);
      // Auto-load most recent session if available and we haven't loaded one yet
      if (res.length > 0 && messages.length === 0) {
        handleSelectSession(res[0].id);
      }
    } catch (error) {
      console.error(error);
    }
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
      const res = await getSessionMessages(id);
      setSessionId(id);
      
      if (Array.isArray(res)) {
        setMessages(res.map((m: any) => ({ id: m.id, role: m.role, content: m.content, feedback: m.feedback, trace: m.trace })));
      } else {
        setMessages(res.messages.map((m: any) => ({ id: m.id, role: m.role, content: m.content, feedback: m.feedback, trace: m.trace })));
        setSources(res.files || []);
        setLastImagePath(res.lastImagePath || undefined);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

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
      const history = [];
      for (let i = 0; i < messages.length; i+=2) {
        if (messages[i].role === 'user' && messages[i+1]?.role === 'assistant') {
          history.push({ user: messages[i].content, assistant: messages[i+1].content });
        }
      }

      const response = await sendChatMessage(userMsg, sessionId, history, lastImagePath);
      setMessages(prev => [...prev, { role: 'assistant', content: response.answer, id: response.message_id, trace: response.trace }]);
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
        content: `Successfully uploaded and processed ${res.pdfs_processed} PDFs, ${res.mds_processed || 0} Markdown files, and ${res.images_processed} images.` 
      }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'assistant', content: "Error uploading files." }]);
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };


  const handleDeleteSession = async () => {
    try {
      await deleteSession(sessionId);
      setIsTitleMenuOpen(false);
      refreshSessions();
      handleNewChat();
    } catch (e) {
      console.error(e);
      alert('Failed to delete session');
    }
  };

  const handleLogout = () => {
    window.location.href = 'http://localhost:7860/logout';
  };

  const activeSessionTitle = sessions.find(s => s.id === sessionId)?.title || "New Chat";

  if (isAuthLoading) {
    return <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: '#fafafa', color: '#6b7280' }}>Loading...</div>;
  }

  if (!user) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: '#f9fafb' }}>
        <div style={{ background: 'white', padding: '40px', borderRadius: '12px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', textAlign: 'center' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px', color: '#2563eb' }}><LogoIcon /></div>
          <h1 style={{ margin: '0 0 8px 0', fontSize: '1.5rem', color: '#111827' }}>Welcome to NexusIQ</h1>
          <p style={{ color: '#6b7280', margin: '0 0 24px 0' }}>Please sign in to continue.</p>
          <a href="http://localhost:7860/login/google" style={{ display: 'inline-block', background: '#2563eb', color: 'white', padding: '10px 24px', borderRadius: '8px', textDecoration: 'none', fontWeight: 500, transition: 'background 0.2s' }}>
            Login with Google
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.appContainer}>
      <Sidebar 
        sessions={sessions} 
        activeSessionId={sessionId} 
        sources={sources}
        onSelectSession={handleSelectSession} 
        onNewChat={handleNewChat} 
      />
      
      <main className={styles.mainContent}>
        <header className={styles.mainHeader}>
          <div style={{ position: 'relative' }}>
            <div 
              style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: '#111827', cursor: 'pointer', padding: '6px 10px', borderRadius: '6px', marginLeft: '-10px' }}
              onClick={() => setIsTitleMenuOpen(!isTitleMenuOpen)}
              className={styles.headerDropdownBtn}
            >
              {activeSessionTitle}
              <ChevronDownIcon />
            </div>
            {isTitleMenuOpen && (
              <div style={{ position: 'absolute', top: '100%', left: 0, marginTop: '4px', background: 'white', border: '1px solid #e5e7eb', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', zIndex: 10, minWidth: '150px', padding: '4px' }}>
                <div style={{ padding: '8px 12px', fontSize: '0.875rem', cursor: 'pointer', color: '#ef4444', borderRadius: '4px' }} onClick={handleDeleteSession} className={styles.dropdownItem}>
                  Delete Chat
                </div>
              </div>
            )}
          </div>
          
          <div style={{ position: 'relative' }}>
            <div 
              style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', fontWeight: 500, color: '#111827', cursor: 'pointer', padding: '4px 8px', borderRadius: '6px' }}
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className={styles.headerDropdownBtn}
            >
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#2563eb', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {user ? (user.name ? user.name.substring(0,2).toUpperCase() : 'U') : 'MP'}
              </div>
              {user ? (user.name || user.email) : 'Meet Patel'}
              <ChevronDownIcon />
            </div>
            {isUserMenuOpen && (
              <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: '4px', background: 'white', border: '1px solid #e5e7eb', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', zIndex: 10, minWidth: '150px', padding: '4px' }}>
                <div style={{ padding: '8px 12px', fontSize: '0.875rem', cursor: 'pointer', color: '#374151', borderRadius: '4px' }} onClick={handleLogout} className={styles.dropdownItem}>
                  Log out
                </div>
              </div>
            )}
          </div>
        </header>

        <div className={styles.chatArea}>
          {messages.length === 0 ? (
            <div style={{ textAlign: 'center', opacity: 0.5, marginTop: '20vh' }}>
              <LogoIcon />
              <h2>How can I help you today?</h2>
            </div>
          ) : (
            messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              return (
                <div key={idx} className={styles.messageContainer}>
                  <div className={styles.messageAvatar} style={{ background: isUser ? '#2563eb' : '#eff6ff' }}>
                    {isUser ? 'MP' : <LogoIcon />}
                  </div>
                  <div className={styles.messageContent} style={{ borderColor: isUser ? 'transparent' : '#e5e7eb' }}>
                    <div className={styles.messageHeader}>
                      <span className={styles.messageName}>{isUser ? 'You' : 'NexusIQ'}</span>
                      <span className={styles.messageTime}>{new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                    <div style={{ lineHeight: '1.6', color: '#374151', overflowX: 'auto' }}>
                      {isUser ? (
                        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                      ) : (
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      )}
                    </div>

                    {!isUser && msg.trace && (
                      <details style={{ marginTop: '12px', padding: '12px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '0.8rem', color: '#4b5563' }}>
                        <summary style={{ cursor: 'pointer', fontWeight: 600, userSelect: 'none', color: '#2563eb' }}>
                          View Reasoning Trace
                        </summary>
                        <div style={{ marginTop: '12px', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                          <ReactMarkdown>{msg.trace}</ReactMarkdown>
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              );
            })
          )}
          {isLoading && (
            <div style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '8px', color: '#6b7280' }}>
              <div style={{ width: '16px', height: '16px', border: '2px solid #2563eb', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              NexusIQ is thinking...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className={styles.promptBarContainer}>
          <div className={styles.promptBar}>
            <div className={styles.promptInputRow}>
              <div style={{ display: 'flex', gap: '8px', paddingLeft: '8px' }}>
                <button className={styles.iconButton} onClick={() => fileInputRef.current?.click()} disabled={isLoading}>
                  <PaperclipIcon />
                </button>
              </div>
              
              <input 
                type="file" 
                multiple 
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleFileUpload}
                accept=".pdf,.md,.png,.jpg,.jpeg"
              />
              
              <input 
                type="text" 
                className={styles.promptInput}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask anything..." 
                disabled={isLoading}
              />
              
              <div style={{ paddingRight: '8px' }}>
                <button 
                  className={styles.sendButton}
                  onClick={handleSend}
                  disabled={isLoading || !input.trim()}
                >
                  <SendIcon />
                </button>
              </div>
            </div>
            
            <div className={styles.pillsRow}>
              <span className={styles.pill} onClick={() => setInput(prev => prev + "/docs ")}>/docs</span>
              <span className={styles.pill} onClick={() => setInput(prev => prev + "/web ")}>/web</span>
              <span className={styles.pill} onClick={() => setInput(prev => prev + "/image ")}>/image</span>
              <span className={styles.pill} onClick={() => setInput(prev => prev + "/code ")}>/code</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
