import React, { useState, useEffect, useRef, useCallback } from 'react';
import '../styles/ChatbotInterface.css';
import FormattedMessage from './FormattedMessage';
import { formatBotResponse } from '../utils/messageFormatter';
import { DEFAULT_BACKEND_URL } from '../config';
import { apiGet, apiPost } from '../services/http';
import chatService from '../services/chatService';

// Constants
const INITIAL_MESSAGE = {
  id: 1,
  text: 'Hello! I\'m your TAI Tutor AI. Ask me anything!',
  sender: 'bot',
  timestamp: new Date()
};
const DEFAULT_MODEL = 'llama3:70b';
const AVAILABLE_MODELS = [
  'gpt-oss-safeguard:20b',
  'gpt-oss:latest',
  'ollama pull llama3.3:70b',
  'llama4:16x17b',
  'llama3.3:70b',
  'llama3:8b',
  'llama3:70b',
  'llama3-chatqa:70b',
  'codegemma:7b',
  'gemma:7b',
];

// Response configuration options
const RESPONSE_STYLES = [
  { value: 'formal', label: 'Formal' },
  { value: 'casual', label: 'Casual' },
  { value: 'technical', label: 'Technical' }
];

const RESPONSE_TYPES = [
  { value: 'direct', label: 'Direct' },
  { value: 'hinting', label: 'Hinting' },
  { value: 'socratic', label: 'Socratic' }
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

  // State - Response Configuration
  const [responseStyle, setResponseStyle] = useState('formal');
  const [responseType, setResponseType] = useState('direct');
  const [responseLength, setResponseLength] = useState('medium');

  // State - Backend Connection
  const [backendURL, setBackendURL] = useState(DEFAULT_BACKEND_URL);
  const [backendStatus, setBackendStatus] = useState(STATUS_CHECKING);
  const [rebuildInfo, setRebuildInfo] = useState(null);
  const [showURLInput, setShowURLInput] = useState(false);
  const [tempURL, setTempURL] = useState(backendURL);

  // State - Loading
  const [loading, setLoading] = useState(false);

  // State - Settings Panel
  const [showSettingsPanel, setShowSettingsPanel] = useState(false);

  // State - Chat History Sidebar
  const [showChatSidebar, setShowChatSidebar] = useState(true);
  const [chatList, setChatList] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [loadingChats, setLoadingChats] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  // Refs
  const messagesEndRef = useRef(null);

  // Build conversation history for context-aware responses
  const buildConversationHistory = useCallback(() => {
    // Get the last 10 messages (excluding the initial greeting)
    const recentMessages = messages.slice(-10);
    return recentMessages
      .filter(msg => msg.id !== 1) // Exclude initial greeting
      .map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.text
      }));
  }, [messages]);

  // Clear chat history
  const handleClearChat = useCallback(() => {
    setMessages([INITIAL_MESSAGE]);
    setCurrentChatId(null);
    setInputValue('');
  }, []);

  // Export chat history as text file
  const handleExportChat = useCallback(() => {
    const chatContent = messages.map(msg => {
      const time = msg.timestamp.toLocaleString();
      const sender = msg.sender === 'user' ? 'You' : 'TAI Tutor AI';
      return `[${time}] ${sender}:\n${msg.text}\n`;
    }).join('\n---\n\n');

    const header = `TAI Tutor AI - Chat Export\nExported on: ${new Date().toLocaleString()}\nTotal messages: ${messages.length}\n\n${'='.repeat(50)}\n\n`;
    const fullContent = header + chatContent;

    const blob = new Blob([fullContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `tai-tutor-chat-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [messages]);

  // Load chat list from backend
  const loadChatList = useCallback(async () => {
    setLoadingChats(true);
    try {
      const result = await chatService.listChats({
        includeArchived: showArchived,
        backendURL
      });
      setChatList(result.chats || []);
    } catch (error) {
      console.error('Failed to load chat list:', error);
    } finally {
      setLoadingChats(false);
    }
  }, [backendURL, showArchived]);

  // Load a specific chat conversation
  const loadChat = useCallback(async (chatId) => {
    if (!chatId) return;
    
    try {
      const chat = await chatService.getChat(chatId, { backendURL });
      setCurrentChatId(chatId);
      
      // Convert backend messages to frontend format
      const loadedMessages = chat.messages.map((msg, index) => ({
        id: index + 2, // Start from 2 (1 is reserved for initial message)
        text: msg.content,
        sender: msg.role === 'user' ? 'user' : 'bot',
        timestamp: new Date(msg.timestamp),
        formatted: msg.role === 'assistant' ? formatBotResponse(msg.content) : null
      }));
      
      // Prepend the initial greeting message
      setMessages([INITIAL_MESSAGE, ...loadedMessages]);
    } catch (error) {
      console.error('Failed to load chat:', error);
      // If chat not found, start fresh
      setCurrentChatId(null);
      setMessages([INITIAL_MESSAGE]);
    }
  }, [backendURL]);

  // Start a new chat conversation
  const handleNewChat = useCallback(async () => {
    setCurrentChatId(null);
    setMessages([INITIAL_MESSAGE]);
    setInputValue('');
    
    // Refresh the chat list
    loadChatList();
  }, [loadChatList]);

  // Delete a chat conversation
  const handleDeleteChat = useCallback(async (chatId, event) => {
    if (event) {
      event.stopPropagation();
    }
    
    if (!window.confirm('Are you sure you want to delete this conversation?')) {
      return;
    }
    
    try {
      await chatService.deleteChat(chatId, { backendURL });
      
      // If we deleted the current chat, start a new one
      if (chatId === currentChatId) {
        handleNewChat();
      }
      
      // Refresh the chat list
      loadChatList();
    } catch (error) {
      console.error('Failed to delete chat:', error);
    }
  }, [backendURL, currentChatId, handleNewChat, loadChatList]);

  // Archive/unarchive a chat conversation
  const handleArchiveChat = useCallback(async (chatId, archive, event) => {
    if (event) {
      event.stopPropagation();
    }
    
    try {
      await chatService.archiveChat(chatId, { archive, backendURL });
      loadChatList();
    } catch (error) {
      console.error('Failed to archive chat:', error);
    }
  }, [backendURL, loadChatList]);

  // Format date for display in sidebar
  const formatChatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  // Check backend connection
  const checkBackendConnection = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), BACKEND_TIMEOUT);
      const response = await apiGet(`${backendURL}/health`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (!response.ok) {
        setBackendStatus(STATUS_DISCONNECTED);
        setRebuildInfo(null);
        return;
      }
      // parse JSON health payload to surface rebuild details
      const data = await response.json().catch(() => ({}));
      // keep the raw payload for UI
      setRebuildInfo(data || null);
      const status = (data && data.status) || "ok";
      if (status === 'ok') {
        setBackendStatus(STATUS_CONNECTED);
      } else if (typeof status === 'string' && status.startsWith('rebuild')) {
        // still mark as connected but indicate rebuild in UI
        setBackendStatus(STATUS_CONNECTED);
      } else {
        setBackendStatus(STATUS_DISCONNECTED);
      }
    } catch (error) {
      // network or fetch error -> treat as disconnected
      setBackendStatus(STATUS_DISCONNECTED);
      setRebuildInfo(null);
    }
  }, [backendURL]);

  // Effects - Backend health check
  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, HEALTH_CHECK_INTERVAL);
    return () => clearInterval(interval);
  }, [checkBackendConnection]);

  // Effects - Load chat list on mount and when backend URL changes
  useEffect(() => {
    if (backendStatus === STATUS_CONNECTED) {
      loadChatList();
    }
  }, [backendStatus, loadChatList]);

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

    // If no current chat, create one first
    let activeChatId = currentChatId;
    if (!activeChatId) {
      try {
        const newChat = await chatService.createChat({ 
          title: questionText.substring(0, 50),
          backendURL 
        });
        activeChatId = newChat.chat_id;
        setCurrentChatId(activeChatId);
      } catch (error) {
        console.error('Failed to create chat session:', error);
        // Continue without chat persistence
      }
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), QUERY_TIMEOUT);

      // Build conversation history for context-awareness
      const conversationHistory = buildConversationHistory();

      // Use the new v3 endpoint with enhanced parameters
      const response = await apiPost(`${backendURL}/query_v3`, {
        signal: controller.signal,
        mode: 'cors',
        question: questionText,
        model: selectedModel,
        style: responseStyle,
        response_type: responseType,
        length: responseLength,
        conversation_history: conversationHistory,
        chat_id: activeChatId,
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
          timestamp: new Date(),
          cached: data.cached || false
        };
        setMessages(prev => [...prev, botMessage]);

        // Save messages to chat history
        if (activeChatId) {
          try {
            await chatService.addMessage(activeChatId, {
              role: 'user',
              content: questionText,
              backendURL
            });
            await chatService.addMessage(activeChatId, {
              role: 'assistant',
              content: data.answer,
              metadata: { cached: data.cached || false },
              backendURL
            });
            // Refresh chat list to update timestamps
            loadChatList();
          } catch (error) {
            console.error('Failed to save messages to chat history:', error);
          }
        }
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

  // Length slider value mapping
  const lengthToSlider = { 'short': 0, 'medium': 1, 'long': 2 };
  const sliderToLength = ['short', 'medium', 'long'];

  const handleLengthSliderChange = (e) => {
    setResponseLength(sliderToLength[parseInt(e.target.value)]);
  };

  // derive a simple status class for styling (connected/disconnected/unknown)
  const statusClass = backendStatus === STATUS_CONNECTED
    ? 'status-connected'
    : (backendStatus === STATUS_DISCONNECTED ? 'status-disconnected' : 'status-unknown');

  const statusText = backendStatus === STATUS_CONNECTED
    ? 'Connected'
    : (backendStatus === STATUS_DISCONNECTED ? 'Disconnected' : 'Checking...');

  return (    <div className='chat-combined' style={{ display: "flex" }}>
    {/* Chat History Sidebar */}
    <aside className={`chat-sidebar ${showChatSidebar ? 'sidebar-open' : 'sidebar-closed'}`}>
      <div className="sidebar-header">
        <h3>💬 Conversations</h3>
        {/* Icon shown in collapsed state and desktop stacked layout */}
        <span className="sidebar-icon" aria-hidden="true">💬</span>
        <button
          className="sidebar-toggle-btn"
          onClick={() => setShowChatSidebar(!showChatSidebar)}
          title={showChatSidebar ? "Hide sidebar" : "Show sidebar"}
        >
          <span className="sidebar-toggle-arrow">{showChatSidebar ? '◀' : '▶'}</span>
        </button>
      </div>

      {showChatSidebar && (
        <>
          <button
            className="new-chat-btn"
            onClick={handleNewChat}
            title="Start a new conversation"
          >
            ➕ New Chat
          </button>

          <div className="sidebar-filters">
            <label className="archive-toggle">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => setShowArchived(e.target.checked)}
              />
              Show archived
            </label>
          </div>

          <div className="chat-list">
            {loadingChats ? (
              <div className="chat-list-loading">Loading...</div>
            ) : chatList.length === 0 ? (
              <div className="chat-list-empty">No conversations yet</div>
            ) : (
              chatList.map((chat) => (
                <div
                  key={chat.chat_id}
                  className={`chat-list-item ${currentChatId === chat.chat_id ? 'chat-list-item-active' : ''} ${chat.archived ? 'chat-list-item-archived' : ''}`}
                  onClick={() => loadChat(chat.chat_id)}
                >
                  <div className="chat-list-item-content">
                    <span className="chat-list-item-title" title={chat.title}>
                      {chat.title || 'Untitled'}
                    </span>
                    <span className="chat-list-item-meta">
                      {formatChatDate(chat.updated_at)} • {chat.message_count} msgs
                    </span>
                  </div>
                  <div className="chat-list-item-actions">
                    <button
                      className="chat-item-action-btn"
                      onClick={(e) => handleArchiveChat(chat.chat_id, !chat.archived, e)}
                      title={chat.archived ? 'Unarchive' : 'Archive'}
                    >
                      {chat.archived ? '📤' : '📥'}
                    </button>
                    <button
                      className="chat-item-action-btn chat-item-delete-btn"
                      onClick={(e) => handleDeleteChat(chat.chat_id, e)}
                      title="Delete conversation"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </aside>

    <div className="chatbot-wrapper">
      {/* Main Chatbot Container */}
      <div className="chatbot-container">
        {/* Top: header (left) and backend/status (right) */}
        <div className="chatbot-top">
          <div className="chatbot-header-left">
            <button
              className="sidebar-mobile-toggle"
              onClick={() => setShowChatSidebar(!showChatSidebar)}
              title="Toggle conversation history"
            >
              ☰
            </button>
            <h1>TAI Tutor AI</h1>
            <p>AI-Powered Learning Assistant</p>
          </div>

          <div className="chatbot-header-side">
            {/* Chat action buttons */}
            <div className="chat-actions">
              <button
                className="chat-action-btn clear-btn"
                onClick={handleClearChat}
                title="Clear chat history"
                disabled={messages.length <= 1}
              >
                🗑️ Clear
              </button>
              <button
                className="chat-action-btn export-btn"
                onClick={handleExportChat}
                title="Export chat as text file"
                disabled={messages.length <= 1}
              >
                📥 Export
              </button>
            </div>

            <div className="backend-status">
              {/* colored dot */}
              <div>
                <span className={`status-indicator ${statusClass}`}></span>
              <span className="status-text">{statusText}</span>
              </div>
              
              {/* Show rebuild details if backend reports a rebuild in progress */}
              {rebuildInfo && typeof rebuildInfo === 'object' && (rebuildInfo.status === 'rebuild_started' || rebuildInfo.status === 'rebuild_already_in_progress') && (
                <div className="rebuild-info" title="Backend detected index/embeddings mismatch">
                  <small style={{ display: 'block' }}>
                    Rebuilding index: {rebuildInfo.new_files || rebuildInfo.current_files || 0} new document(s)
                  </small>
                </div>
              )}
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
                🔗
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
                {message.cached && (
                  <span className="cached-badge" title="Response from cache">⚡</span>
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
          <button
            className="settings-toggle-btn"
            onClick={() => setShowSettingsPanel(!showSettingsPanel)}
            title={showSettingsPanel ? "Hide settings" : "Show settings"}
            aria-label="Toggle settings panel"
          >
            ⚙️
          </button>
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

      
    </div>
      {/* Right-side collapsible settings panel - outside chatbot container */}
      <aside 
        className={`side-panel ${showSettingsPanel ? 'side-panel-open' : 'side-panel-closed'}`}
        aria-label="Chat settings panel"
        aria-hidden={!showSettingsPanel}
      >
        <div className="panel-header">
          <h3>⚙️ Chat Settings</h3>
          <button
            className="panel-close-btn"
            onClick={() => setShowSettingsPanel(false)}
            title="Close settings panel"
            aria-label="Close settings panel"
          >
            ✕
          </button>
        </div>

        <div className="panel-section">
          <label htmlFor="model-dropdown">Model</label>
          <select
            id="model-dropdown"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={loading}
            className="param-dropdown"
          >
            {models.map(model => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
        </div>

        <div className="panel-section">
          <label htmlFor="response-type-dropdown">Response Type</label>
          <select
            id="response-type-dropdown"
            value={responseType}
            onChange={(e) => setResponseType(e.target.value)}
            disabled={loading}
            className="param-dropdown"
          >
            {RESPONSE_TYPES.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
        </div>

        <div className="panel-section">
          <label htmlFor="response-style-dropdown">Style</label>
          <select
            id="response-style-dropdown"
            value={responseStyle}
            onChange={(e) => setResponseStyle(e.target.value)}
            disabled={loading}
            className="param-dropdown"
          >
            {RESPONSE_STYLES.map(style => (
              <option key={style.value} value={style.value}>{style.label}</option>
            ))}
          </select>
        </div>

        <div className="panel-section">
          <label htmlFor="response-length-slider">
            Length: <span className="length-label">{responseLength.charAt(0).toUpperCase() + responseLength.slice(1)}</span>
          </label>
          <div className="slider-container">
            <span className="slider-label-left">Short</span>
            <input
              type="range"
              id="response-length-slider"
              min="0"
              max="2"
              value={lengthToSlider[responseLength]}
              onChange={handleLengthSliderChange}
              disabled={loading}
              className="length-slider"
            />
            <span className="slider-label-right">Long</span>
          </div>
        </div>
      </aside>
 
    </div>
  );
};

export default ChatbotInterface;