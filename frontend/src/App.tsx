import { useState, useEffect } from 'react';
import { BirthForm } from './components/BirthForm';
import { ChatWindow } from './components/ChatWindow';
import { PlanetPositions } from './components/PlanetPositions';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

interface BirthDetails {
  name: string;
  date: string;
  time: string;
  place: string;
  latitude: number;
  longitude: number;
  timezone: string;
  display_name: string;
  sidereal: boolean;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

function App() {
  const [birthDetails, setBirthDetails] = useState<BirthDetails | null>(null);
  const [chartData, setChartData] = useState<any | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [activeTool, setActiveTool] = useState<{ name: string; label: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Settings states
  const [llmProvider, setLlmProvider] = useState<string>('gemini');
  const [apiKey, setApiKey] = useState<string>('');
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);

  // Load state from localStorage on startup
  useEffect(() => {
    const savedDetails = localStorage.getItem('astro_birth_details');
    const savedChart = localStorage.getItem('astro_chart_data');
    const savedMessages = localStorage.getItem('astro_messages');
    const savedProvider = localStorage.getItem('astro_llm_provider');
    const savedApiKey = localStorage.getItem('astro_api_key');

    if (savedDetails) {
      setBirthDetails(JSON.parse(savedDetails));
    }
    if (savedChart) {
      setChartData(JSON.parse(savedChart));
    }
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages));
    }
    if (savedProvider) {
      setLlmProvider(savedProvider);
    }
    if (savedApiKey) {
      setApiKey(savedApiKey);
    }
  }, []);

  const handleSaveSettings = (provider: string, key: string) => {
    setLlmProvider(provider);
    setApiKey(key);
    localStorage.setItem('astro_llm_provider', provider);
    localStorage.setItem('astro_api_key', key);
    setShowSettings(false);
    setSettingsError(null);
  };

  // Save messages to localStorage when updated
  const saveMessages = (updatedMsgs: Message[]) => {
    setMessages(updatedMsgs);
    localStorage.setItem('astro_messages', JSON.stringify(updatedMsgs));
  };

  const handleSaveBirthDetails = async (details: BirthDetails) => {
    setBirthDetails(details);
    localStorage.setItem('astro_birth_details', JSON.stringify(details));
    setError(null);
    setChartData(null);
    localStorage.removeItem('astro_chart_data');

    // Trigger an initial reading request from the agent
    const introPrompt = `My birth details are: Name: ${details.name}, Born: ${details.date} at ${details.time} in ${details.place} (Lat: ${details.latitude.toFixed(4)}, Lng: ${details.longitude.toFixed(4)}, Timezone: ${details.timezone}). Please calculate my birth chart using ${details.sidereal ? 'Vedic Sidereal' : 'Western Tropical'} coordinates, show me the placements, and provide a warm welcoming reading.`;
    
    // We send this system-aligned prompt behind the scenes to trigger the chart calculation, 
    // but show a cleaner, warmer user message in the UI:
    const userDisplayMsg: Message = {
      role: 'user',
      content: `Hello! I've shared my birth details. Please compute my birth chart and tell me about my alignments.`,
    };

    const newMessages = [...messages, userDisplayMsg];
    saveMessages(newMessages);
    
    await executeChatStream(newMessages, introPrompt, details);
  };

  const handleSendMessage = async (text: string) => {
    if (isStreaming) return;

    const newUserMessage: Message = { role: 'user', content: text };
    const updatedMessages = [...messages, newUserMessage];
    saveMessages(updatedMessages);
    setError(null);

    await executeChatStream(updatedMessages, text, birthDetails);
  };

  const executeChatStream = async (messageHistory: Message[], latestQuery: string, currentDetails: BirthDetails | null) => {
    setIsStreaming(true);
    setStreamingMessage('');
    setActiveTool(null);
    
    let accumulatedText = '';

    try {
      // Reconstruct payload. The history sent to backend includes the user's latest query
      // but if we are starting up, we swap the last display message content for the detailed intro prompt.
      const apiMessages = messageHistory.map((msg, idx) => {
        if (idx === messageHistory.length - 1 && currentDetails && msg.content.includes("Hello! I've shared my birth details")) {
          return { role: msg.role, content: latestQuery };
        }
        return { role: msg.role, content: msg.content };
      });

      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: apiMessages,
          birth_details: currentDetails ? {
            latitude: currentDetails.latitude,
            longitude: currentDetails.longitude,
            timezone: currentDetails.timezone,
            display_name: currentDetails.display_name,
          } : null,
          chart_data: chartData,
          sidereal: currentDetails?.sidereal || false,
          llm_provider: llmProvider,
          api_key: apiKey || null,
        }),
      });

      if (!response.ok) {
        throw new Error('Celestial connection disrupted. Please ensure the backend server is running.');
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Failed to read chat stream.');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim().startsWith('data: ')) {
            try {
              const data = JSON.parse(line.trim().substring(6));

              if (data.event === 'token') {
                accumulatedText += data.text;
                setStreamingMessage(accumulatedText);
              } else if (data.event === 'tool_start') {
                setActiveTool({ name: data.name, label: data.label });
              } else if (data.event === 'tool_end') {
                setActiveTool(null);
              } else if (data.event === 'state_update') {
                if (data.chart_data) {
                  setChartData(data.chart_data);
                  localStorage.setItem('astro_chart_data', JSON.stringify(data.chart_data));
                }
              } else if (data.event === 'error') {
                setError(data.message);
                if (data.error_type === 'quota_limit') {
                  setSettingsError(data.message);
                  setShowSettings(true);
                }
              }
            } catch (err) {
              console.error('Error parsing SSE event line:', err, line);
            }
          }
        }
      }

      // Append completed agent response to chat
      if (accumulatedText) {
        const finalMessages = [...messageHistory, { role: 'assistant' as const, content: accumulatedText }];
        saveMessages(finalMessages);
      }
    } catch (err: any) {
      console.error('Streaming error:', err);
      setError(err.message || 'Celestial communication error.');
    } finally {
      setIsStreaming(false);
      setStreamingMessage('');
      setActiveTool(null);
    }
  };

  const handleResetSession = () => {
    setBirthDetails(null);
    setChartData(null);
    setMessages([]);
    setStreamingMessage('');
    setActiveTool(null);
    setError(null);
    localStorage.removeItem('astro_birth_details');
    localStorage.removeItem('astro_chart_data');
    localStorage.removeItem('astro_messages');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header Bar */}
      <header
        style={{
          padding: '1.25rem 2rem',
          borderBottom: '1px solid var(--color-card-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(5, 6, 20, 0.4)',
          backdropFilter: 'blur(8px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.8rem', animation: 'pulse 3s infinite ease-in-out' }}>🌌</span>
          <span
            style={{
              fontSize: '1.6rem',
              fontWeight: 700,
              color: 'var(--color-text-main)',
              fontFamily: 'var(--font-title)',
              letterSpacing: '0.8px',
            }}
          >
            Aradhana
          </span>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <button
            onClick={() => setShowSettings(true)}
            style={{
              background: 'rgba(212, 175, 55, 0.1)',
              border: '1px solid var(--color-gold)',
              color: 'var(--color-gold-light)',
              padding: '0.4rem 0.8rem',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              transition: 'all 0.2s',
            }}
            onMouseOver={(e) => e.currentTarget.style.background = 'rgba(212, 175, 55, 0.25)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'rgba(212, 175, 55, 0.1)'}
          >
            ⚙️ Settings
          </button>
          <span
            style={{
              fontSize: '0.85rem',
              color: 'var(--color-text-muted)',
              border: '1px solid var(--color-card-border)',
              padding: '0.4rem 0.8rem',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(255, 255, 255, 0.03)',
            }}
          >
            Provider: <strong style={{ color: 'var(--color-gold-light)' }}>{llmProvider.toUpperCase()}</strong>
          </span>
        </div>
      </header>

      {/* Main Layout Container */}
      <main
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: 'minmax(350px, 450px) 1fr',
          gap: '2rem',
          padding: '2rem',
          maxWidth: '1400px',
          width: '100%',
          margin: '0 auto',
        }}
      >
        {/* Left Side: Chart details and setup */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {!birthDetails ? (
            <div style={{ margin: 'auto 0' }}>
              <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '2rem', color: 'var(--color-text-main)', marginBottom: '0.5rem' }}>
                  Meet Your Astrological Guide
                </h2>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
                  Please share your natal details to align with the movements of the cosmos.
                </p>
              </div>
              <BirthForm onSave={handleSaveBirthDetails} />
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Profile Card */}
              <div className="glass-panel" style={{ padding: '1.25rem' }}>
                <h4 style={{ color: 'var(--color-gold)', marginBottom: '0.6rem' }} className="gold-glow">
                  👤 Devotee Profile
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.85rem' }}>
                  <div>
                    <span style={{ color: 'var(--color-text-muted)' }}>Name:</span>{' '}
                    <strong>{birthDetails.name}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--color-text-muted)' }}>Date:</span>{' '}
                    <strong>{birthDetails.date}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--color-text-muted)' }}>Time:</span>{' '}
                    <strong>{birthDetails.time}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--color-text-muted)' }}>Calculation:</span>{' '}
                    <strong>{birthDetails.sidereal ? 'Sidereal' : 'Tropical'}</strong>
                  </div>
                  <div style={{ gridColumn: 'span 2' }}>
                    <span style={{ color: 'var(--color-text-muted)' }}>Place:</span>{' '}
                    <span style={{ fontSize: '0.8rem' }}>{birthDetails.place}</span>
                  </div>
                </div>
                <button
                  onClick={() => {
                    const confirmEdit = window.confirm(
                      'Editing your birth details will clear your current chart calculations. Proceed?'
                    );
                    if (confirmEdit) {
                      setBirthDetails(null);
                      setChartData(null);
                      localStorage.removeItem('astro_birth_details');
                      localStorage.removeItem('astro_chart_data');
                    }
                  }}
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--color-card-border)',
                    color: 'var(--color-gold-light)',
                    padding: '0.3rem 0.6rem',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    marginTop: '0.8rem',
                    width: '100%',
                  }}
                >
                  Edit Birth Details
                </button>
              </div>

              {/* Placements Card */}
              {chartData ? (
                <PlanetPositions chartData={chartData} sidereal={birthDetails.sidereal} />
              ) : (
                <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  <div className="pulse-indicator" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>✨</div>
                  <p style={{ fontSize: '0.9rem' }}>Aligning birth details with the ephemeris...</p>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Right Side: Chat Window */}
        <section style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {error && (
            <div
              style={{
                background: 'rgba(255, 107, 107, 0.1)',
                border: '1px solid rgba(255, 107, 107, 0.3)',
                padding: '0.8rem 1.2rem',
                borderRadius: 'var(--radius-md)',
                color: '#ff6b6b',
                marginBottom: '1rem',
                fontSize: '0.9rem',
              }}
            >
              ⚠️ {error}
            </div>
          )}
          <ChatWindow
            messages={messages}
            onSendMessage={handleSendMessage}
            isStreaming={isStreaming}
            streamingMessage={streamingMessage}
            activeTool={activeTool}
            onReset={handleResetSession}
          />
        </section>
      </main>

      {/* Dynamic Settings Modal overlay */}
      {showSettings && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(5, 6, 20, 0.75)',
            backdropFilter: 'blur(12px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            animation: 'fadeIn 0.25s ease-out',
          }}
        >
          <div 
            className="glass-panel" 
            style={{
              padding: '2.5rem',
              maxWidth: '500px',
              width: '90%',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.5rem',
              boxShadow: '0 0 40px rgba(0, 0, 0, 0.8), 0 0 30px rgba(212, 175, 55, 0.15)',
              border: '1px solid rgba(212, 175, 55, 0.25)',
              borderRadius: 'var(--radius-lg)',
              position: 'relative'
            }}
          >
            <button 
              onClick={() => { setShowSettings(false); setSettingsError(null); }}
              style={{
                position: 'absolute',
                top: '1.25rem',
                right: '1.25rem',
                background: 'transparent',
                border: 'none',
                color: 'var(--color-text-muted)',
                fontSize: '1.5rem',
                cursor: 'pointer',
                lineHeight: 1,
                outline: 'none',
              }}
            >
              ×
            </button>
            
            <h3 className="gold-glow" style={{ color: 'var(--color-gold)', fontSize: '1.6rem', textAlign: 'center', margin: 0 }}>
              ⚙️ Celestial Settings
            </h3>
            
            {settingsError && (
              <div style={{ color: '#ff6b6b', fontSize: '0.85rem', background: 'rgba(255, 107, 107, 0.12)', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255, 107, 107, 0.25)', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span>⚠️</span> 
                <span>{settingsError}</span>
              </div>
            )}
            
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', margin: 0, textAlign: 'center' }}>
              Configure your preferred language model provider and custom API keys.
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>LLM Provider</label>
                <select
                  value={llmProvider}
                  onChange={(e) => setLlmProvider(e.target.value)}
                  style={{
                    padding: '0.75rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-card-border)',
                    background: 'rgba(5, 6, 20, 0.85)',
                    color: 'var(--color-text-main)',
                    fontSize: '1rem',
                    outline: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <option value="gemini">Google Gemini (Recommended)</option>
                  <option value="openai">OpenAI GPT</option>
                  <option value="openrouter">OpenRouter API</option>
                  <option value="ollama">Ollama (Local)</option>
                </select>
              </div>
              
              {llmProvider !== 'ollama' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                    Custom API Key <span style={{ fontSize: '0.75rem', fontWeight: 'normal' }}>(Optional)</span>
                  </label>
                  <input
                    type="password"
                    placeholder={
                      llmProvider === 'gemini' ? 'AIzaSy...' : 
                      llmProvider === 'openai' ? 'sk-proj-...' : 
                      'Enter API key...'
                    }
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    style={{
                      padding: '0.75rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-card-border)',
                      background: 'rgba(5, 6, 20, 0.85)',
                      color: 'var(--color-text-main)',
                      fontSize: '1rem',
                      outline: 'none',
                    }}
                  />
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem', margin: '0.1rem 0 0 0' }}>
                    Leave blank to use the system default backup keys.
                  </p>
                </div>
              )}
              
              {llmProvider === 'ollama' && (
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.8rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-card-border)' }}>
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', margin: 0 }}>
                    ℹ️ Local Ollama requires a running instance on <strong>http://localhost:11434</strong> with the model loaded.
                  </p>
                </div>
              )}
              
              <button
                onClick={() => handleSaveSettings(llmProvider, apiKey)}
                style={{
                  padding: '0.9rem',
                  background: 'var(--color-gold)',
                  color: 'var(--bg-deep)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '1rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  marginTop: '0.5rem',
                  transition: 'all 0.3s',
                  boxShadow: '0 0 15px var(--color-gold-glow)',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'var(--color-gold-light)';
                  e.currentTarget.style.boxShadow = '0 0 25px var(--color-gold)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'var(--color-gold)';
                  e.currentTarget.style.boxShadow = '0 0 15px var(--color-gold-glow)';
                }}
              >
                Apply Celestial Configuration
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
