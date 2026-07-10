import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import styles from './styles/layout.module.css';
import { sendChatStream, uploadFiles, getMe, getSessions, getSessionMessages, deleteSession, sendFeedback, searchMessages } from './api';

type User = { id: number, name: string, email: string };
type SessionData = { id: string, title: string, created_at: string };
type Confidence = { level: 'high' | 'medium' | 'low'; label: string };
type Message = { id?: number; role: 'user' | 'assistant'; content: string; feedback?: number; trace?: string; timestamp?: string; confidence?: Confidence; };

// --- Helpers ---
function getUserInitials(user: User | null): string {
  if (!user) return '?';
  if (user.name) {
    const parts = user.name.trim().split(' ');
    return parts.length >= 2
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : user.name.substring(0, 2).toUpperCase();
  }
  return user.email.substring(0, 2).toUpperCase();
}

function formatTime(timestamp?: string): string {
  if (!timestamp) return '';
  try { return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
  catch { return ''; }
}

function generateSessionId(): string {
  return 'sess_' + crypto.randomUUID().replace(/-/g, '').substring(0, 16);
}

// --- Custom Markdown Components ---
const CopyButton = ({ text }: { text: string }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} style={{
      position: 'absolute', top: '10px', right: '10px',
      background: copied ? 'rgba(139,92,246,0.7)' : 'rgba(255,255,255,0.12)',
      border: 'none', borderRadius: '6px', color: '#e2e8f0',
      fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer',
      padding: '4px 10px', transition: 'all 0.2s', backdropFilter: 'blur(4px)'
    }}>
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  );
};

// --- Mermaid Diagram Block ---
const MermaidBlock = ({ chart }: { chart: string }) => {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let cancelled = false;
    import('mermaid').then(({ default: mermaid }) => {
      mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });
      const id = 'mermaid_' + Math.random().toString(36).slice(2);
      mermaid.render(id, chart).then(({ svg }) => {
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      }).catch(err => {
        if (!cancelled && ref.current) ref.current.innerHTML = `<pre style="color:#ef4444;font-size:0.75rem">${err.message}</pre>`;
      });
    });
    return () => { cancelled = true; };
  }, [chart]);
  return (
    <div ref={ref} style={{
      padding: '16px', background: 'rgba(255,255,255,0.6)', borderRadius: '12px',
      border: '1px solid rgba(139,92,246,0.15)', margin: '1rem 0',
      display: 'flex', justifyContent: 'center', overflowX: 'auto'
    }}>
      <span style={{ color: '#8b5cf6', fontSize: '0.8rem' }}>Rendering diagram…</span>
    </div>
  );
};

