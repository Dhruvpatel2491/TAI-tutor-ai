# Chat History System Documentation

This document describes the chat history feature implementation in TAI Tutor AI.

## Overview

The chat history system allows users to:
- Save and persist conversations with the AI tutor
- View past conversations in a sidebar
- Load and continue previous conversations
- Delete or archive old conversations
- Search through conversation history

## Architecture

### Backend Components

#### `chat_manager.py`

The core module for chat history management. Provides a lightweight JSON-backed store.

**Key Classes:**

- `ChatMessage`: Represents a single message in a conversation
  - `message_id`: Unique identifier
  - `role`: 'user' or 'assistant'
  - `content`: Message text
  - `timestamp`: ISO 8601 timestamp
  - `metadata`: Additional message metadata

- `ChatSession`: Represents a complete conversation
  - `chat_id`: Unique identifier
  - `user_id`: Owner's email
  - `title`: Auto-generated from first message
  - `created_at`/`updated_at`: Timestamps
  - `messages`: List of ChatMessage objects
  - `archived`: Boolean flag
  - `metadata`: Additional session metadata

- `ChatManager`: Main manager class
  - Handles CRUD operations
  - Manages file storage
  - Thread-safe operations

**Storage Structure:**
```
user_data/
└── chats/
    └── <user_email>/
        ├── <chat_id_1>.json
        ├── <chat_id_2>.json
        └── ...
```

### API Endpoints

All endpoints require authentication (unless `DISABLE_AUTH=true`).

#### Create Chat Session
```http
POST /chats
Content-Type: application/json

{
  "title": "optional title"
}

Response: 201 Created
{
  "chat_id": "uuid",
  "title": "...",
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "messages": [],
  "archived": false
}
```

#### List Chat Sessions
```http
GET /chats?include_archived=false&limit=50&offset=0

Response: 200 OK
{
  "chats": [
    {
      "chat_id": "uuid",
      "title": "...",
      "created_at": "ISO timestamp",
      "updated_at": "ISO timestamp",
      "message_count": 5,
      "archived": false
    }
  ]
}
```

#### Get Chat Session
```http
GET /chats/<chat_id>

Response: 200 OK
{
  "chat_id": "uuid",
  "title": "...",
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "messages": [
    {
      "message_id": "uuid",
      "role": "user",
      "content": "...",
      "timestamp": "ISO timestamp",
      "metadata": {}
    }
  ],
  "archived": false
}
```

#### Add Message
```http
POST /chats/<chat_id>/messages
Content-Type: application/json

{
  "role": "user" | "assistant",
  "content": "message text",
  "metadata": {}
}

Response: 201 Created
{
  "message_id": "uuid",
  "role": "...",
  "content": "...",
  "timestamp": "ISO timestamp",
  "metadata": {}
}
```

#### Delete Chat Session
```http
DELETE /chats/<chat_id>

Response: 200 OK
{
  "status": "deleted",
  "chat_id": "uuid"
}
```

#### Archive/Unarchive Chat
```http
POST /chats/<chat_id>/archive
Content-Type: application/json

{
  "archive": true | false
}

Response: 200 OK
{
  "status": "archived" | "unarchived",
  "chat_id": "uuid"
}
```

#### Update Chat Title
```http
PUT /chats/<chat_id>/title
Content-Type: application/json

{
  "title": "new title"
}

Response: 200 OK
{
  "status": "updated",
  "chat_id": "uuid",
  "title": "new title"
}
```

### Frontend Components

#### `chatService.js`

Service module for chat API calls:

```javascript
import chatService from './services/chatService';

// Create a new chat
const chat = await chatService.createChat({ title: 'My Chat' });

// List all chats
const { chats } = await chatService.listChats({ includeArchived: false });

// Get a specific chat
const chatWithMessages = await chatService.getChat(chatId);

// Add a message
await chatService.addMessage(chatId, {
  role: 'user',
  content: 'Hello!'
});

// Delete a chat
await chatService.deleteChat(chatId);

// Archive a chat
await chatService.archiveChat(chatId, { archive: true });
```

#### `ChatbotInterface.js`

The main chat interface component with integrated history sidebar.

**New State Variables:**
- `showChatSidebar`: Controls sidebar visibility
- `chatList`: Array of chat summaries
- `currentChatId`: Currently active chat ID
- `loadingChats`: Loading state for chat list
- `showArchived`: Filter for archived chats

**Key Functions:**
- `loadChatList()`: Fetches chat summaries from API
- `loadChat(chatId)`: Loads a specific conversation
- `handleNewChat()`: Starts a new conversation
- `handleDeleteChat(chatId)`: Deletes a conversation
- `handleArchiveChat(chatId, archive)`: Archives/unarchives

**Integration with sendMessage:**
1. On first message, creates new chat session
2. Stores chat_id in state
3. Saves both user and assistant messages
4. Updates chat list after each exchange

### CSS Styles

New styles in `ChatbotInterface.css`:
- `.chat-sidebar`: Left sidebar container
- `.sidebar-open`/`.sidebar-closed`: Visibility states
- `.new-chat-btn`: New conversation button
- `.chat-list`: Scrollable list container
- `.chat-list-item`: Individual chat entry
- `.chat-list-item-active`: Currently selected chat
- `.chat-list-item-archived`: Archived chat styling

## Data Flow

### Creating a New Chat

```
User types message → sendMessage()
                   ↓
         currentChatId null?
              ↓ yes
    chatService.createChat()
              ↓
    Store chat_id in state
              ↓
    Send query to /query_v3
              ↓
    Save user message to chat
              ↓
    Save assistant response to chat
              ↓
    Refresh chat list
```

### Loading a Previous Chat

```
User clicks chat in sidebar → loadChat(chatId)
                            ↓
                  chatService.getChat()
                            ↓
                  Convert messages to UI format
                            ↓
                  Set currentChatId
                            ↓
                  Update messages state
                            ↓
                  Scroll to bottom
```

## Configuration

### Environment Variables

- `CHAT_STORE_DIR`: Base directory for chat storage (default: `user_data/chats`)
- `DISABLE_AUTH`: Set to 'true' to disable authentication for testing

### Frontend Configuration

Backend URL is configured in `src/config.js`:
```javascript
export const DEFAULT_BACKEND_URL = 'http://localhost:5000';
```

## Testing

### Unit Tests

Run backend unit tests:
```bash
cd backend_test
pytest test_chat_manager.py -v
```

Tests cover:
- Message creation and serialization
- Session management
- CRUD operations
- Edge cases (unicode, large messages, etc.)
- User isolation

### Integration Tests

Run API integration tests:
```bash
cd backend_test
pytest test_chat_api_integration.py -v
```

Tests cover:
- All API endpoints
- Authentication
- Error handling
- Data integrity
- Complete conversation flows

## Security Considerations

1. **User Isolation**: Users can only access their own chats
2. **Authentication**: All endpoints require valid JWT (when auth enabled)
3. **Input Validation**: Role must be 'user' or 'assistant'
4. **File Path Sanitization**: User IDs are sanitized for filesystem safety

## Future Enhancements

- [ ] Full-text search across conversations
- [ ] Export conversations to various formats
- [ ] Share conversations with other users
- [ ] Chat categorization/tagging
- [ ] Conversation summarization
- [ ] Message editing/deletion
