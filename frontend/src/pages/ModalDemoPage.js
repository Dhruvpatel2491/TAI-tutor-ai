import React, { useState } from 'react';
import ConfirmModal from '../components/ConfirmModal';
import '../styles/ConfirmModal.css';

/**
 * ModalDemo - Demonstration page showcasing the ConfirmModal component
 * This page shows all variants and use cases of the custom confirmation modal
 */
function ModalDemo() {
  const [modalState, setModalState] = useState({
    isOpen: false,
    title: "",
    message: "",
    variant: "warning",
    confirmText: "Confirm",
    cancelText: "Cancel"
  });

  const [actionLog, setActionLog] = useState([]);

  const logAction = (action) => {
    const timestamp = new Date().toLocaleTimeString();
    setActionLog(prev => [`[${timestamp}] ${action}`, ...prev].slice(0, 10));
  };

  const showModal = (config) => {
    setModalState({
      isOpen: true,
      ...config
    });
  };

  const closeModal = () => {
    setModalState(prev => ({ ...prev, isOpen: false }));
    logAction("Modal dismissed/cancelled");
  };

  const handleConfirm = () => {
    logAction(`Action confirmed: ${modalState.title}`);
  };

  return (
    <div style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Custom Confirmation Modal Demo</h1>
      <p style={{ color: '#666', marginBottom: '40px' }}>
        A custom, accessible, and responsive modal component to replace native <code>window.confirm</code> dialogs.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '40px' }}>
        {/* Danger Variant */}
        <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fff' }}>
          <h3 style={{ color: '#dc3545', marginTop: 0 }}>Danger Variant</h3>
          <p style={{ color: '#666', fontSize: '14px' }}>
            Use for destructive actions like deleting data that cannot be undone.
          </p>
          <button
            style={{
              padding: '10px 20px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600'
            }}
            onClick={() => showModal({
              title: "Delete Item",
              message: "Are you sure you want to delete this item? This action cannot be undone.",
              variant: "danger",
              confirmText: "Delete",
              cancelText: "Cancel"
            })}
          >
            Show Danger Modal
          </button>
        </div>

        {/* Warning Variant */}
        <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fff' }}>
          <h3 style={{ color: '#ffc107', marginTop: 0 }}>Warning Variant</h3>
          <p style={{ color: '#666', fontSize: '14px' }}>
            Use for actions that require caution, like discarding unsaved changes.
          </p>
          <button
            style={{
              padding: '10px 20px',
              backgroundColor: '#ffc107',
              color: '#333',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600'
            }}
            onClick={() => showModal({
              title: "Unsaved Changes",
              message: "You have unsaved changes. Are you sure you want to leave?",
              variant: "warning",
              confirmText: "Leave",
              cancelText: "Stay"
            })}
          >
            Show Warning Modal
          </button>
        </div>

        {/* Info Variant */}
        <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fff' }}>
          <h3 style={{ color: '#007bff', marginTop: 0 }}>Info Variant</h3>
          <p style={{ color: '#666', fontSize: '14px' }}>
            Use for informational confirmations or non-critical actions.
          </p>
          <button
            style={{
              padding: '10px 20px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600'
            }}
            onClick={() => showModal({
              title: "Confirm Action",
              message: "Do you want to proceed with this action?",
              variant: "info",
              confirmText: "Proceed",
              cancelText: "Cancel"
            })}
          >
            Show Info Modal
          </button>
        </div>
      </div>

      {/* Common Use Cases */}
      <div style={{ marginTop: '40px' }}>
        <h2>Common Use Cases</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
          <button
            style={{
              padding: '10px 20px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
            onClick={() => showModal({
              title: "Delete Plan",
              message: "Delete this plan? This action cannot be undone.",
              variant: "danger",
              confirmText: "Delete",
              cancelText: "Cancel"
            })}
          >
            Delete Plan
          </button>

          <button
            style={{
              padding: '10px 20px',
              backgroundColor: '#ffc107',
              color: '#333',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
            onClick={() => showModal({
              title: "Overwrite Plan",
              message: "Overwrite existing plan 'My Study Plan'? This action cannot be undone.",
              variant: "warning",
              confirmText: "Overwrite",
              cancelText: "Cancel"
            })}
          >
            Overwrite Plan
          </button>

          <button
            style={{
              padding: '10px 20px',
              backgroundColor: '#ffc107',
              color: '#333',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
            onClick={() => showModal({
              title: "Unsaved Changes",
              message: "You have unsaved changes. Are you sure you want to cancel?",
              variant: "warning",
              confirmText: "Yes, Cancel",
              cancelText: "Keep Editing"
            })}
          >
            Cancel with Unsaved Changes
          </button>

          <button
            style={{
              padding: '10px 20px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
            onClick={() => showModal({
              title: "Regenerate Plan",
              message: "This will regenerate your plan based on new requirements. Continue?",
              variant: "info",
              confirmText: "Regenerate",
              cancelText: "Cancel"
            })}
          >
            Regenerate Plan
          </button>

          <button
            style={{
              padding: '10px 20px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
            onClick={() => showModal({
              title: "Submit Assignment",
              message: "Are you ready to submit your assignment? You won't be able to edit it after submission.",
              variant: "info",
              confirmText: "Submit",
              cancelText: "Review Again"
            })}
          >
            Submit Assignment
          </button>
        </div>
      </div>

      {/* Action Log */}
      <div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
        <h2 style={{ marginTop: 0 }}>Action Log</h2>
        {actionLog.length === 0 ? (
          <p style={{ color: '#666' }}>No actions yet. Try clicking a button above!</p>
        ) : (
          <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
            {actionLog.map((log, index) => (
              <li
                key={index}
                style={{
                  padding: '8px 12px',
                  marginBottom: '4px',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  fontSize: '14px',
                  fontFamily: 'monospace'
                }}
              >
                {log}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Features List */}
      <div style={{ marginTop: '40px' }}>
        <h2>Features</h2>
        <ul style={{ lineHeight: '1.8', color: '#333' }}>
          <li>✅ <strong>Fully Accessible:</strong> ARIA labels, keyboard navigation (Escape/Enter), and focus management</li>
          <li>✅ <strong>Responsive Design:</strong> Works on all screen sizes with mobile-optimized layout</li>
          <li>✅ <strong>Three Variants:</strong> Danger (red), Warning (yellow), and Info (blue) for different contexts</li>
          <li>✅ <strong>Customizable:</strong> Custom titles, messages, and button text</li>
          <li>✅ <strong>Smooth Animations:</strong> Fade-in backdrop and slide-up modal for polished UX</li>
          <li>✅ <strong>Click Outside to Close:</strong> Backdrop click dismisses the modal</li>
          <li>✅ <strong>Dark Mode Support:</strong> Respects system color scheme preferences</li>
          <li>✅ <strong>No External Dependencies:</strong> Pure React with vanilla CSS</li>
        </ul>
      </div>

      {/* Usage Example */}
      <div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
        <h2 style={{ marginTop: 0 }}>Usage Example</h2>
        <pre style={{
          backgroundColor: '#282c34',
          color: '#abb2bf',
          padding: '20px',
          borderRadius: '8px',
          overflow: 'auto',
          fontSize: '14px'
        }}>
{`import ConfirmModal from './components/ConfirmModal';

function MyComponent() {
  const [modalOpen, setModalOpen] = useState(false);

  const handleDelete = () => {
    setModalOpen(true);
  };

  const confirmDelete = () => {
    // Perform delete operation
    console.log('Item deleted');
    setModalOpen(false);
  };

  return (
    <>
      <button onClick={handleDelete}>Delete Item</button>
      
      <ConfirmModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onConfirm={confirmDelete}
        title="Delete Item"
        message="Are you sure you want to delete this item?"
        variant="danger"
        confirmText="Delete"
        cancelText="Cancel"
      />
    </>
  );
}`}
        </pre>
      </div>

      {/* The Actual Modal */}
      <ConfirmModal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        onConfirm={handleConfirm}
        title={modalState.title}
        message={modalState.message}
        confirmText={modalState.confirmText}
        cancelText={modalState.cancelText}
        variant={modalState.variant}
      />
    </div>
  );
}

export default ModalDemo;
