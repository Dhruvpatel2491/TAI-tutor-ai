import React, { useState, useEffect, useRef } from 'react';
import '../styles/PromptModal.css';

/**
 * PromptModal - A reusable custom prompt dialog component with text input
 * 
 * @param {boolean} isOpen - Controls modal visibility
 * @param {function} onClose - Callback when modal is dismissed/cancelled
 * @param {function} onConfirm - Callback when user confirms action (receives input value)
 * @param {string} title - Modal title/heading
 * @param {string} message - Modal body message/prompt text
 * @param {string} placeholder - Input placeholder text
 * @param {string} defaultValue - Default value for input
 * @param {string} confirmText - Text for confirm button (default: "OK")
 * @param {string} cancelText - Text for cancel button (default: "Cancel")
 * @param {string} variant - Visual variant: 'info', 'primary' (default: 'primary')
 */
function PromptModal({
  isOpen,
  onClose,
  onConfirm,
  title = "Input Required",
  message = "Please enter a value:",
  placeholder = "",
  defaultValue = "",
  confirmText = "OK",
  cancelText = "Cancel",
  variant = "primary" // 'primary', 'info'
}) {
  const [inputValue, setInputValue] = useState(defaultValue);
  const inputRef = useRef(null);

  // Reset input value when modal opens with new default value
  useEffect(() => {
    if (isOpen) {
      setInputValue(defaultValue);
      // Focus input after a short delay to ensure modal is rendered
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
          inputRef.current.select();
        }
      }, 100);
    }
  }, [isOpen, defaultValue]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm(inputValue.trim());
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
      e.preventDefault();
      handleConfirm();
    }
  };

  return (
    <div 
      className="prompt-modal-backdrop" 
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="prompt-modal-title"
      aria-describedby="prompt-modal-message"
    >
      <div className={`prompt-modal-content prompt-modal-${variant}`}>
        <div className="prompt-modal-header">
          <h3 id="prompt-modal-title" className="prompt-modal-title">
            {variant === 'info' && <span className="prompt-modal-icon">ℹ️</span>}
            {variant === 'primary' && <span className="prompt-modal-icon">✏️</span>}
            {title}
          </h3>
          <button
            className="prompt-modal-close-btn"
            onClick={handleCancel}
            aria-label="Close dialog"
            type="button"
          >
            ×
          </button>
        </div>
        
        <div className="prompt-modal-body">
          <p id="prompt-modal-message" className="prompt-modal-message">
            {message}
          </p>
          <input
            ref={inputRef}
            type="text"
            className="prompt-modal-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            aria-label={message}
          />
        </div>
        
        <div className="prompt-modal-footer">
          <button
            className="prompt-modal-btn prompt-modal-btn-cancel"
            onClick={handleCancel}
            type="button"
          >
            {cancelText}
          </button>
          <button
            className={`prompt-modal-btn prompt-modal-btn-confirm prompt-modal-btn-${variant}`}
            onClick={handleConfirm}
            type="button"
            disabled={!inputValue.trim()}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export default PromptModal;
