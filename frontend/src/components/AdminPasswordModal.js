import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminService } from '../services/adminService';
import '../styles/AdminPasswordModal.css';

const AdminPasswordModal = ({ onClose, onSuccess }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await adminService.verifyPassword(password);
      
      if (result.success) {
        if (onSuccess) {
          onSuccess();
        }
        navigate('/admin');
      } else {
        setError(result.error || 'Invalid password');
      }
    } catch (err) {
      console.error('Error verifying password:', err);
      setError('Failed to verify password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="admin-password-modal-overlay" onClick={handleOverlayClick}>
      <div className="admin-password-modal">
        <div className="modal-header">
          <h2>🔐 Admin Access</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p>Enter the admin password to continue:</p>
            
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Admin password"
              className="password-input"
              autoFocus
              disabled={loading}
            />
            
            {error && (
              <div className="error-message">
                ⚠️ {error}
              </div>
            )}
          </div>
          
          <div className="modal-footer">
            <button
              type="button"
              className="btn-cancel"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-submit"
              disabled={!password || loading}
            >
              {loading ? 'Verifying...' : 'Access Admin'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AdminPasswordModal;
