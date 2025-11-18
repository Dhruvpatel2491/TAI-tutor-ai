import React from 'react';
import ChatbotInterface from '../components/ChatbotInterface';

// ChatPage now uses the existing ChatbotInterface component which integrates
// with the backend `/query_v2` endpoint and offers model selection, backend
// URL configuration, and message formatting. This keeps the chat UI
// centralized and avoids duplicating logic.

const ChatPage = () => {
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <ChatbotInterface />
    </div>
  );
};

export default ChatPage;
