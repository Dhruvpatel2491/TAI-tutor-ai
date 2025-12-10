"""
Chat History Manager for TAI Tutor AI.

This module provides a lightweight JSON-backed store for chat history management.
It handles:
- Creating new chat sessions
- Appending messages to existing chats
- Retrieving chat histories
- Listing past conversations
- Deleting or archiving conversations

Data is persisted in user_data/chats/<user_email>/<chat_id>.json
"""

import os
import json
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("backend.chat_manager")

# Default storage directory for chat data
DEFAULT_CHAT_STORE_DIR = os.environ.get(
    "CHAT_STORE_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_data", "chats")
)


class ChatMessage:
    """Represents a single message in a chat conversation."""
    
    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message_id = message_id or str(uuid.uuid4())
        self.role = role  # 'user' or 'assistant'
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary."""
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Deserialize message from dictionary."""
        return cls(
            message_id=data.get("message_id"),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {})
        )


class ChatSession:
    """Represents a chat session with multiple messages."""
    
    def __init__(
        self,
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        messages: Optional[List[ChatMessage]] = None,
        archived: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.chat_id = chat_id or str(uuid.uuid4())
        self.user_id = user_id
        self.title = title or "New Conversation"
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.updated_at = updated_at or self.created_at
        self.messages = messages or []
        self.archived = archived
        self.metadata = metadata or {}
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        """Add a new message to the chat session."""
        message = ChatMessage(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Update title based on first user message if still default
        if self.title == "New Conversation" and role == "user" and content:
            # Use first 50 chars of first user message as title
            self.title = content[:50] + ("..." if len(content) > 50 else "")
        
        return message
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [msg.to_dict() for msg in self.messages],
            "archived": self.archived,
            "metadata": self.metadata
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Return a lightweight summary for listing (no message content)."""
        return {
            "chat_id": self.chat_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": len(self.messages),
            "archived": self.archived
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSession":
        """Deserialize session from dictionary."""
        messages = [ChatMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            chat_id=data.get("chat_id"),
            user_id=data.get("user_id"),
            title=data.get("title"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            messages=messages,
            archived=data.get("archived", False),
            metadata=data.get("metadata", {})
        )


class ChatManager:
    """
    Manages chat history storage and retrieval.
    
    Uses a JSON-backed file store with one file per chat session:
    <store_dir>/<user_id>/<chat_id>.json
    """
    
    def __init__(self, store_dir: Optional[str] = None):
        self.store_dir = Path(store_dir or DEFAULT_CHAT_STORE_DIR)
        self._lock = threading.Lock()
        # Ensure base directory exists
        self.store_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ChatManager initialized with store_dir: {self.store_dir}")
    
    def _get_user_dir(self, user_id: str) -> Path:
        """Get the directory for a specific user's chats."""
        # Sanitize user_id for filesystem (replace @ and . with safe chars)
        safe_user_id = user_id.replace("@", "__at__").replace(".", "__dot__")
        return self.store_dir / safe_user_id
    
    def _get_chat_path(self, user_id: str, chat_id: str) -> Path:
        """Get the file path for a specific chat."""
        return self._get_user_dir(user_id) / f"{chat_id}.json"
    
    def _save_session(self, session: ChatSession) -> bool:
        """Save a chat session to disk."""
        if not session.user_id:
            logger.error("Cannot save session without user_id")
            return False
        
        try:
            user_dir = self._get_user_dir(session.user_id)
            user_dir.mkdir(parents=True, exist_ok=True)
            
            chat_path = self._get_chat_path(session.user_id, session.chat_id)
            
            # Write atomically using temp file
            tmp_path = chat_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.replace(tmp_path, chat_path)
            logger.debug(f"Saved chat session {session.chat_id} for user {session.user_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to save chat session: {e}")
            return False
    
    def _load_session(self, user_id: str, chat_id: str) -> Optional[ChatSession]:
        """Load a chat session from disk."""
        chat_path = self._get_chat_path(user_id, chat_id)
        
        if not chat_path.exists():
            logger.debug(f"Chat session not found: {chat_path}")
            return None
        
        try:
            with open(chat_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ChatSession.from_dict(data)
        except Exception as e:
            logger.exception(f"Failed to load chat session: {e}")
            return None
    
    def create_chat(
        self,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ChatSession]:
        """
        Create a new chat session.
        
        Args:
            user_id: The user's identifier (usually email)
            title: Optional title for the chat
            metadata: Optional metadata dict
            
        Returns:
            The created ChatSession or None on error
        """
        with self._lock:
            session = ChatSession(
                user_id=user_id,
                title=title,
                metadata=metadata
            )
            
            if self._save_session(session):
                logger.info(f"Created new chat {session.chat_id} for user {user_id}")
                return session
            return None
    
    def get_chat(self, user_id: str, chat_id: str) -> Optional[ChatSession]:
        """
        Retrieve a chat session.
        
        Args:
            user_id: The user's identifier
            chat_id: The chat session ID
            
        Returns:
            The ChatSession or None if not found
        """
        with self._lock:
            return self._load_session(user_id, chat_id)
    
    def add_message(
        self,
        user_id: str,
        chat_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ChatMessage]:
        """
        Add a message to an existing chat session.
        
        Args:
            user_id: The user's identifier
            chat_id: The chat session ID
            role: 'user' or 'assistant'
            content: The message content
            metadata: Optional message metadata
            
        Returns:
            The created ChatMessage or None on error
        """
        with self._lock:
            session = self._load_session(user_id, chat_id)
            if not session:
                logger.warning(f"Chat session not found: {chat_id}")
                return None
            
            message = session.add_message(role, content, metadata)
            
            if self._save_session(session):
                return message
            return None
    
    def add_message_pair(
        self,
        user_id: str,
        chat_id: str,
        user_content: str,
        assistant_content: str,
        user_metadata: Optional[Dict[str, Any]] = None,
        assistant_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[tuple]:
        """
        Add both user and assistant messages to a chat session.
        
        Args:
            user_id: The user's identifier
            chat_id: The chat session ID
            user_content: The user's message
            assistant_content: The assistant's response
            user_metadata: Optional metadata for user message
            assistant_metadata: Optional metadata for assistant message
            
        Returns:
            Tuple of (user_message, assistant_message) or None on error
        """
        with self._lock:
            session = self._load_session(user_id, chat_id)
            if not session:
                logger.warning(f"Chat session not found: {chat_id}")
                return None
            
            user_msg = session.add_message("user", user_content, user_metadata)
            assistant_msg = session.add_message("assistant", assistant_content, assistant_metadata)
            
            if self._save_session(session):
                return (user_msg, assistant_msg)
            return None
    
    def list_chats(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all chat sessions for a user.
        
        Args:
            user_id: The user's identifier
            include_archived: Whether to include archived chats
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of chat summaries sorted by updated_at descending
        """
        with self._lock:
            user_dir = self._get_user_dir(user_id)
            
            if not user_dir.exists():
                return []
            
            summaries = []
            try:
                for chat_file in user_dir.glob("*.json"):
                    try:
                        with open(chat_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        if not include_archived and data.get("archived", False):
                            continue
                        # Derive a display title: prefer the most recent user message content if present
                        display_title = data.get("title", "Untitled")
                        messages = data.get("messages", []) or []
                        # Look for the last user message to use as a compact display title
                        for m in reversed(messages):
                            if m.get("role") == "user" and m.get("content"):
                                content = m.get("content")
                                display_title = content[:50] + ("..." if len(content) > 50 else "")
                                break

                        summaries.append({
                            "chat_id": data.get("chat_id"),
                            "title": display_title,
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "message_count": len(messages),
                            "archived": data.get("archived", False)
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read chat file {chat_file}: {e}")
                        continue
            except Exception as e:
                logger.exception(f"Failed to list chats for user {user_id}: {e}")
                return []
            
            # Sort by updated_at descending (most recent first)
            summaries.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
            # Apply pagination
            if offset:
                summaries = summaries[offset:]
            if limit:
                summaries = summaries[:limit]
            
            return summaries
    
    def delete_chat(self, user_id: str, chat_id: str) -> bool:
        """
        Delete a chat session.
        
        Args:
            user_id: The user's identifier
            chat_id: The chat session ID
            
        Returns:
            True if deleted, False otherwise
        """
        with self._lock:
            chat_path = self._get_chat_path(user_id, chat_id)
            
            if not chat_path.exists():
                logger.warning(f"Chat session not found for deletion: {chat_id}")
                return False
            
            try:
                os.remove(chat_path)
                logger.info(f"Deleted chat {chat_id} for user {user_id}")
                return True
            except Exception as e:
                logger.exception(f"Failed to delete chat: {e}")
                return False
    
    def archive_chat(self, user_id: str, chat_id: str, archive: bool = True) -> bool:
        """
        Archive or unarchive a chat session.
        
        Args:
            user_id: The user's identifier
            chat_id: The chat session ID
            archive: True to archive, False to unarchive
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            session = self._load_session(user_id, chat_id)
            if not session:
                logger.warning(f"Chat session not found for archiving: {chat_id}")
                return False
            
            session.archived = archive
            session.updated_at = datetime.now(timezone.utc).isoformat()
            
            if self._save_session(session):
                logger.info(f"{'Archived' if archive else 'Unarchived'} chat {chat_id}")
                return True
            return False
    
    def update_chat_title(self, user_id: str, chat_id: str, title: str) -> bool:
        """
        Update the title of a chat session.
        
        Args:
            user_id: The user's identifier
            chat_id: The chat session ID
            title: The new title
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            session = self._load_session(user_id, chat_id)
            if not session:
                logger.warning(f"Chat session not found for title update: {chat_id}")
                return False
            
            session.title = title
            session.updated_at = datetime.now(timezone.utc).isoformat()
            
            return self._save_session(session)
    
    def get_or_create_chat(
        self,
        user_id: str,
        chat_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[ChatSession]:
        """
        Get an existing chat or create a new one.
        
        If chat_id is provided, attempts to load that chat.
        If not found or not provided, creates a new chat.
        
        Args:
            user_id: The user's identifier
            chat_id: Optional existing chat ID
            title: Optional title for new chat
            
        Returns:
            The ChatSession or None on error
        """
        with self._lock:
            if chat_id:
                session = self._load_session(user_id, chat_id)
                if session:
                    return session
                logger.debug(f"Chat {chat_id} not found, creating new")
            
            # Create new session outside the lock (create_chat has its own lock)
        
        return self.create_chat(user_id, title)


# Global singleton instance
_chat_manager: Optional[ChatManager] = None
_manager_lock = threading.Lock()


def get_chat_manager(store_dir: Optional[str] = None) -> ChatManager:
    """Get the global ChatManager singleton."""
    global _chat_manager
    with _manager_lock:
        if _chat_manager is None:
            _chat_manager = ChatManager(store_dir)
        return _chat_manager


# Convenience functions that use the global manager
def create_chat(user_id: str, title: Optional[str] = None) -> Optional[ChatSession]:
    """Create a new chat session."""
    return get_chat_manager().create_chat(user_id, title)


def get_chat(user_id: str, chat_id: str) -> Optional[ChatSession]:
    """Get a chat session."""
    return get_chat_manager().get_chat(user_id, chat_id)


def add_message(user_id: str, chat_id: str, role: str, content: str) -> Optional[ChatMessage]:
    """Add a message to a chat."""
    return get_chat_manager().add_message(user_id, chat_id, role, content)


def list_chats(user_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
    """List chats for a user."""
    return get_chat_manager().list_chats(user_id, include_archived)


def delete_chat(user_id: str, chat_id: str) -> bool:
    """Delete a chat."""
    return get_chat_manager().delete_chat(user_id, chat_id)


def archive_chat(user_id: str, chat_id: str, archive: bool = True) -> bool:
    """Archive/unarchive a chat."""
    return get_chat_manager().archive_chat(user_id, chat_id, archive)
