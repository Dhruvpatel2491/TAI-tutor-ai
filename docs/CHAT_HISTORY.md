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

#### `backend/modules/chat.py`

The core module for chat history management. This repo stores chat sessions as per-user JSON files on disk under `user_data/chats/`. The `backend/modules/chat.py` module provides high-level CRUD and file management functions and is the authoritative implementation for session lifecycle.

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

```md
user_data/
└── chats/
  └── <user_email>/
    ├── <chat_id_1>.json
    ├── <chat_id_2>.json
    └── ...
```

### API Endpoints

All endpoints require authentication (unless `DISABLE_AUTH=true` in environment).

#### Create Chat Session

```http
POST /chats
Content-Type: application/json

{
  "title": "optional title"
}

Response: 201 Created

```json
{
  "chat_id": "uuid",
  "title": "...",
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "messages": [],
  "archived": false
}
```

#### Get Chat Session

```http
GET /chats/<chat_id>

Response: 200 OK

```json
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

```json
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

```json
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

```json
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

```json
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
### API Endpoints

All endpoints require authentication (unless `DISABLE_AUTH=true` in environment).

#### Create Chat Session

```http
POST /chats
Content-Type: application/json

{ "title": "optional title" }
```

Response: 201 Created

```json
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
```

Response: 200 OK

```json
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

## Future Enhancements

- [ ] Full-text search across conversations
- [ ] Export conversations to various formats
- [ ] Share conversations with other users
- [ ] Chat categorization/tagging
- [ ] Conversation summarization
- [ ] Message editing/deletion
