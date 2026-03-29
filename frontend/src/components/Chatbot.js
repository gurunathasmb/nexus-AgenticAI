import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { getApiBase } from '../config';

const API_BASE = getApiBase();

const PERSONAS = ['default', 'student', 'faculty', 'parent', 'recruiter'];

function Chatbot() {
  const [messages, setMessages] = useState([
    { text: 'Hello! I am your AIML Nexus assistant. How can I help you today? You can ask about your results, timetable, attendance, or fees.', sender: 'bot' }
  ]);
  const [input, setInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState([]);
  const [persona, setPersona] = useState('default');
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);

  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition
  } = useSpeechRecognition();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  // Create a backend session on mount
  useEffect(() => {
    createSession();
    fetchAgents();
  }, []);

  const createSession = async () => {
    try {
      const res = await fetch(`${API_BASE}/chat/session`, { method: 'POST' });
      const data = await res.json();
      setSessionId(data.session_id);
      console.log('Session created:', data.session_id);
    } catch (err) {
      console.warn('Backend not available, falling back to local mode:', err.message);
    }
  };

  const fetchAgents = async () => {
    try {
      const res = await fetch(`${API_BASE}/agents/`);
      const data = await res.json();
      setAgents(data);
    } catch (err) {
      console.warn('Could not fetch agents:', err.message);
    }
  };

  const sendToBackend = async (text) => {
    if (!sessionId) return null;

    try {
      const res = await fetch(
        `${API_BASE}/chat/send?session_id=${sessionId}&text=${encodeURIComponent(text)}&persona=${encodeURIComponent(persona)}`,
        { method: 'POST' }
      );
      const data = await res.json();
      return data;
    } catch (err) {
      console.warn('Backend send failed, using fallback:', err.message);
      return null;
    }
  };

  const handleVoiceInput = () => {
    if (!browserSupportsSpeechRecognition) {
      alert('Browser does not support speech recognition.');
      return;
    }
    if (listening) {
      SpeechRecognition.stopListening();
      setIsListening(false);
      if (input.trim()) {
        handleSend();
      }
    } else {
      resetTranscript();
      SpeechRecognition.startListening({ continuous: true });
      setIsListening(true);
    }
  };

  const handleSend = async () => {
    if (input.trim()) {
      const userMessage = { text: input, sender: 'user' };
      const newMessages = [...messages, userMessage];
      setMessages(newMessages);
      const currentInput = input;
      setInput('');

      // Reset voice
      if (isListening) {
        SpeechRecognition.stopListening();
        setIsListening(false);
        resetTranscript();
      }

      // Save to local history
      if (!currentChatId) {
        const chatId = Date.now().toString();
        setCurrentChatId(chatId);
        const newChat = {
          id: chatId,
          title: currentInput.slice(0, 30) + (currentInput.length > 30 ? '...' : ''),
          messages: newMessages,
          timestamp: new Date()
        };
        setChatHistory(prev => [newChat, ...prev]);
      } else {
        setChatHistory(prev => prev.map(chat =>
          chat.id === currentChatId ? { ...chat, messages: newMessages } : chat
        ));
      }

      setLoading(true);

      // Try backend first, fall back to local
      const backendResponse = await sendToBackend(currentInput);

      let botMessage;
      if (backendResponse && backendResponse.response) {
        const agentName = backendResponse.sender || 'agent';
        botMessage = {
          text: backendResponse.response,
          sender: 'bot',
          agent: agentName,
          intent: backendResponse.intent,
          confidence: backendResponse.confidence,
          entropy_reduction: backendResponse.entropy_reduction,
          reasoning: backendResponse.reasoning,
        };
      } else {
        // Fallback to local mock responses
        const response = generateResponse(currentInput.toLowerCase());
        botMessage = { text: response, sender: 'bot', agent: 'local' };
      }

      const finalMessages = [...newMessages, botMessage];
      setMessages(finalMessages);

      setChatHistory(prev => prev.map(chat =>
        chat.id === currentChatId ? { ...chat, messages: finalMessages } : chat
      ));

      setLoading(false);
    }
  };

  const startNewChat = () => {
    setCurrentChatId(null);
    setMessages([
      { text: 'Hello! I am your AIML Nexus assistant. How can I help you today? You can ask about your results, timetable, attendance, or fees.', sender: 'bot' }
    ]);
    // Create new backend session
    createSession();
  };

  const loadChat = (chatId) => {
    const chat = chatHistory.find(c => c.id === chatId);
    if (chat) {
      setCurrentChatId(chatId);
      setMessages(chat.messages);
    }
  };

  const toggleAgent = async (agentName, currentEnabled) => {
    try {
      const action = currentEnabled ? 'disable' : 'enable';
      await fetch(`${API_BASE}/agents/${action}/${agentName}`, { method: 'POST' });
      fetchAgents();
    } catch (err) {
      console.warn('Could not toggle agent:', err.message);
    }
  };

  // --- Fallback local response generator (same as original) ---
  const generateResponse = (query) => {
    if (query.includes('result') || query.includes('grade') || query.includes('marks')) {
      return 'Academic results module is active. Please specify semester/year for detailed results.';
    } else if (query.includes('timetable') || query.includes('schedule') || query.includes('class')) {
      return 'Timetable module is active. Please specify the day for your schedule.';
    } else if (query.includes('attendance') || query.includes('present')) {
      return 'Attendance module is active. Please specify batch year for records.';
    } else if (query.includes('fees') || query.includes('payment') || query.includes('tuition')) {
      return 'Fee structure module is active. Contact accounts for payment queries.';
    } else if (query.includes('faculty') || query.includes('teacher') || query.includes('professor')) {
      return 'Faculty information module is active.';
    } else if (query.includes('placement') || query.includes('job') || query.includes('career')) {
      return 'Placement pipeline is available. Check placement portal for upcoming drives.';
    } else {
      return 'I am your AIML Nexus assistant. I can help with results, timetable, attendance, fees, faculty, and placements. Please ask about any of these topics!';
    }
  };

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      background: 'linear-gradient(to bottom, #16213e, #0f3460)',
      color: 'white'
    }}>
      {/* Sidebar for chat history */}
      <div style={{
        width: '300px',
        backgroundColor: 'rgba(0,0,0,0.2)',
        borderRight: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{
          padding: '20px',
          borderBottom: '1px solid rgba(255,255,255,0.1)'
        }}>
          <button
            id="new-chat-btn"
            onClick={startNewChat}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer',
              marginBottom: '10px'
            }}
          >
            New Chat
          </button>
          <h3>Chat History</h3>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {chatHistory.map(chat => (
            <div
              key={chat.id}
              onClick={() => loadChat(chat.id)}
              style={{
                padding: '10px 20px',
                cursor: 'pointer',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                backgroundColor: currentChatId === chat.id ? 'rgba(76,175,80,0.2)' : 'transparent'
              }}
            >
              <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>{chat.title}</div>
              <div style={{ fontSize: '12px', color: '#cccccc' }}>
                {chat.timestamp.toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>

        {/* Agent Status Panel */}
        {agents.length > 0 && (
          <div style={{
            padding: '15px',
            borderTop: '1px solid rgba(255,255,255,0.1)',
            fontSize: '13px'
          }}>
            <h4 style={{ marginBottom: '8px', color: '#80cbc4' }}>🤖 Agents</h4>
            {agents.map(a => (
              <div key={a.name} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '4px',
                padding: '4px 0'
              }}>
                <span style={{ opacity: a.enabled ? 1 : 0.5 }}>
                  {a.enabled ? '🟢' : '🔴'} {a.name}
                </span>
                <button
                  onClick={() => toggleAgent(a.name, a.enabled)}
                  style={{
                    padding: '2px 8px',
                    fontSize: '11px',
                    background: a.enabled ? 'rgba(255,82,82,0.3)' : 'rgba(76,175,80,0.3)',
                    color: 'white',
                    border: '1px solid rgba(255,255,255,0.2)',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  {a.enabled ? 'off' : 'on'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main chat area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '10px 20px',
          backgroundColor: 'rgba(0,0,0,0.3)',
          borderBottom: '1px solid rgba(255,255,255,0.1)'
        }}>
          <h2 id="chat-header">AIML NEXUS ASSISTANT</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <select
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              style={{
                padding: '6px 10px',
                borderRadius: '5px',
                border: '1px solid rgba(255,255,255,0.3)',
                backgroundColor: '#1a1a2e',
                color: 'white',
                fontSize: '13px',
                cursor: 'pointer'
              }}
            >
              {PERSONAS.map(p => (
                <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
              ))}
            </select>
            {sessionId && (
              <span style={{ fontSize: '12px', color: '#80cbc4' }}>
                Session: {sessionId}
              </span>
            )}
            <button
              id="logout-btn"
              onClick={() => navigate('/')}
              style={{
                padding: '8px 16px',
                backgroundColor: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer'
              }}
            >
              Logout
            </button>
          </div>
        </div>

        <div style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, overflowY: 'auto', marginBottom: '20px' }}>
            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  marginBottom: '10px',
                  textAlign: msg.sender === 'user' ? 'right' : 'left'
                }}
              >
                {msg.agent && msg.sender === 'bot' && (
                  <div style={{
                    fontSize: '11px',
                    color: '#80cbc4',
                    marginBottom: '2px',
                    fontStyle: 'italic'
                  }}>
                    via {msg.agent}
                    {msg.intent && (
                      <span style={{ marginLeft: '8px', color: '#ffcc80' }}>
                        | intent: {msg.intent} | conf: {msg.confidence} | ΔH: {msg.entropy_reduction}
                      </span>
                    )}
                  </div>
                )}
                {msg.reasoning && msg.sender === 'bot' && (
                  <div style={{
                    fontSize: '10px',
                    color: '#a5a5a5',
                    marginBottom: '2px',
                    maxWidth: '70%',
                  }}>
                    {msg.reasoning}
                  </div>
                )}
                <div
                  style={{
                    display: 'inline-block',
                    padding: '10px 15px',
                    borderRadius: '20px',
                    backgroundColor: msg.sender === 'user' ? '#4CAF50' : 'rgba(255,255,255,0.1)',
                    maxWidth: '70%',
                    whiteSpace: 'pre-line'
                  }}
                >
                  {msg.text}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ marginTop: '10px', color: '#80cbc4', fontStyle: 'italic' }}>
                <span className="loading-dots">Agent is thinking</span>
                <span>...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <input
              id="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about results, timetable, attendance, fees..."
              style={{
                flex: 1,
                padding: '10px',
                borderRadius: '20px',
                border: 'none',
                marginRight: '10px',
                backgroundColor: '#E8F5E8',
                color: '#333'
              }}
            />
            <button
              id="voice-btn"
              onClick={handleVoiceInput}
              style={{
                padding: '10px',
                backgroundColor: isListening ? '#FF5722' : '#2196F3',
                color: 'white',
                border: 'none',
                borderRadius: '50%',
                cursor: 'pointer',
                width: '40px',
                height: '40px',
                marginRight: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title={isListening ? 'Stop Listening' : 'Start Voice Input'}
            >
              {isListening ? '⏹️' : '🎤'}
            </button>
            <button
              id="send-btn"
              onClick={handleSend}
              disabled={loading}
              style={{
                padding: '10px 20px',
                backgroundColor: loading ? '#666' : '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '20px',
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? '...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chatbot;
