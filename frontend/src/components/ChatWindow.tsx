import React, { useState, useRef, useEffect } from 'react';
import { ToolActivity } from './ToolActivity';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatWindowProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  isStreaming: boolean;
  streamingMessage: string;
  activeTool: { name: string; label: string } | null;
  onReset: () => void;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  onSendMessage,
  isStreaming,
  streamingMessage,
  activeTool,
  onReset,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage, activeTool]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isStreaming) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '600px', width: '100%' }}>
      {/* Chat Header */}
      <div
        style={{
          padding: '1rem 1.5rem',
          borderBottom: '1px solid var(--color-card-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.4rem' }}>🕉️</span>
          <div>
            <h4 style={{ color: 'var(--color-gold)', margin: 0 }} className="gold-glow">AstroAgent</h4>
            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', margin: 0 }}>Daily Spiritual Companion</p>
          </div>
        </div>
        <button
          onClick={onReset}
          style={{
            background: 'transparent',
            border: '1px solid rgba(255, 107, 107, 0.4)',
            color: '#ff6b6b',
            padding: '0.4rem 0.8rem',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontSize: '0.8rem',
            transition: 'all 0.2s',
          }}
          onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(255, 107, 107, 0.1)')}
          onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
        >
          Reset Session
        </button>
      </div>

      {/* Message List */}
      <div
        style={{
          flex: 1,
          padding: '1.5rem',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        {messages.length === 0 && (
          <div style={{ margin: 'auto', textAlign: 'center', maxWidth: '350px', color: 'var(--color-text-muted)' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>✨</div>
            <p style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
              Welcome to your spiritual companion. Ask me anything about your natal alignments, daily transits, or general guidance.
            </p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '80%',
            }}
          >
            <div
              style={{
                background: msg.role === 'user' ? 'var(--color-user-bubble)' : 'var(--color-agent-bubble)',
                border: msg.role === 'user' ? '1px solid rgba(255, 255, 255, 0.08)' : '1px solid var(--color-card-border)',
                padding: '0.8rem 1.1rem',
                borderRadius: msg.role === 'user' ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                color: 'var(--color-text-main)',
                fontSize: '0.95rem',
                lineHeight: '1.5',
                whiteSpace: 'pre-wrap',
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Streaming Answer */}
        {isStreaming && streamingMessage && (
          <div style={{ alignSelf: 'flex-start', maxWidth: '80%' }}>
            <div
              style={{
                background: 'var(--color-agent-bubble)',
                border: '1px solid var(--color-card-border)',
                padding: '0.8rem 1.1rem',
                borderRadius: '16px 16px 16px 2px',
                color: 'var(--color-text-main)',
                fontSize: '0.95rem',
                lineHeight: '1.5',
                whiteSpace: 'pre-wrap',
              }}
            >
              {streamingMessage}
              <span className="pulse-indicator" style={{ fontWeight: 'bold', color: 'var(--color-gold)', marginLeft: '2px' }}>|</span>
            </div>
          </div>
        )}

        {/* Active Tool Spinner */}
        {activeTool && (
          <div style={{ alignSelf: 'flex-start' }}>
            <ToolActivity toolName={activeTool.name} label={activeTool.label} />
          </div>
        )}

        {/* Scrolling anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form
        onSubmit={handleSubmit}
        style={{
          padding: '1rem 1.5rem',
          borderTop: '1px solid var(--color-card-border)',
          display: 'flex',
          gap: '0.75rem',
        }}
      >
        <input
          type="text"
          className="gold-border-glow"
          placeholder={isStreaming ? 'Awaiting stellar currents...' : 'Ask your question...'}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          disabled={isStreaming}
          style={{
            flex: 1,
            padding: '0.8rem 1rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-card-border)',
            background: 'rgba(5, 6, 20, 0.6)',
            color: 'var(--color-text-main)',
            fontSize: '0.95rem',
          }}
        />
        <button
          type="submit"
          disabled={!inputText.trim() || isStreaming}
          style={{
            background: inputText.trim() && !isStreaming ? 'var(--color-gold)' : 'rgba(255, 255, 255, 0.05)',
            color: inputText.trim() && !isStreaming ? 'var(--bg-deep)' : 'var(--color-text-muted)',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            padding: '0 1.5rem',
            fontWeight: '600',
            cursor: inputText.trim() && !isStreaming ? 'pointer' : 'default',
            transition: 'all 0.2s',
          }}
        >
          Send
        </button>
      </form>
    </div>
  );
};
