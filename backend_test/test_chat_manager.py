"""
Unit tests for chat_manager.py

This module tests all functionality of the chat history management system including:
- Creating chat sessions
- Adding messages
- Retrieving chat histories
- Listing past conversations
- Deleting and archiving conversations
- Data integrity and edge cases
"""

import os
import json
import pytest
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Import the chat module from new backend structure
import sys
# Add both project root and backend directory to path
project_root = os.path.join(os.path.dirname(__file__), '..')
backend_dir = os.path.join(project_root, 'backend')
sys.path.insert(0, project_root)
sys.path.insert(0, backend_dir)

from modules.chat import (
    ChatMessage,
    ChatSession,
    ChatManager,
    get_chat_manager,
    create_chat,
    get_chat,
    add_message,
    list_chats,
    delete_chat,
    archive_chat
)


class TestChatMessage:
    """Tests for the ChatMessage class."""
    
    def test_create_message_with_defaults(self):
        """Test creating a message with default values."""
        msg = ChatMessage(role="user", content="Hello, world!")
        
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.message_id is not None
        assert msg.timestamp is not None
        assert msg.metadata == {}
    
    def test_create_message_with_all_fields(self):
        """Test creating a message with all fields specified."""
        msg = ChatMessage(
            role="assistant",
            content="How can I help?",
            message_id="test-msg-id",
            timestamp="2024-01-01T00:00:00+00:00",
            metadata={"model": "test-model"}
        )
        
        assert msg.message_id == "test-msg-id"
        assert msg.role == "assistant"
        assert msg.content == "How can I help?"
        assert msg.timestamp == "2024-01-01T00:00:00+00:00"
        assert msg.metadata == {"model": "test-model"}
    
    def test_message_to_dict(self):
        """Test serializing a message to dictionary."""
        msg = ChatMessage(
            role="user",
            content="Test message",
            message_id="msg-123"
        )
        data = msg.to_dict()
        
        assert data["message_id"] == "msg-123"
        assert data["role"] == "user"
        assert data["content"] == "Test message"
        assert "timestamp" in data
        assert "metadata" in data
    
    def test_message_from_dict(self):
        """Test deserializing a message from dictionary."""
        data = {
            "message_id": "msg-456",
            "role": "assistant",
            "content": "Response text",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "metadata": {"cached": True}
        }
        msg = ChatMessage.from_dict(data)
        
        assert msg.message_id == "msg-456"
        assert msg.role == "assistant"
        assert msg.content == "Response text"
        assert msg.timestamp == "2024-01-01T12:00:00+00:00"
        assert msg.metadata == {"cached": True}


class TestChatSession:
    """Tests for the ChatSession class."""
    
    def test_create_session_with_defaults(self):
        """Test creating a session with default values."""
        session = ChatSession(user_id="test@test.com")
        
        assert session.chat_id is not None
        assert session.user_id == "test@test.com"
        assert session.title == "New Conversation"
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.messages == []
        assert session.archived is False
        assert session.metadata == {}
    
    def test_create_session_with_all_fields(self):
        """Test creating a session with all fields specified."""
        session = ChatSession(
            chat_id="chat-123",
            user_id="user@example.com",
            title="Python Questions",
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T01:00:00+00:00",
            archived=True,
            metadata={"topic": "python"}
        )
        
        assert session.chat_id == "chat-123"
        assert session.title == "Python Questions"
        assert session.archived is True
    
    def test_add_message_to_session(self):
        """Test adding a message to a session."""
        session = ChatSession(user_id="test@test.com")
        msg = session.add_message("user", "Hello!")
        
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello!"
        assert msg.message_id is not None
    
    def test_add_message_updates_title(self):
        """Test that first user message updates the title."""
        session = ChatSession(user_id="test@test.com")
        assert session.title == "New Conversation"
        
        session.add_message("user", "How do I learn Python programming?")
        
        assert session.title == "How do I learn Python programming?"
    
    def test_add_message_truncates_long_title(self):
        """Test that long messages are truncated in title."""
        session = ChatSession(user_id="test@test.com")
        long_message = "A" * 100
        
        session.add_message("user", long_message)
        
        assert len(session.title) <= 53  # 50 chars + "..."
        assert session.title.endswith("...")
    
    def test_session_to_dict(self):
        """Test serializing a session to dictionary."""
        session = ChatSession(
            chat_id="chat-789",
            user_id="test@test.com",
            title="Test Session"
        )
        session.add_message("user", "Question")
        session.add_message("assistant", "Answer")
        
        data = session.to_dict()
        
        assert data["chat_id"] == "chat-789"
        assert data["title"] == "Test Session"
        assert len(data["messages"]) == 2
    
    def test_session_to_summary(self):
        """Test getting a lightweight summary of a session."""
        session = ChatSession(
            chat_id="chat-999",
            user_id="test@test.com",
            title="Summary Test"
        )
        session.add_message("user", "Q1")
        session.add_message("assistant", "A1")
        
        summary = session.to_summary()
        
        assert summary["chat_id"] == "chat-999"
        assert summary["title"] == "Summary Test"
        assert summary["message_count"] == 2
        assert "messages" not in summary
    
    def test_session_from_dict(self):
        """Test deserializing a session from dictionary."""
        data = {
            "chat_id": "chat-abc",
            "user_id": "user@test.com",
            "title": "Loaded Session",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T01:00:00+00:00",
            "messages": [
                {"message_id": "m1", "role": "user", "content": "Hi", "timestamp": "2024-01-01T00:00:00+00:00", "metadata": {}}
            ],
            "archived": False,
            "metadata": {}
        }
        session = ChatSession.from_dict(data)
        
        assert session.chat_id == "chat-abc"
        assert session.title == "Loaded Session"
        assert len(session.messages) == 1


