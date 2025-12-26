"""
Integration tests for chat history API endpoints.

These tests verify the end-to-end functionality of chat history management
through the Flask API endpoints, testing:
- Creating chat sessions via API
- Adding messages via API
- Retrieving chat histories via API
- Listing conversations via API
- Deleting and archiving via API
- Authentication integration
"""

import os
import json
import pytest
import tempfile
import shutil
from pathlib import Path

# Set auth disabled BEFORE importing backend modules
os.environ['DISABLE_AUTH'] = 'true'

# Add backend to path
import sys
project_root = os.path.join(os.path.dirname(__file__), '..')
backend_dir = os.path.join(project_root, 'backend')
sys.path.insert(0, project_root)
sys.path.insert(0, backend_dir)

# Import Flask app and test client from new backend structure
from server_v2 import app
from modules import chat as cm

try:
    from modules import chat as bcm  # type: ignore
except Exception:
    bcm = None


@pytest.fixture
def temp_chat_store():
    """Create a temporary directory for chat storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(temp_chat_store):
    """Create a test client with temporary storage."""
    # Reset the global chat manager with temp directory
    cm._chat_manager = cm.ChatManager(store_dir=temp_chat_store)
    if bcm is not None:
        bcm._chat_manager = cm._chat_manager
    
    # Set up Flask test client
    app.config['TESTING'] = True
    
    # Disable auth for testing
    os.environ['DISABLE_AUTH'] = 'true'
    
    with app.test_client() as client:
        yield client
    
    # Cleanup
    cm._chat_manager = None
    if bcm is not None:
        bcm._chat_manager = None
    os.environ.pop('DISABLE_AUTH', None)


@pytest.fixture
def auth_client(temp_chat_store):
    """Create a test client with authentication enabled."""
    cm._chat_manager = cm.ChatManager(store_dir=temp_chat_store)
    if bcm is not None:
        bcm._chat_manager = cm._chat_manager
    app.config['TESTING'] = True
    
    # Enable auth
    os.environ['DISABLE_AUTH'] = 'false'
    
    with app.test_client() as client:
        yield client
    
    cm._chat_manager = None
    if bcm is not None:
        bcm._chat_manager = None
    os.environ.pop('DISABLE_AUTH', None)


class TestChatAPIBasic:
    """Basic API endpoint tests."""
    
    def test_create_chat(self, client):
        """Test creating a new chat via API."""
        response = client.post(
            '/chats',
            json={'title': 'Test Chat', 'user_id': 'test@test.com'},
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'chat_id' in data
        assert data['title'] == 'Test Chat'
    
    def test_create_chat_default_title(self, client):
        """Test creating a chat with default title."""
        response = client.post(
            '/chats',
            json={'user_id': 'test@test.com'},
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['title'] == 'New Conversation'
    
    def test_list_chats_empty(self, client):
        """Test listing chats when none exist."""
        response = client.get('/chats?user_id=test@test.com')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'chats' in data
        assert len(data['chats']) == 0
    
    def test_list_chats_with_data(self, client):
        """Test listing chats after creating some."""
        # Create chats
        client.post('/chats', json={'title': 'Chat 1', 'user_id': 'test@test.com'})
        client.post('/chats', json={'title': 'Chat 2', 'user_id': 'test@test.com'})
        
        response = client.get('/chats?user_id=test@test.com')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['chats']) == 2
    
    def test_get_chat(self, client):
        """Test retrieving a specific chat."""
        # Create chat
        create_response = client.post('/chats', json={'title': 'Get Test', 'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        
        response = client.get(f'/chats/{chat_id}?user_id=test@test.com')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['chat_id'] == chat_id
        assert data['title'] == 'Get Test'
    
    def test_get_chat_not_found(self, client):
        """Test retrieving a non-existent chat."""
        response = client.get('/chats/nonexistent?user_id=test@test.com')
        
        assert response.status_code == 404
    
    def test_add_message(self, client):
        """Test adding a message to a chat."""
        # Create chat
        create_response = client.post('/chats', json={'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        
        # Add message
        response = client.post(
            f'/chats/{chat_id}/messages',
            json={
                'role': 'user',
                'content': 'Hello!',
                'user_id': 'test@test.com'
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['role'] == 'user'
        assert data['content'] == 'Hello!'
    
    def test_add_message_invalid_role(self, client):
        """Test adding a message with invalid role."""
        create_response = client.post('/chats', json={'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        
        response = client.post(
            f'/chats/{chat_id}/messages',
            json={
                'role': 'invalid',
                'content': 'Test',
                'user_id': 'test@test.com'
            }
        )
        
        assert response.status_code == 400
    
    def test_delete_chat(self, client):
        """Test deleting a chat."""
        # Create chat
        create_response = client.post('/chats', json={'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        
        # Delete
        response = client.delete(f'/chats/{chat_id}?user_id=test@test.com')
        
        assert response.status_code == 200
        
        # Verify deleted
        get_response = client.get(f'/chats/{chat_id}?user_id=test@test.com')
        assert get_response.status_code == 404
    
    def test_delete_chat_not_found(self, client):
        """Test deleting a non-existent chat."""
        response = client.delete('/chats/nonexistent?user_id=test@test.com')
        assert response.status_code == 404
    
    def test_archive_chat(self, client):
        """Test archiving a chat."""
        # Create chat
        create_response = client.post('/chats', json={'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        
        # Archive
        response = client.post(
            f'/chats/{chat_id}/archive',
            json={'archive': True, 'user_id': 'test@test.com'}
        )
        
        assert response.status_code == 200
        assert response.get_json()['status'] == 'archived'
    
    def test_unarchive_chat(self, client):
        """Test unarchiving a chat."""
        # Create and archive chat
        create_response = client.post('/chats', json={'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        client.post(f'/chats/{chat_id}/archive', json={'archive': True, 'user_id': 'test@test.com'})
        
        # Unarchive
        response = client.post(
            f'/chats/{chat_id}/archive',
            json={'archive': False, 'user_id': 'test@test.com'}
        )
        
        assert response.status_code == 200
        assert response.get_json()['status'] == 'unarchived'
    
    def test_update_chat_title(self, client):
        """Test updating chat title."""
        # Create chat
        create_response = client.post('/chats', json={'title': 'Old', 'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        
        # Update title
        response = client.put(
            f'/chats/{chat_id}/title',
            json={'title': 'New Title', 'user_id': 'test@test.com'}
        )
        
        assert response.status_code == 200
        
        # Verify
        get_response = client.get(f'/chats/{chat_id}?user_id=test@test.com')
        assert get_response.get_json()['title'] == 'New Title'


class TestChatAPIFiltering:
    """Tests for filtering and pagination."""
    
    def test_list_excludes_archived_by_default(self, client):
        """Test that archived chats are excluded by default."""
        # Create active chat
        client.post('/chats', json={'title': 'Active', 'user_id': 'test@test.com'})
        
        # Create and archive chat
        create_response = client.post('/chats', json={'title': 'Archived', 'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        client.post(f'/chats/{chat_id}/archive', json={'archive': True, 'user_id': 'test@test.com'})
        
        # List without archived
        response = client.get('/chats?user_id=test@test.com')
        data = response.get_json()
        
        assert len(data['chats']) == 1
        assert data['chats'][0]['title'] == 'Active'
    
    def test_list_includes_archived_when_requested(self, client):
        """Test including archived chats in listing."""
        client.post('/chats', json={'title': 'Active', 'user_id': 'test@test.com'})
        
        create_response = client.post('/chats', json={'title': 'Archived', 'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        client.post(f'/chats/{chat_id}/archive', json={'archive': True, 'user_id': 'test@test.com'})
        
        response = client.get('/chats?user_id=test@test.com&include_archived=true')
        data = response.get_json()
        
        assert len(data['chats']) == 2
    
    def test_list_pagination_limit(self, client):
        """Test limiting chat list results."""
        for i in range(10):
            client.post('/chats', json={'title': f'Chat {i}', 'user_id': 'test@test.com'})
        
        response = client.get('/chats?user_id=test@test.com&limit=5')
        data = response.get_json()
        
        assert len(data['chats']) == 5
    
    def test_list_pagination_offset(self, client):
        """Test offset in chat list."""
        for i in range(10):
            client.post('/chats', json={'title': f'Chat {i}', 'user_id': 'test@test.com'})
        
        response = client.get('/chats?user_id=test@test.com&limit=5&offset=5')
        data = response.get_json()
        
        assert len(data['chats']) == 5


class TestChatAPIAuthentication:
    """Tests for authentication handling.
    
    Note: These tests are skipped because AUTH is disabled at module import time
    for all other tests. To test authentication, run these in a separate test file
    that doesn't set DISABLE_AUTH=true at the top.
    """
    
    @pytest.mark.skip(reason="Auth disabled at module level for other tests")
    def test_auth_required_create(self, auth_client):
        """Test that auth is required for creating chats."""
        response = auth_client.post('/chats', json={'title': 'Test'})
        
        assert response.status_code == 401
    
    @pytest.mark.skip(reason="Auth disabled at module level for other tests")
    def test_auth_with_token(self, auth_client):
        """Test creating chat with valid auth token."""
        # First register/login to get token
        auth_client.post('/auth/register', json={
            'email': 'test@test.com',
            'password': 'testpass'
        })
        
        login_response = auth_client.post('/auth/login', json={
            'email': 'test@test.com',
            'password': 'testpass'
        })
        token = login_response.get_json()['token']
        
        # Create chat with token
        response = auth_client.post(
            '/chats',
            json={'title': 'Authenticated Chat'},
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 201


class TestChatAPIDataIntegrity:
    """Tests for data integrity and edge cases."""
    
    def test_message_order_preserved(self, client):
        """Test that message order is preserved."""
        create_response = client.post('/chats', json={'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        
        # Add messages in order
        for i in range(5):
            client.post(f'/chats/{chat_id}/messages', json={
                'role': 'user',
                'content': f'Message {i}',
                'user_id': 'test@test.com'
            })
        
        # Get chat and verify order
        response = client.get(f'/chats/{chat_id}?user_id=test@test.com')
        messages = response.get_json()['messages']
        
        for i, msg in enumerate(messages):
            assert msg['content'] == f'Message {i}'
    
    def test_unicode_support(self, client):
        """Test handling of unicode in chat content."""
        create_response = client.post('/chats', json={
            'title': '你好 Hello 🎉',
            'user_id': 'test@test.com'
        })
        chat_id = create_response.get_json()['chat_id']
        
        client.post(f'/chats/{chat_id}/messages', json={
            'role': 'user',
            'content': 'こんにちは 世界 🌍',
            'user_id': 'test@test.com'
        })
        
        response = client.get(f'/chats/{chat_id}?user_id=test@test.com')
        data = response.get_json()
        
        assert data['title'] == '你好 Hello 🎉'
        assert data['messages'][0]['content'] == 'こんにちは 世界 🌍'
    
    def test_large_message(self, client):
        """Test handling of large messages."""
        create_response = client.post('/chats', json={'user_id': 'test@test.com'})
        chat_id = create_response.get_json()['chat_id']
        
        large_content = 'A' * 50000
        
        response = client.post(f'/chats/{chat_id}/messages', json={
            'role': 'user',
            'content': large_content,
            'user_id': 'test@test.com'
        })
        
        assert response.status_code == 201
        assert len(response.get_json()['content']) == 50000
    
    def test_concurrent_chat_creation(self, client):
        """Test handling multiple chat creations."""
        chat_ids = []
        
        for i in range(20):
            response = client.post('/chats', json={
                'title': f'Chat {i}',
                'user_id': 'test@test.com'
            })
            assert response.status_code == 201
            chat_ids.append(response.get_json()['chat_id'])
        
        # All IDs should be unique
        assert len(set(chat_ids)) == 20
        
        # All should be retrievable
        for chat_id in chat_ids:
            response = client.get(f'/chats/{chat_id}?user_id=test@test.com')
            assert response.status_code == 200
    
    def test_user_isolation(self, client):
        """Test that users cannot access each other's chats."""
        # Create chat for user 1
        response1 = client.post('/chats', json={
            'title': 'User 1 Chat',
            'user_id': 'user1@test.com'
        })
        chat_id = response1.get_json()['chat_id']
        
        # User 2 should not be able to access
        response2 = client.get(f'/chats/{chat_id}?user_id=user2@test.com')
        assert response2.status_code == 404
        
        # User 2's list should not include user 1's chat
        list_response = client.get('/chats?user_id=user2@test.com')
        assert len(list_response.get_json()['chats']) == 0


