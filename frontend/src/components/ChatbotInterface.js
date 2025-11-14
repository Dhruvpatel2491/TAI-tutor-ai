import React, { useState, useEffect, useRef, useCallback } from 'react';
import '../styles/ChatbotInterface.css';
import FormattedMessage from './FormattedMessage';
import { formatBotResponse } from '../utils/messageFormatter';

// Constants
const INITIAL_MESSAGE = {
  id: 1,
  text: 'Hello! I\'m your TAI Tutor AI. Ask me anything!',
  sender: 'bot',
  timestamp: new Date()
};
const DEFAULT_MODEL = 'llama2';
const AVAILABLE_MODELS = ['llama3-chatqa', 'llama2', 'gpt-oss:latest', 'llama3:8b'];
const DEFAULT_BACKEND_URL = 'http://147.4.122.14:5000';
const BACKEND_TIMEOUT = 5000;
const QUERY_TIMEOUT = 120000;
const HEALTH_CHECK_INTERVAL = 60000;

const ChatbotInterface = () => {
  // State - Messages
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);

  // State - User Input
  const [inputValue, setInputValue] = useState('');

  // State - Model Configuration
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL);
  const [models] = useState(AVAILABLE_MODELS);

  // State - Backend Connection
  const [backendURL, setBackendURL] = useState(DEFAULT_BACKEND_URL);
  const [backendStatus, setBackendStatus] = useState('Checking...  ');
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

      const response = await fetch(`${backendURL}/health`, {
        method: 'GET',
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      setBackendStatus(response.ok ? 'connected✅  ' : 'disconnected❌  ');
    } catch (error) {
      setBackendStatus('disconnected❌  ');
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

      const response = await fetch(`${backendURL}/query_v2`, {
        method: 'POST',
        signal: controller.signal,
        mode: 'cors',
        body: JSON.stringify({
          question: questionText,
          model: selectedModel,
          temperature: 5.0,
          max_tokens: 1024,
          stream: false,
          retrieval: { similarity_top_k: 6, rerank_top_k: 3 }
        })
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
      setBackendStatus('disconnected❌  ');
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

  return (
    <div className="chatbot-container">
      {/* Header */}
      <div className="chatbot-header">
        <h1>TAI Tutor</h1>
        <p>AI-Powered Learning Assistant</p>
        <div className="backend-status">
          <span className={`status-indicator ${backendStatus}`}></span>
          <span className="status-text">Backend: {backendStatus}</span>
          <button
            className="url-config-btn"
            onClick={() => setShowURLInput(!showURLInput)}
            aria-label="Configure backend URL"
          >
            ⚙️
          </button>
        </div>
      </div>

      {/* URL Configuration */}
      {showURLInput && (
        <div className="url-input-container">
          <input
            type="text"
            value={tempURL}
            onChange={(e) => setTempURL(e.target.value)}
            placeholder="Backend URL"
            className="url-input"
          />
          <button onClick={handleUpdateURL} className="url-confirm-btn">
            Update
          </button>
          <button onClick={() => setShowURLInput(false)} className="url-cancel-btn">
            Cancel
          </button>
        </div>
      )}

      {/* Model Selector */}
      <div className="model-selector">
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