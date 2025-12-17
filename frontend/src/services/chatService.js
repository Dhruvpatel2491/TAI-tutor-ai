/**
 * Chat History Service
 * 
 * This service handles all API calls for chat history management including:
 * - Creating new chat sessions
 * - Listing past conversations
 * - Loading chat histories
 * - Deleting/archiving conversations
 */

import { apiGet, apiPost, apiRequest } from './http';
import { DEFAULT_BACKEND_URL } from '../config';

/**
 * Create a new chat session.
 * 
 * @param {Object} options
 * @param {string} options.title - Optional title for the chat
 * @param {string} options.backendURL - Optional backend URL override
 * @returns {Promise<Object>} The created chat session
 */
export async function createChat({ title = null, backendURL = DEFAULT_BACKEND_URL } = {}) {
  const response = await apiPost(`${backendURL}/chats`, { title });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to create chat' }));
    throw new Error(error.error || 'Failed to create chat');
  }
  return response.json();
}

/**
 * List all chat sessions for the current user.
 * 
 * @param {Object} options
 * @param {boolean} options.includeArchived - Whether to include archived chats
 * @param {number} options.limit - Maximum number of results
 * @param {number} options.offset - Number of results to skip
 * @param {string} options.backendURL - Optional backend URL override
 * @returns {Promise<Object>} Object containing array of chat summaries
 */
export async function listChats({
  includeArchived = false,
  limit = 50,
  offset = 0,
  backendURL = DEFAULT_BACKEND_URL
} = {}) {
  const params = new URLSearchParams({
    include_archived: includeArchived.toString(),
    limit: limit.toString(),
    offset: offset.toString()
  });
  
  const response = await apiGet(`${backendURL}/chats?${params}`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to list chats' }));
    throw new Error(error.error || 'Failed to list chats');
  }
  return response.json();
}

/**
 * Get a specific chat session with all messages.
 * 
 * @param {string} chatId - The chat session ID
 * @param {Object} options
 * @param {string} options.backendURL - Optional backend URL override
 * @returns {Promise<Object>} The chat session with messages
 */
export async function getChat(chatId, { backendURL = DEFAULT_BACKEND_URL } = {}) {
  const response = await apiGet(`${backendURL}/chats/${chatId}`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to get chat' }));
    throw new Error(error.error || 'Failed to get chat');
  }
  return response.json();
}

/**
 * Add a message to an existing chat session.
 * 
 * @param {string} chatId - The chat session ID
 * @param {Object} options
 * @param {string} options.role - 'user' or 'assistant'
 * @param {string} options.content - The message content
 * @param {Object} options.metadata - Optional message metadata
 * @param {string} options.backendURL - Optional backend URL override
 * @returns {Promise<Object>} The created message
 */
export async function addMessage(chatId, {
  role,
  content,
  metadata = {},
  backendURL = DEFAULT_BACKEND_URL
}) {
  const response = await apiPost(`${backendURL}/chats/${chatId}/messages`, {
    role,
    content,
    metadata
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to add message' }));
    throw new Error(error.error || 'Failed to add message');
  }
  return response.json();
}

/**
 * Delete a chat session.
 * 
 * @param {string} chatId - The chat session ID
 * @param {Object} options
 * @param {string} options.backendURL - Optional backend URL override
 * @returns {Promise<Object>} Deletion confirmation
 */
export async function deleteChat(chatId, { backendURL = DEFAULT_BACKEND_URL } = {}) {
  const response = await apiRequest(`${backendURL}/chats/${chatId}`, { method: 'DELETE' });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to delete chat' }));
    throw new Error(error.error || 'Failed to delete chat');
  }
  return response.json();
}

/**
 * Archive or unarchive a chat session.
 * 
 * @param {string} chatId - The chat session ID
 * @param {Object} options
 * @param {boolean} options.archive - True to archive, false to unarchive
 * @param {string} options.backendURL - Optional backend URL override
 * @returns {Promise<Object>} Archive/unarchive confirmation
 */
export async function archiveChat(chatId, { archive = true, backendURL = DEFAULT_BACKEND_URL } = {}) {
  const response = await apiPost(`${backendURL}/chats/${chatId}/archive`, { archive });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to archive chat' }));
    throw new Error(error.error || 'Failed to archive chat');
  }
  return response.json();
}

/**
 * Update the title of a chat session.
 * 
 * @param {string} chatId - The chat session ID
 * @param {string} title - The new title
 * @param {Object} options
 * @param {string} options.backendURL - Optional backend URL override
 * @returns {Promise<Object>} Update confirmation
 */
export async function updateChatTitle(chatId, title, { backendURL = DEFAULT_BACKEND_URL } = {}) {
  const response = await apiRequest(`${backendURL}/chats/${chatId}/title`, {
    method: 'PUT',
    body: { title }
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to update title' }));
    throw new Error(error.error || 'Failed to update title');
  }
  return response.json();
}

/**
 * Get or create a chat session for the current conversation.
 * If chatId is provided and valid, returns the existing chat.
 * Otherwise, creates a new chat.
 * 
 * @param {string|null} chatId - Optional existing chat ID
 * @param {Object} options
 * @param {string} options.title - Optional title for new chat
 * @param {string} options.backendURL - Optional backend URL override
 * @returns {Promise<Object>} The chat session
 */
export async function getOrCreateChat(chatId, { title = null, backendURL = DEFAULT_BACKEND_URL } = {}) {
  if (chatId) {
    try {
      const chat = await getChat(chatId, { backendURL });
      return chat;
    } catch (error) {
      // Chat not found, create new one
      console.error('Chat not found, creating new one');
    }
  }
  return createChat({ title, backendURL });
}

// Default export for convenience
const chatService = {
  createChat,
  listChats,
  getChat,
  addMessage,
  deleteChat,
  archiveChat,
  updateChatTitle,
  getOrCreateChat
};

export default chatService;
