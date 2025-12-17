/**
 * Admin Service
 * Handles all admin-related API calls for the TAI-tutor-ai admin panel.
 */

import { DEFAULT_BACKEND_URL } from '../config';
import { authService } from './authService';

class AdminService {
  constructor() {
    this.baseURL = `${DEFAULT_BACKEND_URL}/admin`;
    this.adminPassword = null;
  }

  /**
   * Set the admin password (stored in memory only)
   */
  setAdminPassword(password) {
    this.adminPassword = password;
    // Store in session storage (cleared on browser close)
    sessionStorage.setItem('admin_password', password);
  }

  /**
   * Get the admin password
   */
  getAdminPassword() {
    if (!this.adminPassword) {
      this.adminPassword = sessionStorage.getItem('admin_password');
    }
    return this.adminPassword;
  }

  /**
   * Clear the admin password
   */
  clearAdminPassword() {
    this.adminPassword = null;
    sessionStorage.removeItem('admin_password');
  }

  /**
   * Get authorization headers with user bearer token and admin password
   */
  getAuthHeaders() {
    const userToken = authService.getToken();
    const adminPassword = this.getAdminPassword();
    
    return {
      'Content-Type': 'application/json',
      ...(userToken ? { 'Authorization': `Bearer ${userToken}` } : {}),
      ...(adminPassword ? { 'X-Admin-Password': adminPassword } : {})
    };
  }

  /**
   * Get auth headers for file uploads (no Content-Type)
   */
  getFileUploadHeaders() {
    const userToken = authService.getToken();
    const adminPassword = this.getAdminPassword();
    
    return {
      ...(userToken ? { 'Authorization': `Bearer ${userToken}` } : {}),
      ...(adminPassword ? { 'X-Admin-Password': adminPassword } : {})
    };
  }

  /**
   * Verify admin password with user's bearer token
   */
  async verifyPassword(password) {
    try {
      const userToken = authService.getToken();
      
      if (!userToken) {
        return { success: false, error: 'User not logged in' };
      }

      const response = await fetch(`${this.baseURL}/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userToken}`
        },
        body: JSON.stringify({ password })
      });

      const data = await response.json();

      if (response.ok && data.status === 'verified') {
        // Store admin password for subsequent requests
        this.setAdminPassword(password);
        return { success: true, user_id: data.user_id };
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

      const response = await fetch(`${this.baseURL}/courses/upload`, {
        method: 'POST',
        headers: this.getFileUploadHeaders(),
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
    return !!authService.getToken() && !!this.getAdminPassword();
  }
}

// Export a singleton instance
export const adminService = new AdminService();
