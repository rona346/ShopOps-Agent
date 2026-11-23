import React, { useState } from 'react';
import { Modal } from './Modal';
import { ApprovalRequest } from '../types';

export interface ExecutionConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  approval: ApprovalRequest | null;
  onConfirm: (approvalId: string, notes?: string) => Promise<void>;
}

export const ExecutionConfirmModal: React.FC<ExecutionConfirmModalProps> = ({
  isOpen,
  onClose,
  approval,
  onConfirm,
}) => {
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!approval) return null;

  const handleConfirm = async () => {
    try {
      setSubmitting(true);
      setError(null);
      await onConfirm(approval.id, notes.trim() || undefined);
      setNotes('');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Execution failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Confirm Reorder Task Execution"
      footer={
        <div className="modal-footer-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleConfirm}
            disabled={submitting}
          >
            {submitting ? 'Executing...' : 'Confirm & Create Task'}
          </button>
        </div>
      }
    >
      <div className="execution-modal-content">
        <div className="alert-box alert-info" style={{ marginBottom: '1.25rem' }}>
          <strong>Execution Safety Policy:</strong>
          <p style={{ marginTop: '0.25rem', fontSize: '0.875rem' }}>
            This action creates an <strong>internal reorder task</strong> for store operations.
            It is completely non-destructive: it will <em>not</em> contact suppliers, process payments,
            or alter current inventory stock counts.
          </p>
        </div>

        <div className="detail-grid">
          <div className="detail-item">
            <span className="detail-label">Product Name</span>
            <span className="detail-value font-semibold">{approval.product_name}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">SKU</span>
            <span className="detail-value">{approval.sku}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Approved Units</span>
            <span className="detail-value font-semibold text-primary">
              {approval.proposed_reorder_quantity} units
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Estimated Cost</span>
            <span className="detail-value">
              {approval.estimated_cost != null
                ? `$${approval.estimated_cost.toFixed(2)}`
                : 'N/A'}
            </span>
          </div>
          <div className="detail-item full-width">
            <span className="detail-label">Approval ID</span>
            <span className="detail-value code-snippet">{approval.id}</span>
          </div>
        </div>

        <div className="form-group" style={{ marginTop: '1.25rem' }}>
          <label htmlFor="exec-notes">Execution Notes (Optional)</label>
          <textarea
            id="exec-notes"
            rows={3}
            className="form-control"
            placeholder="Add operational notes for the receiving or stock manager..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={submitting}
          />
        </div>

        {error && (
          <div className="alert-box alert-error" style={{ marginTop: '1rem' }}>
            {error}
          </div>
        )}
      </div>
    </Modal>
  );
};