const markdownComponents = {
  code({ node, className, children, ...props }: any) {
    const isInline = !className;
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : 'text';
    const codeString = String(children).replace(/\n$/, '');

    // Mermaid diagram rendering
    if (language === 'mermaid') return <MermaidBlock chart={codeString} />;

    if (isInline) {
      return (
        <code style={{
          background: 'rgba(139,92,246,0.1)', color: '#6d28d9', padding: '2px 6px',
          borderRadius: '5px', fontSize: '0.87em', fontFamily: "'Fira Code', monospace",
          border: '1px solid rgba(139,92,246,0.2)'
        }} {...props}>{children}</code>
      );
    }
    return (
      <div style={{ position: 'relative', margin: '1rem 0' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: '#1e1b4b', padding: '8px 14px',
          borderRadius: '12px 12px 0 0', borderBottom: '1px solid rgba(255,255,255,0.08)'
        }}>
          <span style={{ fontSize: '0.7rem', color: '#a5b4fc', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            {language}
          </span>
          <CopyButton text={codeString} />
        </div>
        <SyntaxHighlighter style={oneLight} language={language} PreTag="div"
          customStyle={{
            margin: 0, borderRadius: '0 0 12px 12px', fontSize: '0.875rem',
            border: '1px solid rgba(139,92,246,0.12)', borderTop: 'none',
            padding: '1.1rem 1rem', background: 'rgba(255,255,255,0.7)',
            backdropFilter: 'blur(8px)'
          }}
          codeTagProps={{ style: { fontFamily: "'Fira Code', monospace" } }}
        >{codeString}</SyntaxHighlighter>
      </div>
    );
  },
  table({ children }: any) {
    return (
      <div style={{ overflowX: 'auto', margin: '1rem 0', borderRadius: '12px', border: '1px solid rgba(139,92,246,0.15)', boxShadow: '0 2px 12px rgba(139,92,246,0.06)' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.875rem' }}>{children}</table>
      </div>
    );
  },
  thead({ children }: any) { return <thead style={{ background: 'rgba(139,92,246,0.08)' }}>{children}</thead>; },
  th({ children }: any) { return <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: '#4c1d95', borderBottom: '2px solid rgba(139,92,246,0.15)' }}>{children}</th>; },
  td({ children }: any) { return <td style={{ padding: '9px 16px', borderBottom: '1px solid rgba(139,92,246,0.07)', color: '#374151' }}>{children}</td>; },
  tr({ children, ...props }: any) { return <tr onMouseEnter={e => (e.currentTarget.style.background = 'rgba(139,92,246,0.04)')} onMouseLeave={e => (e.currentTarget.style.background = '')} {...props}>{children}</tr>; },
  blockquote({ children }: any) {
    return (
      <blockquote style={{
        margin: '0.75rem 0', padding: '0.75rem 1rem',
        borderLeft: '4px solid #8b5cf6',
        background: 'rgba(139,92,246,0.06)',
        borderRadius: '0 10px 10px 0', color: '#5b21b6',
        fontStyle: 'italic', fontSize: '0.9rem'
      }}>{children}</blockquote>
    );
  },
  h1({ children }: any) { return <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#2d1b69', margin: '1.2rem 0 0.5rem', paddingBottom: '6px', borderBottom: '2px solid rgba(139,92,246,0.2)' }}>{children}</h1>; },
  h2({ children }: any) { return <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#6d28d9', margin: '1rem 0 0.4rem' }}>{children}</h2>; },
  h3({ children }: any) { return <h3 style={{ fontSize: '0.97rem', fontWeight: 600, color: '#4c1d95', margin: '0.8rem 0 0.3rem' }}>{children}</h3>; },
  ul({ children }: any) { return <ul style={{ margin: '0.5rem 0', paddingLeft: '1.4rem', display: 'flex', flexDirection: 'column', gap: '3px' }}>{children}</ul>; },
  ol({ children }: any) { return <ol style={{ margin: '0.5rem 0', paddingLeft: '1.4rem', display: 'flex', flexDirection: 'column', gap: '3px' }}>{children}</ol>; },
  li({ children }: any) { return <li style={{ color: '#374151', lineHeight: '1.65' }}>{children}</li>; },
  p({ children }: any) { return <p style={{ margin: '0.35rem 0', lineHeight: '1.75', color: '#374151' }}>{children}</p>; },
  strong({ children }: any) { return <strong style={{ fontWeight: 700, color: '#2d1b69' }}>{children}</strong>; },
  em({ children }: any) { return <em style={{ color: '#5b21b6', fontStyle: 'italic' }}>{children}</em>; },
  hr() { return <hr style={{ border: 'none', borderTop: '1px solid rgba(139,92,246,0.15)', margin: '1rem 0' }} />; },
};

// --- SVGs ---
const PaperclipIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
);
const ChevronDownIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
);
const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
);
const LogoIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2c-.65 2-.8 3.5-1 4.5C9 7 7 9 7 13c0 4.5 2.5 8 5 8s5-3.5 5-8c0-4-2-6-4-6.5-.2-1-.35-2.5-1-4.5" />
    <path d="M12 2s3-1 4 2" />
  </svg>
);
const FileIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
);
const ThumbUpIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>
);
const ThumbDownIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path></svg>
);
const CopyMsgIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
);

// --- Loading Dots ---
const LoadingDots = () => (
  <div className={styles.loadingDots}>
    <div className={styles.loadingDot} />
    <div className={styles.loadingDot} />
    <div className={styles.loadingDot} />
  </div>
);