class TestChatAPIFullFlow:
    """Full end-to-end workflow tests."""
    
    def test_complete_conversation_flow(self, client):
        """Test a complete conversation flow."""
        user_id = 'test@test.com'
        
        # 1. Create new chat
        create_response = client.post('/chats', json={'user_id': user_id})
        assert create_response.status_code == 201
        chat_id = create_response.get_json()['chat_id']
        
        # 2. User sends first message
        msg1_response = client.post(f'/chats/{chat_id}/messages', json={
            'role': 'user',
            'content': 'What is Python?',
            'user_id': user_id
        })
        assert msg1_response.status_code == 201
        
        # 3. Bot responds
        msg2_response = client.post(f'/chats/{chat_id}/messages', json={
            'role': 'assistant',
            'content': 'Python is a programming language...',
            'user_id': user_id
        })
        assert msg2_response.status_code == 201
        
        # 4. User follows up
        client.post(f'/chats/{chat_id}/messages', json={
            'role': 'user',
            'content': 'Can you give an example?',
            'user_id': user_id
        })
        
        # 5. Bot responds again
        client.post(f'/chats/{chat_id}/messages', json={
            'role': 'assistant',
            'content': 'Here is an example: print("Hello")',
            'user_id': user_id
        })
        
        # 6. Verify chat state
        get_response = client.get(f'/chats/{chat_id}?user_id={user_id}')
        chat_data = get_response.get_json()
        
        assert len(chat_data['messages']) == 4
        assert chat_data['title'] == 'What is Python?'
        
        # 7. Chat should appear in list
        list_response = client.get(f'/chats?user_id={user_id}')
        chats = list_response.get_json()['chats']
        assert len(chats) == 1
        assert chats[0]['message_count'] == 4
        
        # 8. Archive the chat
        archive_response = client.post(f'/chats/{chat_id}/archive', json={
            'archive': True,
            'user_id': user_id
        })
        assert archive_response.status_code == 200
        
        # 9. Should not appear in default list
        list_response2 = client.get(f'/chats?user_id={user_id}')
        assert len(list_response2.get_json()['chats']) == 0
        
        # 10. Should appear when including archived
        list_response3 = client.get(f'/chats?user_id={user_id}&include_archived=true')
        assert len(list_response3.get_json()['chats']) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
