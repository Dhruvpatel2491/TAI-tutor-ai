import React from 'react';
import '../styles/ConfirmModal.css';

/**
 * ConfirmModal - A reusable custom confirmation dialog component
 * 
 * @param {boolean} isOpen - Controls modal visibility
 * @param {function} onClose - Callback when modal is dismissed/cancelled
 * @param {function} onConfirm - Callback when user confirms action
 * @param {string} title - Modal title/heading
 * @param {string} message - Modal body message/question
 * @param {string} confirmText - Text for confirm button (default: "Confirm")
 * @param {string} cancelText - Text for cancel button (default: "Cancel")
 * @param {string} variant - Visual variant: 'danger', 'warning', 'info' (default: 'warning')
 */
function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = "Confirm Action",
  message = "Are you sure you want to proceed?",
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "warning" // 'danger', 'warning', 'info'
}) {
  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const handleCancel = () => {
    onClose();
  };

  // Handle backdrop click (click outside modal)
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      handleCancel();
    }
  };

  // Handle keyboard events for accessibility
  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      handleCancel();
    } else if (e.key === 'Enter' && !e.shiftKey) {
      handleConfirm();
    }
  };

  return (
    <div 
      className="confirm-modal-backdrop" 
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
      aria-describedby="confirm-modal-message"
    >
      <div className={`confirm-modal-content confirm-modal-${variant}`}>
        <div className="confirm-modal-header">
          <h3 id="confirm-modal-title" className="confirm-modal-title">
            {variant === 'danger' && <span className="confirm-modal-icon">⚠️</span>}
            {variant === 'warning' && <span className="confirm-modal-icon">⚡</span>}
            {variant === 'info' && <span className="confirm-modal-icon">ℹ️</span>}
            {title}
          </h3>
          <button
            className="confirm-modal-close-btn"
            onClick={handleCancel}
            aria-label="Close dialog"
            type="button"
          >
            ×
          </button>
        </div>
        
        <div className="confirm-modal-body">
          <p id="confirm-modal-message" className="confirm-modal-message">
            {message}
          </p>
        </div>
        
        <div className="confirm-modal-footer">
          <button
            className="confirm-modal-btn confirm-modal-btn-cancel"
            onClick={handleCancel}
            type="button"
            autoFocus
          >
            {cancelText}
          </button>
          <button
            className={`confirm-modal-btn confirm-modal-btn-confirm confirm-modal-btn-${variant}`}
            onClick={handleConfirm}
            type="button"
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmModal;