// --- AI Avatar Orb ---
const AIAvatar = () => (
  <div style={{
    width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
    background: 'radial-gradient(circle at 35% 35%, rgba(255,255,255,0.9) 0%, rgba(216,180,254,0.8) 25%, rgba(167,139,250,0.7) 55%, rgba(139,92,246,0.6) 80%, rgba(109,40,217,0.4) 100%)',
    boxShadow: '0 4px 16px rgba(139,92,246,0.35), inset 0 2px 6px rgba(255,255,255,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: 'white'
  }}>
    <LogoIcon />
  </div>
);

// --- Confidence Badge (#9) ---
const ConfidenceBadge = ({ confidence }: { confidence?: Confidence }) => {
  if (!confidence) return null;
  const config = {
    high:   { emoji: '🟢', color: '#16a34a', bg: 'rgba(22,163,74,0.08)', border: 'rgba(22,163,74,0.2)' },
    medium: { emoji: '🟡', color: '#d97706', bg: 'rgba(217,119,6,0.08)',  border: 'rgba(217,119,6,0.2)' },
    low:    { emoji: '⚪', color: '#6b7280', bg: 'rgba(107,114,128,0.08)', border: 'rgba(107,114,128,0.2)' },
  };
  const c = config[confidence.level] || config.low;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      fontSize: '0.7rem', fontWeight: 600, padding: '2px 8px',
      borderRadius: '20px', border: `1px solid ${c.border}`,
      background: c.bg, color: c.color, letterSpacing: '0.02em'
    }}>
      {c.emoji} {confidence.label}
    </span>
  );
};