class TestChatManager:
    """Tests for the ChatManager class."""
    
    @pytest.fixture
    def temp_store_dir(self):
        """Create a temporary directory for test storage."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def manager(self, temp_store_dir):
        """Create a ChatManager with temporary storage."""
        return ChatManager(store_dir=temp_store_dir)
    
    def test_create_chat(self, manager):
        """Test creating a new chat session."""
        session = manager.create_chat(user_id="test@test.com", title="Test Chat")
        
        assert session is not None
        assert session.chat_id is not None
        assert session.title == "Test Chat"
        assert session.user_id == "test@test.com"
    
    def test_get_chat(self, manager):
        """Test retrieving a chat session."""
        created = manager.create_chat(user_id="test@test.com", title="Get Test")
        
        retrieved = manager.get_chat("test@test.com", created.chat_id)
        
        assert retrieved is not None
        assert retrieved.chat_id == created.chat_id
        assert retrieved.title == "Get Test"
    
    def test_get_chat_not_found(self, manager):
        """Test retrieving a non-existent chat returns None."""
        result = manager.get_chat("test@test.com", "nonexistent-id")
        assert result is None
    
    def test_add_message(self, manager):
        """Test adding a message to a chat."""
        session = manager.create_chat(user_id="test@test.com")
        
        message = manager.add_message(
            user_id="test@test.com",
            chat_id=session.chat_id,
            role="user",
            content="Test message"
        )
        
        assert message is not None
        assert message.role == "user"
        assert message.content == "Test message"
        
        # Verify persistence
        retrieved = manager.get_chat("test@test.com", session.chat_id)
        assert len(retrieved.messages) == 1
    
    def test_add_message_pair(self, manager):
        """Test adding both user and assistant messages."""
        session = manager.create_chat(user_id="test@test.com")
        
        result = manager.add_message_pair(
            user_id="test@test.com",
            chat_id=session.chat_id,
            user_content="Question?",
            assistant_content="Answer!"
        )
        
        assert result is not None
        user_msg, assistant_msg = result
        assert user_msg.role == "user"
        assert assistant_msg.role == "assistant"
        
        # Verify persistence
        retrieved = manager.get_chat("test@test.com", session.chat_id)
        assert len(retrieved.messages) == 2
    
    def test_list_chats(self, manager):
        """Test listing chat sessions."""
        manager.create_chat(user_id="test@test.com", title="Chat 1")
        manager.create_chat(user_id="test@test.com", title="Chat 2")
        manager.create_chat(user_id="test@test.com", title="Chat 3")
        
        chats = manager.list_chats("test@test.com")
        
        assert len(chats) == 3
    
    def test_list_chats_sorted_by_updated(self, manager):
        """Test that chats are sorted by updated_at descending."""
        chat1 = manager.create_chat(user_id="test@test.com", title="First")
        chat2 = manager.create_chat(user_id="test@test.com", title="Second")
        
        # Update the first chat to make it more recent
        manager.add_message("test@test.com", chat1.chat_id, "user", "Update")
        
        chats = manager.list_chats("test@test.com")
        
        assert chats[0]["title"] == "Update"  # Title gets updated from first user msg
    
    def test_list_chats_excludes_archived(self, manager):
        """Test that archived chats are excluded by default."""
        manager.create_chat(user_id="test@test.com", title="Active")
        archived = manager.create_chat(user_id="test@test.com", title="Archived")
        manager.archive_chat("test@test.com", archived.chat_id, True)
        
        chats = manager.list_chats("test@test.com", include_archived=False)
        
        assert len(chats) == 1
        assert chats[0]["title"] == "Active"
    
    def test_list_chats_includes_archived(self, manager):
        """Test including archived chats in listing."""
        manager.create_chat(user_id="test@test.com", title="Active")
        archived = manager.create_chat(user_id="test@test.com", title="Archived")
        manager.archive_chat("test@test.com", archived.chat_id, True)
        
        chats = manager.list_chats("test@test.com", include_archived=True)
        
        assert len(chats) == 2
    
    def test_list_chats_pagination(self, manager):
        """Test pagination of chat listing."""
        for i in range(10):
            manager.create_chat(user_id="test@test.com", title=f"Chat {i}")
        
        # Get first 5
        page1 = manager.list_chats("test@test.com", limit=5, offset=0)
        assert len(page1) == 5
        
        # Get next 5
        page2 = manager.list_chats("test@test.com", limit=5, offset=5)
        assert len(page2) == 5
        
        # Verify no overlap
        ids1 = {c["chat_id"] for c in page1}
        ids2 = {c["chat_id"] for c in page2}
        assert len(ids1 & ids2) == 0
    
    def test_delete_chat(self, manager):
        """Test deleting a chat session."""
        session = manager.create_chat(user_id="test@test.com", title="To Delete")
        
        result = manager.delete_chat("test@test.com", session.chat_id)
        
        assert result is True
        assert manager.get_chat("test@test.com", session.chat_id) is None
    
    def test_delete_chat_not_found(self, manager):
        """Test deleting a non-existent chat."""
        result = manager.delete_chat("test@test.com", "nonexistent")
        assert result is False
    
    def test_archive_chat(self, manager):
        """Test archiving a chat session."""
        session = manager.create_chat(user_id="test@test.com", title="To Archive")
        
        result = manager.archive_chat("test@test.com", session.chat_id, True)
        
        assert result is True
        retrieved = manager.get_chat("test@test.com", session.chat_id)
        assert retrieved.archived is True
    
    def test_unarchive_chat(self, manager):
        """Test unarchiving a chat session."""
        session = manager.create_chat(user_id="test@test.com")
        manager.archive_chat("test@test.com", session.chat_id, True)
        
        result = manager.archive_chat("test@test.com", session.chat_id, False)
        
        assert result is True
        retrieved = manager.get_chat("test@test.com", session.chat_id)
        assert retrieved.archived is False
    
    def test_update_chat_title(self, manager):
        """Test updating a chat title."""
        session = manager.create_chat(user_id="test@test.com", title="Old Title")
        
        result = manager.update_chat_title("test@test.com", session.chat_id, "New Title")
        
        assert result is True
        retrieved = manager.get_chat("test@test.com", session.chat_id)
        assert retrieved.title == "New Title"
    
    def test_get_or_create_chat_existing(self, manager):
        """Test get_or_create returns existing chat."""
        created = manager.create_chat(user_id="test@test.com", title="Existing")
        
        result = manager.get_or_create_chat("test@test.com", chat_id=created.chat_id)
        
        assert result.chat_id == created.chat_id
    
    def test_get_or_create_chat_new(self, manager):
        """Test get_or_create creates new chat when not found."""
        result = manager.get_or_create_chat("test@test.com", title="New Chat")
        
        assert result is not None
        assert result.title == "New Chat"
    
    def test_user_isolation(self, manager):
        """Test that users can only access their own chats."""
        session1 = manager.create_chat(user_id="user1@test.com", title="User 1 Chat")
        session2 = manager.create_chat(user_id="user2@test.com", title="User 2 Chat")
        
        # User 1 should not see User 2's chat
        assert manager.get_chat("user1@test.com", session2.chat_id) is None
        
        # User 2 should not see User 1's chat
        assert manager.get_chat("user2@test.com", session1.chat_id) is None
        
        # Each user sees only their chats
        user1_chats = manager.list_chats("user1@test.com")
        user2_chats = manager.list_chats("user2@test.com")
        
        assert len(user1_chats) == 1
        assert len(user2_chats) == 1
        assert user1_chats[0]["chat_id"] != user2_chats[0]["chat_id"]


class TestChatManagerEdgeCases:
    """Edge case tests for ChatManager."""
    
    @pytest.fixture
    def temp_store_dir(self):
        """Create a temporary directory for test storage."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def manager(self, temp_store_dir):
        """Create a ChatManager with temporary storage."""
        return ChatManager(store_dir=temp_store_dir)
    
    def test_special_characters_in_user_id(self, manager):
        """Test handling of special characters in user ID."""
        user_id = "test.user+special@sub.domain.com"
        session = manager.create_chat(user_id=user_id, title="Special Chars")
        
        assert session is not None
        retrieved = manager.get_chat(user_id, session.chat_id)
        assert retrieved is not None
    
    def test_empty_message_content(self, manager):
        """Test adding message with empty content."""
        session = manager.create_chat(user_id="test@test.com")
        
        message = manager.add_message("test@test.com", session.chat_id, "user", "")
        
        assert message is not None
        assert message.content == ""
    
    def test_unicode_content(self, manager):
        """Test handling of unicode in messages."""
        session = manager.create_chat(user_id="test@test.com")
        
        message = manager.add_message(
            "test@test.com",
            session.chat_id,
            "user",
            "Hello 你好 こんにちは 🎉"
        )
        
        assert message.content == "Hello 你好 こんにちは 🎉"
        
        retrieved = manager.get_chat("test@test.com", session.chat_id)
        assert retrieved.messages[0].content == "Hello 你好 こんにちは 🎉"
    
    def test_very_long_message(self, manager):
        """Test handling of very long messages."""
        session = manager.create_chat(user_id="test@test.com")
        long_content = "A" * 100000  # 100KB message
        
        message = manager.add_message("test@test.com", session.chat_id, "user", long_content)
        
        assert len(message.content) == 100000
    
    def test_many_messages_in_chat(self, manager):
        """Test chat with many messages."""
        session = manager.create_chat(user_id="test@test.com")
        
        for i in range(100):
            manager.add_message("test@test.com", session.chat_id, "user", f"Message {i}")
            manager.add_message("test@test.com", session.chat_id, "assistant", f"Response {i}")
        
        retrieved = manager.get_chat("test@test.com", session.chat_id)
        assert len(retrieved.messages) == 200
    
    def test_concurrent_access_safety(self, manager):
        """Test basic thread safety (not exhaustive)."""
        import threading
        
        session = manager.create_chat(user_id="test@test.com")
        errors = []
        
        def add_messages():
            try:
                for i in range(10):
                    manager.add_message("test@test.com", session.chat_id, "user", f"Thread msg {i}")
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=add_messages) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        retrieved = manager.get_chat("test@test.com", session.chat_id)
        assert len(retrieved.messages) == 50  # 5 threads * 10 messages


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    @pytest.fixture
    def temp_store_dir(self):
        """Create a temporary directory for test storage."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture(autouse=True)
    def reset_global_manager(self, temp_store_dir):
        """Reset the global manager for each test."""
        from modules import chat as cm
        cm._chat_manager = ChatManager(store_dir=temp_store_dir)
        yield
        cm._chat_manager = None
    
    def test_create_chat_convenience(self):
        """Test the create_chat convenience function."""
        session = create_chat("test@test.com", "Convenience Test")
        assert session is not None
        assert session.title == "Convenience Test"
    
    def test_get_chat_convenience(self):
        """Test the get_chat convenience function."""
        created = create_chat("test@test.com", "Get Test")
        retrieved = get_chat("test@test.com", created.chat_id)
        assert retrieved is not None
        assert retrieved.chat_id == created.chat_id
    
    def test_add_message_convenience(self):
        """Test the add_message convenience function."""
        session = create_chat("test@test.com")
        message = add_message("test@test.com", session.chat_id, "user", "Hello")
        assert message is not None
        assert message.content == "Hello"
    
    def test_list_chats_convenience(self):
        """Test the list_chats convenience function."""
        create_chat("test@test.com", "Chat 1")
        create_chat("test@test.com", "Chat 2")
        
        chats = list_chats("test@test.com")
        assert len(chats) == 2
    
    def test_delete_chat_convenience(self):
        """Test the delete_chat convenience function."""
        session = create_chat("test@test.com")
        result = delete_chat("test@test.com", session.chat_id)
        assert result is True
    
    def test_archive_chat_convenience(self):
        """Test the archive_chat convenience function."""
        session = create_chat("test@test.com")
        result = archive_chat("test@test.com", session.chat_id, True)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
