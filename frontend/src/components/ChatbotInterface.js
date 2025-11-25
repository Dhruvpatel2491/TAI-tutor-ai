import React, { useState, useEffect, useRef, useCallback } from 'react';
import '../styles/ChatbotInterface.css';
import FormattedMessage from './FormattedMessage';
import { formatBotResponse } from '../utils/messageFormatter';
import { DEFAULT_BACKEND_URL } from '../config';
import { apiGet, apiPost } from '../services/http';

// Constants
const INITIAL_MESSAGE = {
  id: 1,
  text: 'Hello! I\'m your TAI Tutor AI. Ask me anything!',
  sender: 'bot',
  timestamp: new Date()
};
const DEFAULT_MODEL = 'llama3:8b';
const AVAILABLE_MODELS = [
  'codegemma:7b',
  'gemma:7b',
  'gpt-oss:latest',
  'llama2:latest',
  'llama3:8b',
  'llama3:70b',
  'llama3-chatqa:latest'
];
// Use centralized frontend config for backend URL
const BACKEND_TIMEOUT = 60 * 1000; // 60 seconds
const QUERY_TIMEOUT = 120 * 1000; // 120 seconds
const HEALTH_CHECK_INTERVAL = 120 * 1000; // 120 seconds

// Normalized status constants
const STATUS_CONNECTED = 'connected';
const STATUS_DISCONNECTED = 'disconnected';
const STATUS_CHECKING = 'checking';

const ChatbotInterface = () => {
  // State - Messages
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);

  // State - User Input
  const [inputValue, setInputValue] = useState('');

  // State - Model Configuration
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL);
  const [models] = useState(AVAILABLE_MODELS);
  // State - Prompt Mode Configuration (hint or direct)
  const PROMPT_MODES = ["hint", "direct"];
  const [selectedPromptMode, setSelectedPromptMode] = useState(process.env.REACT_APP_DEFAULT_PROMPT_MODE || 'hint');

  // State - Backend Connection
  const [backendURL, setBackendURL] = useState(DEFAULT_BACKEND_URL);
  const [backendStatus, setBackendStatus] = useState(STATUS_CHECKING);
  const [showURLInput, setShowURLInput] = useState(false);
  const [tempURL, setTempURL] = useState(backendURL);

  // State - Loading
  const [loading, setLoading] = useState(false);

  // Refs
  const messagesEndRef = useRef(null);

  // Check backend connection
  const checkBackendConnection = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), BACKEND_TIMEOUT);
      const response = await apiGet(`${backendURL}/health`, { signal: controller.signal });
      clearTimeout(timeoutId);
      setBackendStatus(response.ok ? STATUS_CONNECTED : STATUS_DISCONNECTED);
    } catch (error) {
      // network or fetch error -> treat as disconnected
      setBackendStatus(STATUS_DISCONNECTED);
    }
  }, [backendURL]);

  // Effects - Backend health check
  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, HEALTH_CHECK_INTERVAL);
    return () => clearInterval(interval);
  }, [checkBackendConnection]);

  // Effects - Auto-scroll to bottom
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const sendMessage = async () => {
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const questionText = inputValue;
    setInputValue('');
    setLoading(true);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), QUERY_TIMEOUT);

      const response = await apiPost(`${backendURL}/query_v2`, {
        signal: controller.signal,
        mode: 'cors',
        question: questionText,
        model: selectedModel,
        rebuild: false
      });
      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        const formattedBlocks = formatBotResponse(data.answer);
        const botMessage = {
          id: messages.length + 2,
          text: data.answer,
          formatted: formattedBlocks,
          sender: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        const errorMessage = {
          id: messages.length + 2,
          text: `Error: ${errorData.error || 'An error occurred'}`,
          sender: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: messages.length + 2,
        text: `Error: Failed to connect to backend at ${backendURL}. Check that:\n1. Backend server is running\n2. URL is correct\n3. Network connection is stable\n\nError: ${error.message}`,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      setBackendStatus(STATUS_DISCONNECTED);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateURL = () => {
    setBackendURL(tempURL);
    setShowURLInput(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // derive a simple status class for styling (connected/disconnected/unknown)
  const statusClass = backendStatus === STATUS_CONNECTED
    ? 'status-connected'
    : (backendStatus === STATUS_DISCONNECTED ? 'status-disconnected' : 'status-unknown');

  const statusText = backendStatus === STATUS_CONNECTED
    ? 'Connected'
    : (backendStatus === STATUS_DISCONNECTED ? 'Disconnected' : 'Checking...');

  return (
    <div className="chatbot-container">
      {/* Top: header (left) and backend/status (right) */}
      <div className="chatbot-top">
        <div className="chatbot-header-left">
          <h1>TAI Tutor</h1>
          <p>AI-Powered Learning Assistant</p>
        </div>

        <div className="chatbot-header-side">
          <div className="backend-status">
            {/* colored dot */}
            <span className={`status-indicator ${statusClass}`}></span>
            <span className="status-text">{statusText}</span>
            {/* retry button */}
            <button
              className="status-retry-btn"
              onClick={checkBackendConnection}
              aria-label="Retry backend health check"
              title="Retry"
            >
              ⟳
            </button>
            {/* settings */}
            <button
              className="url-config-btn"
              onClick={() => setShowURLInput(!showURLInput)}
              aria-label="Configure backend URL"
            >
              ⚙️
            </button>
          </div>
        </div>
      </div>

      {/* URL Configuration Modal */}
      {showURLInput && (
        <div
          className="url-modal-backdrop"
          onClick={() => setShowURLInput(false)}
          role="presentation"
        >
          <div
            className="url-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Backend URL configuration"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="url-modal-header">
              <h3>Configure Backend URL</h3>
              <button
                className="url-modal-close"
                onClick={() => setShowURLInput(false)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>
            <div className="url-input-container">
              <input
                type="text"
                value={tempURL}
                onChange={(e) => setTempURL(e.target.value)}
                placeholder="Backend URL"
                className="url-input"
              />
              <div className="url-modal-actions">
                <button onClick={handleUpdateURL} className="url-confirm-btn">
                  Update
                </button>
                <button onClick={() => setShowURLInput(false)} className="url-cancel-btn">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Model + Prompt Mode Selector (same row, 50/50) */}
      <div className="model-selector">
        <div className="model-row">
          <div className="control-half">
            <label htmlFor="model-dropdown">Select Model:</label>
            <div className="model-control">
              <select
                id="model-dropdown"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={loading}
                className="model-dropdown"
              >
                {models.map(model => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="control-half">
            <label htmlFor="prompt-mode-dropdown">Prompt Mode:</label>
            <div className="model-control">
              <select
                id="prompt-mode-dropdown"
                value={selectedPromptMode}
                onChange={(e) => setSelectedPromptMode(e.target.value)}
                disabled={loading}
                className="model-dropdown"
              >
                {PROMPT_MODES.map(mode => (
                  <option key={mode} value={mode}>
                    {mode.charAt(0).toUpperCase() + mode.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Messages Display */}
      <div className="messages-container">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.sender === 'user' ? 'user-message' : 'bot-message'}`}
          >
            <div className="message-content">
              {message.formatted ? (
                <FormattedMessage blocks={message.formatted} />
              ) : (
                message.text
              )}
            </div>
            <span className="message-timestamp">
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        ))}
        {loading && (
          <div className="message bot-message loading">
            <div className="message-content">
              <span className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="input-container">
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your question here... (Shift+Enter for new line)"
          disabled={loading}
          className="message-input"
          rows="3"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !inputValue.trim()}
          className="send-button"
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};

export default ChatbotInterface;