// --- Sidebar ---
const Sidebar = ({ sessions, activeSessionId, sources, onSelectSession, onNewChat, searchQuery, handleSearch, searchResults, isSearching }: any) => {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarHeader}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'linear-gradient(135deg, #8b5cf6, #d8b4fe)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
            <LogoIcon />
          </div>
          <span style={{ fontSize: '1.05rem', fontWeight: 800, color: '#2d1b69', letterSpacing: '-0.3px' }}>NexusIQ</span>
        </div>
      </div>
      
      <button className={styles.newChatBtn} onClick={onNewChat}>
        + New Chat
      </button>

      {/* #Search Input */}
      <div style={{ padding: '0 20px 10px 20px' }}>
        <input 
          type="text" 
          placeholder="🔍 Search past chats..." 
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          style={{ width: '100%', padding: '8px 12px', borderRadius: '10px', border: '1px solid rgba(139,92,246,0.2)', background: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', color: '#2d1b69', outline: 'none' }}
        />
      </div>

      <div className={styles.sessionList}>
        {searchQuery ? (
          <div>
            <div className={styles.sidebarSectionTitle}>SEARCH RESULTS</div>
            {isSearching ? (
              <div style={{ padding: '10px 20px', fontSize: '0.8rem', color: '#8b5cf6' }}>Searching...</div>
            ) : searchResults.length === 0 ? (
              <div style={{ padding: '10px 20px', fontSize: '0.8rem', color: '#6b7280' }}>No matches found</div>
            ) : (
              searchResults.map((res: any) => (
                <div key={res.message_id} className={styles.sessionItem} onClick={() => onSelectSession(res.session_id)}>
                  <div style={{ fontSize: '0.7rem', color: '#8b5cf6', fontWeight: 600 }}>{res.session_title}</div>
                  <div style={{ fontSize: '0.8rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{res.preview}</div>
                </div>
              ))
            )}
          </div>
        ) : (
          <>
            <div className={styles.sidebarSectionTitle}>RECENT</div>
            {sessions.map((s: any) => (
              <div key={s.id} className={`${styles.sessionItem} ${s.id === activeSessionId ? styles.sessionItemActive : ''}`} onClick={() => onSelectSession(s.id)}>
                {s.title}
                {s.id === activeSessionId && <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#8b5cf6', marginLeft: 'auto' }} />}
              </div>
            ))}
          </>
        )}
      </div>
    </aside>
  );
};

// --- App ---
const App = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState<string | null>(null); // #13 streaming
  const streamingRef = useRef<string>(''); // captures full streamed text
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(generateSessionId);
  const [sources, setSources] = useState<string[]>([]);
  const [lastImagePath, setLastImagePath] = useState<string | undefined>(undefined);
  const [user, setUser] = useState<User | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [isTitleMenuOpen, setIsTitleMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [copiedMsgIdx, setCopiedMsgIdx] = useState<number | null>(null);
  // New feature states
  const [isDragging, setIsDragging] = useState(false);          // #DragDrop
  const [searchQuery, setSearchQuery] = useState('');            // #Search
  const [searchResults, setSearchResults] = useState<any[]>([]); // #Search
  const [isSearching, setIsSearching] = useState(false);         // #Search
  const [isListening, setIsListening] = useState(false);         // #VoiceInput
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const titleMenuRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);                       // #VoiceInput

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (titleMenuRef.current && !titleMenuRef.current.contains(e.target as Node)) setIsTitleMenuOpen(false);
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) setIsUserMenuOpen(false);
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  useEffect(() => {
    getMe().then(u => { setUser(u); if (u) refreshSessions(); })
      .catch(console.error).finally(() => setIsAuthLoading(false));
  }, []);

  const refreshSessions = async () => {
    try { const res = await getSessions(); setSessions(res); } catch (e) { console.error(e); }
  };

  // #VoiceInput — mic toggle
  const handleVoiceInput = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) { alert('Voice input not supported in this browser.'); return; }
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }
    const rec = new SpeechRecognition();
    rec.lang = 'en-US'; rec.interimResults = false; rec.maxAlternatives = 1;
    rec.onresult = (e: any) => setInput(prev => prev + ' ' + e.results[0][0].transcript);
    rec.onend = () => setIsListening(false);
    rec.onerror = () => setIsListening(false);
    recognitionRef.current = rec;
    rec.start();
    setIsListening(true);
  };

  // #ChatExport — download conversation as .md
  const handleExport = () => {
    if (!messages.length) return;
    const lines = messages.map(m =>
      `**${m.role === 'user' ? 'You' : 'NexusIQ'}** _(${formatTime(m.timestamp)})_\n\n${m.content}\n`
    );
    const md = `# NexusIQ Chat Export\n\n---\n\n${lines.join('\n---\n\n')}`;
    const blob = new Blob([md], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `nexusiq_chat_${new Date().toISOString().slice(0,10)}.md`;
    a.click();
  };

  // #Search — full-text conversation search
  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (!q.trim() || q.length < 2) { setSearchResults([]); return; }
    setIsSearching(true);
    try {
      const res = await searchMessages(q);
      setSearchResults(res.results || []);
    } catch { setSearchResults([]); }
    finally { setIsSearching(false); }
  };

  // #DragDrop — drag-and-drop file upload
  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: React.DragEvent) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDragging(false); };
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length) {
      const mockEvent = { target: { files } } as any;
      await handleFileUpload(mockEvent);
    }
  };

  const handleNewChat = useCallback(() => {
    setSessionId(generateSessionId()); setMessages([]); setSources([]); setLastImagePath(undefined);
  }, []);

  const handleSelectSession = async (id: string) => {
    if (id === sessionId && messages.length > 0) return;
    try {
      setIsLoading(true);
      const res = await getSessionMessages(id);
      setSessionId(id);
      if (Array.isArray(res)) {
        setMessages(res.map((m: any) => ({ id: m.id, role: m.role, content: m.content, feedback: m.feedback, trace: m.trace, timestamp: m.timestamp })));
      } else {
        setMessages(res.messages.map((m: any) => ({ id: m.id, role: m.role, content: m.content, feedback: m.feedback, trace: m.trace, timestamp: m.timestamp })));
        setSources(res.files || []); setLastImagePath(res.lastImagePath || undefined);
      }
    } catch (e) { console.error(e); } finally { setIsLoading(false); }
  };

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg, timestamp: new Date().toISOString() }]);
    setIsLoading(true);
    streamingRef.current = '';
    setStreamingContent('');
    try {
      const history = [];
      for (let i = 0; i < messages.length; i += 2) {
        if (messages[i].role === 'user' && messages[i + 1]?.role === 'assistant')
          history.push({ user: messages[i].content, assistant: messages[i + 1].content });
      }
      let finalMeta: { message_id: number | null; confidence: Confidence } | null = null;
      await sendChatStream(userMsg, sessionId, history, lastImagePath, {
        onToken: (token) => {
          streamingRef.current += token;
          setStreamingContent(streamingRef.current);
        },
        onDone: (meta) => { finalMeta = meta as { message_id: number | null; confidence: Confidence }; },
        onError: (err) => console.error('Stream error:', err),
      });
      const finalContent = streamingRef.current;
      setStreamingContent(null);
      streamingRef.current = '';
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: finalContent || '(No response)',
        id: finalMeta?.message_id ?? undefined,
        confidence: finalMeta?.confidence,
        timestamp: new Date().toISOString()
      }]);
      if (user) refreshSessions();
    } catch (error) {
      console.error(error);
      setStreamingContent(null);
      streamingRef.current = '';
      setMessages(prev => [...prev, { role: 'assistant', content: '❌ Connection error. Please try again.', timestamp: new Date().toISOString() }]);
    } finally { setIsLoading(false); }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const files = Array.from(e.target.files);
    const fileNames = files.map(f => f.name);
    setIsLoading(true);
    try {
      const res = await uploadFiles(e.target.files, sessionId);
      setSources(prev => [...prev, ...fileNames]);
      const uploadedImageFiles = res.files?.filter((f: string) => f.match(/\.(png|jpe?g)$/i)) || [];
      if (uploadedImageFiles.length > 0) setLastImagePath(uploadedImageFiles[uploadedImageFiles.length - 1]);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `✅ **Upload Complete!**\n\nProcessed **${res.pdfs_processed} PDF(s)**, **${res.mds_processed || 0} Markdown file(s)**, **${res.images_processed} image(s)**.\n\nYou can now ask questions about these files.`,
        timestamp: new Date().toISOString(),
        trace: `__files__:${JSON.stringify(fileNames)}`
      }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'assistant', content: "❌ Error uploading files. Please try again.", timestamp: new Date().toISOString() }]);
    } finally { setIsLoading(false); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  const handleFeedback = async (msgId: number | undefined, value: number, msgIdx: number) => {
    if (!msgId) return;
    try { await sendFeedback(msgId, value); setMessages(prev => prev.map((m, i) => i === msgIdx ? { ...m, feedback: value } : m)); }
    catch (e) { console.error(e); }
  };

  const handleCopyMessage = async (content: string, idx: number) => {
    await navigator.clipboard.writeText(content);
    setCopiedMsgIdx(idx);
    setTimeout(() => setCopiedMsgIdx(null), 2000);
  };

  const handleDeleteSession = async () => {
    try { await deleteSession(sessionId); setIsTitleMenuOpen(false); refreshSessions(); handleNewChat(); }
    catch (e) { console.error(e); alert('Failed to delete session'); }
  };

  const handleLogout = () => { window.location.href = 'http://localhost:7860/logout'; };

  const SUGGESTED_PROMPTS = [
    "📄 Summarize uploaded document",
    "🔍 Latest AI news today",
    "🖼️ What's in this image?",
    "💻 Write a Python function",
    "📊 Compare React vs Vue",
    "❓ List all problem statements",
  ];

  const activeSessionTitle = sessions.find(s => s.id === sessionId)?.title || "New Chat";
  const userInitials = getUserInitials(user);

  if (isAuthLoading) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#fce7f3,#ede9fe,#ddd6fe,#c7d2fe)', fontFamily: 'Inter, system-ui, sans-serif' }}>
        <LoadingDots />
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#fce7f3 0%,#ede9fe 35%,#ddd6fe 65%,#c7d2fe 100%)', fontFamily: 'Inter, system-ui, sans-serif', position: 'relative', overflow: 'hidden' }}>
        {/* Background orbs */}
        <div style={{ position: 'absolute', top: '-100px', right: '-80px', width: '380px', height: '380px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(167,139,250,0.5) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', bottom: '-80px', left: '50px', width: '300px', height: '300px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(240,147,251,0.35) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <div style={{ background: 'rgba(255,255,255,0.45)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '52px 44px', borderRadius: '24px', boxShadow: '0 24px 64px rgba(139,92,246,0.18), 0 4px 16px rgba(0,0,0,0.06)', border: '1px solid rgba(255,255,255,0.7)', textAlign: 'center', maxWidth: 380, width: '100%', animation: 'fadeInUp 0.4s ease', position: 'relative', zIndex: 1 }}>
          {/* Big orb */}
          <div style={{ width: 80, height: 80, borderRadius: '50%', margin: '0 auto 24px', background: 'radial-gradient(circle at 35% 35%, rgba(255,255,255,0.9) 0%, rgba(216,180,254,0.8) 25%, rgba(167,139,250,0.7) 55%, rgba(139,92,246,0.6) 80%, rgba(109,40,217,0.4) 100%)', boxShadow: '0 0 0 1px rgba(255,255,255,0.5), 0 8px 32px rgba(139,92,246,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: '1.5rem' }}>
            <LogoIcon />
          </div>
          <h1 style={{ margin: '0 0 8px', fontSize: '1.7rem', color: '#2d1b69', fontWeight: 800, letterSpacing: '-0.5px' }}>Welcome to NexusIQ</h1>
          <p style={{ color: 'rgba(109,40,217,0.65)', margin: '0 0 6px', fontSize: '0.9rem' }}>Your multimodal AI assistant.</p>
          <p style={{ color: 'rgba(109,40,217,0.4)', margin: '0 0 36px', fontSize: '0.8rem' }}>Sign in to save your conversations.</p>
          <a href="http://localhost:7860/login/google" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', background: 'linear-gradient(135deg, #8b5cf6, #a855f7)', color: 'white', padding: '13px 24px', borderRadius: '14px', textDecoration: 'none', fontWeight: 700, fontSize: '0.95rem', boxShadow: '0 6px 20px rgba(139,92,246,0.4)', transition: 'all 0.2s' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Continue with Google
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.appContainer} onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
      {/* #DragDrop Overlay */}
      {isDragging && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(139,92,246,0.2)', backdropFilter: 'blur(4px)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '4px dashed #8b5cf6' }}>
          <h2 style={{ color: '#6d28d9', fontSize: '2rem', fontWeight: 800 }}>Drop files here to upload</h2>
        </div>
      )}

      {/* Floating background orbs */}
      <div className={styles.orb1} />
      <div className={styles.orb2} />
      <div className={styles.orb3} />

      <Sidebar sessions={sessions} activeSessionId={sessionId} sources={sources} onSelectSession={handleSelectSession} onNewChat={handleNewChat} searchQuery={searchQuery} handleSearch={handleSearch} searchResults={searchResults} isSearching={isSearching} />

      <main className={styles.mainContent}>
        {/* Header */}
        <header className={styles.mainHeader}>
          <div ref={titleMenuRef} style={{ position: 'relative' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, color: '#2d1b69', cursor: 'pointer', padding: '6px 10px', borderRadius: '10px', marginLeft: '-10px', fontSize: '0.95rem' }}
              onClick={() => setIsTitleMenuOpen(!isTitleMenuOpen)} className={styles.headerDropdownBtn}>
              {activeSessionTitle} <ChevronDownIcon />
            </div>
            {isTitleMenuOpen && (
              <div style={{ position: 'absolute', top: '100%', left: 0, marginTop: '6px', background: 'rgba(255,255,255,0.8)', backdropFilter: 'blur(20px)', border: '1px solid rgba(255,255,255,0.7)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(139,92,246,0.15)', zIndex: 10, minWidth: '160px', padding: '6px' }}>
                <div style={{ padding: '8px 12px', fontSize: '0.875rem', cursor: 'pointer', color: '#ef4444', borderRadius: '8px' }} onClick={handleDeleteSession} className={styles.dropdownItem}>🗑️ Delete Chat</div>
              </div>
            )}
          </div>

          <div ref={userMenuRef} style={{ position: 'relative' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: 600, color: '#2d1b69', cursor: 'pointer', padding: '4px 10px', borderRadius: '10px' }}
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)} className={styles.headerDropdownBtn}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #8b5cf6, #c084fc)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800, boxShadow: '0 3px 10px rgba(139,92,246,0.35)' }}>
                {userInitials}
              </div>
              {user.name || user.email}
              <ChevronDownIcon />
            </div>
            {isUserMenuOpen && (
              <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: '6px', background: 'rgba(255,255,255,0.8)', backdropFilter: 'blur(20px)', border: '1px solid rgba(255,255,255,0.7)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(139,92,246,0.15)', zIndex: 10, minWidth: '180px', padding: '6px' }}>
                <div style={{ padding: '8px 12px', fontSize: '0.72rem', color: 'rgba(109,40,217,0.5)', borderBottom: '1px solid rgba(139,92,246,0.1)', marginBottom: '4px' }}>{user.email}</div>
                <div style={{ padding: '8px 12px', fontSize: '0.875rem', cursor: 'pointer', color: '#374151', borderRadius: '8px' }} onClick={handleLogout} className={styles.dropdownItem}>Log out</div>
              </div>
            )}
          </div>
        </header>

        {/* Chat */}
        <div className={styles.chatArea}>
          {messages.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyStateOrb} />
              <h2 className={styles.emptyStateTitle}>How can I help you today?</h2>
              <p className={styles.emptyStateSubtitle}>Ask about documents, images, code, or anything on the web.</p>
              <div className={styles.suggestedPrompts}>
                {SUGGESTED_PROMPTS.map((p, i) => (
                  <div key={i} className={styles.suggestedPrompt}
                    onClick={() => setInput(p.replace(/^[\p{Emoji}\s]+/u, '').trim())}>
                    {p}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              let uploadedFiles: string[] = [];
              let displayTrace = msg.trace;
              if (msg.trace?.startsWith('__files__:')) {
                try { uploadedFiles = JSON.parse(msg.trace.replace('__files__:', '')); } catch {}
                displayTrace = undefined;
              }
              return (
                <div key={idx}
                  className={`${styles.messageContainer} ${isUser ? styles.messageContainerUser : ''}`}>
                  {/* Avatar */}
                  {isUser ? (
                    <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'linear-gradient(135deg,#8b5cf6,#a855f7)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800, flexShrink: 0, boxShadow: '0 4px 12px rgba(139,92,246,0.35)' }}>
                      {userInitials}
                    </div>
                  ) : <AIAvatar />}

                  {/* Bubble */}
                  <div className={isUser ? styles.messageContentUser : styles.messageContentAI}>
                    <div className={styles.messageHeader}>
                      <span className={isUser ? styles.messageNameUser : styles.messageName}>
                        {isUser ? 'You' : 'NexusIQ'}
                      </span>
                      <span className={isUser ? styles.messageTimeUser : styles.messageTime}>
                        {formatTime(msg.timestamp)}
                      </span>
                    </div>

                    <div style={{ overflowX: 'auto' }}>
                      {isUser ? (
                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.7', color: 'rgba(255,255,255,0.95)', fontSize: '0.92rem' }}>{msg.content}</div>
                      ) : (
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={markdownComponents}>
                          {msg.content}
                        </ReactMarkdown>
                      )}
                    </div>

                    {/* Uploaded file tags */}
                    {uploadedFiles.length > 0 && (
                      <div className={styles.fileTagsRow}>
                        {uploadedFiles.map((f, i) => (<div key={i} className={styles.fileTag}><FileIcon /> {f}</div>))}
                      </div>
                    )}

                    {/* Trace */}
                    {!isUser && displayTrace && (
                      <details style={{ marginTop: '12px', padding: '10px 12px', background: 'rgba(139,92,246,0.05)', borderRadius: '10px', border: '1px solid rgba(139,92,246,0.12)', fontSize: '0.78rem' }}>
                        <summary style={{ cursor: 'pointer', fontWeight: 600, color: '#7c3aed', userSelect: 'none' }}>🔍 View Reasoning Trace</summary>
                        <div style={{ marginTop: '10px', whiteSpace: 'pre-wrap', fontFamily: 'monospace', color: '#4c1d95' }}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{displayTrace}</ReactMarkdown>
                        </div>
                      </details>
                    )}

                    {/* Copy + Feedback */}
                    {!isUser && (
                      <div className={styles.feedbackRow}>
                        <ConfidenceBadge confidence={msg.confidence} />
                        <button className={styles.feedbackBtn} onClick={() => handleCopyMessage(msg.content, idx)} title="Copy">
                          <CopyMsgIcon /> {copiedMsgIdx === idx ? 'Copied!' : 'Copy'}
                        </button>
                        <div style={{ flex: 1 }} />
                        {msg.id && (<>
                          <button className={`${styles.feedbackBtn} ${msg.feedback === 1 ? styles.feedbackBtnActive : ''}`}
                            onClick={() => handleFeedback(msg.id, msg.feedback === 1 ? 0 : 1, idx)} title="Helpful"><ThumbUpIcon /></button>
                          <button className={`${styles.feedbackBtn} ${msg.feedback === -1 ? styles.feedbackBtnActive : ''}`}
                            onClick={() => handleFeedback(msg.id, msg.feedback === -1 ? 0 : -1, idx)} title="Not helpful"><ThumbDownIcon /></button>
                        </>)}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Live streaming bubble (#13) */}
          {streamingContent !== null && (
            <div className={styles.messageContainer}>
              <AIAvatar />
              <div className={styles.messageContentAI}>
                <div className={styles.messageHeader}>
                  <span className={styles.messageName}>NexusIQ</span>
                  <span style={{ fontSize: '0.68rem', color: 'rgba(139,92,246,0.4)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ width: 6, height: 6, background: '#8b5cf6', borderRadius: '50%', display: 'inline-block', animation: 'dotBounce 1s ease-in-out infinite' }} />
                    Streaming…
                  </span>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  {streamingContent ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={markdownComponents}>
                      {streamingContent}
                    </ReactMarkdown>
                  ) : <LoadingDots />}
                </div>
              </div>
            </div>
          )}

          {/* Static loading indicator (only when not streaming) */}
          {isLoading && streamingContent === null && (
            <div className={styles.messageContainer}>
              <AIAvatar />
              <div className={styles.messageContentAI}>
                <div className={styles.messageHeader}>
                  <span className={styles.messageName}>NexusIQ</span>
                </div>
                <LoadingDots />
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Prompt Bar */}
        <div className={styles.promptBarContainer}>
          <div className={styles.promptBar}>
            <div className={styles.promptInputRow}>
              <div style={{ paddingLeft: '8px' }}>
                <button className={styles.iconButton} onClick={() => fileInputRef.current?.click()} disabled={isLoading} title="Upload files">
                  <PaperclipIcon />
                </button>
              </div>
              <input type="file" multiple ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileUpload} accept=".pdf,.md,.png,.jpg,.jpeg" />
              <input type="text" className={styles.promptInput} value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder="Ask anything..." disabled={isLoading} />
              <div style={{ paddingRight: '8px', display: 'flex', gap: '4px' }}>
                <button className={styles.iconButton} onClick={handleVoiceInput} disabled={isLoading} title="Voice Input" style={{ color: isListening ? '#ef4444' : undefined }}>
                  🎤
                </button>
                <button className={styles.iconButton} onClick={handleExport} disabled={messages.length === 0} title="Export Chat">
                  📥
                </button>
                <button className={styles.sendButton} onClick={handleSend} disabled={isLoading || !input.trim()} title="Send">
                  <SendIcon />
                </button>
              </div>
            </div>
            <div className={styles.pillsRow}>
              <span className={styles.pill} onClick={() => setInput(p => p + '/docs ')}>📄 /docs</span>
              <span className={styles.pill} onClick={() => setInput(p => p + '/web ')}>🌐 /web</span>
              <span className={styles.pill} onClick={() => setInput(p => p + '/image ')}>🖼️ /image</span>
              <span className={styles.pill} onClick={() => setInput(p => p + '/code ')}>💻 /code</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
