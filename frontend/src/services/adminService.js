/**
 * Admin Service
 * Handles all admin-related API calls for the TAI-tutor-ai admin panel.
 */

import { DEFAULT_BACKEND_URL } from '../config';

class AdminService {
  constructor() {
    this.baseURL = `${DEFAULT_BACKEND_URL}/admin`;
    this.token = null;
  }

  /**
   * Set the admin authentication token
   */
  setToken(token) {
    this.token = token;
    // Store in session storage (not localStorage for security)
    sessionStorage.setItem('admin_token', token);
  }

  /**
   * Get the admin authentication token
   */
  getToken() {
    if (!this.token) {
      this.token = sessionStorage.getItem('admin_token');
    }
    return this.token;
  }

  /**
   * Clear the admin authentication token
   */
  clearToken() {
    this.token = null;
    sessionStorage.removeItem('admin_token');
  }

  /**
   * Get authorization headers with token
   */
  getAuthHeaders() {
    const token = this.getToken();
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  }

  /**
   * Verify admin password and get token
   */
  async verifyPassword(password) {
    try {
      const response = await fetch(`${this.baseURL}/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ password })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        this.setToken(data.token);
        return { success: true, token: data.token };
      } else {
        return { success: false, error: data.error || 'Invalid password' };
      }
    } catch (error) {
      console.error('Error verifying admin password:', error);
      return { success: false, error: 'Failed to verify password' };
    }
  }

  /**
   * Get list of all users
   */
  async getUsers() {
    try {
      const response = await fetch(`${this.baseURL}/users`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch users');
      }

      const data = await response.json();
      return data.users;
    } catch (error) {
      console.error('Error fetching users:', error);
      throw error;
    }
  }

  /**
   * Delete a user
   */
  async deleteUser(email) {
    try {
      const response = await fetch(`${this.baseURL}/users/${encodeURIComponent(email)}`, {
        method: 'DELETE',
        headers: this.getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to delete user');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error deleting user:', error);
      throw error;
    }
  }

  /**
   * Get course directory structure
   */
  async getCourses() {
    try {
      const response = await fetch(`${this.baseURL}/courses`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch courses');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching courses:', error);
      throw error;
    }
  }

  /**
   * Upload course files (zip)
   */
  async uploadCourse(file, targetPath) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('path', targetPath);

      const token = this.getToken();
      const response = await fetch(`${this.baseURL}/courses/upload`, {
        method: 'POST',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to upload course');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error uploading course:', error);
      throw error;
    }
  }

  /**
   * Delete course files or directories
   */
  async deleteCourses(paths) {
    try {
      const response = await fetch(`${this.baseURL}/courses/delete`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ paths })
      });

      if (!response.ok) {
        throw new Error('Failed to delete courses');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error deleting courses:', error);
      throw error;
    }
  }

  /**
   * Get system health information
   */
  async getHealth() {
    try {
      const response = await fetch(`${this.baseURL}/health`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch health info');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching health info:', error);
      throw error;
    }
  }

  /**
   * Trigger vector database rebuild
   */
  async triggerRebuild() {
    try {
      const response = await fetch(`${this.baseURL}/rebuild`, {
        method: 'POST',
        headers: this.getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to trigger rebuild');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error triggering rebuild:', error);
      throw error;
    }
  }

  /**
   * Check if user is authenticated as admin
   */
  isAuthenticated() {
    return !!this.getToken();
  }
}

// Export a singleton instance
export const adminService = new AdminService();
