import React, { useState, useEffect } from 'react';
import { Modal } from './Modal';
import { ApprovalRequest } from '../types';

export interface EditQuantityModalProps {
  isOpen: boolean;
  onClose: () => void;
  approval: ApprovalRequest | null;
  onSave: (approvalId: string, quantity: number, notes?: string) => Promise<void>;
}

export const EditQuantityModal: React.FC<EditQuantityModalProps> = ({
  isOpen,
  onClose,
  approval,
  onSave,
}) => {
  const [quantity, setQuantity] = useState<number>(0);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (approval) {
      setQuantity(approval.proposed_reorder_quantity);
      setNotes(approval.owner_notes || '');
      setError(null);
    }
  }, [approval]);

  if (!approval) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (quantity < 0) {
      setError('Proposed reorder quantity must be non-negative.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      await onSave(approval.id, quantity, notes.trim() || undefined);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update reorder quantity');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Proposed Reorder Quantity"
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
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? 'Saving...' : 'Update Quantity'}
          </button>
        </div>
      }
    >
      <form onSubmit={handleSubmit}>
        <div className="detail-grid" style={{ marginBottom: '1rem' }}>
          <div className="detail-item">
            <span className="detail-label">Product</span>
            <span className="detail-value font-semibold">{approval.product_name}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Current Stock</span>
            <span className="detail-value">{approval.current_quantity} units</span>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="proposed-qty">
            Proposed Reorder Quantity <span className="required">*</span>
          </label>
          <input
            id="proposed-qty"
            type="number"
            min="0"
            className="form-control"
            value={quantity}
            onChange={(e) => setQuantity(Math.max(0, parseInt(e.target.value, 10) || 0))}
            required
            disabled={submitting}
          />
          <small className="help-text">
            Adjust the quantity recommended by deterministic analysis.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="owner-notes">Owner Modification Notes (Optional)</label>
          <textarea
            id="owner-notes"
            rows={3}
            className="form-control"
            placeholder="Explain why quantity was modified (e.g., supplier pack minimum, expected seasonal surge)..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={submitting}
          />
        </div>

        {error && <div className="alert-box alert-error">{error}</div>}
      </form>
    </Modal>
  );
};
