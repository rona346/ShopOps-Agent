import React, { useState, useEffect } from 'react';
import {
  ApprovalRequest,
  ApprovalListResponse,
} from '../types';
import {
  listApprovals,
  updateApprovalQuantity,
  approveRequest,
  rejectRequest,
  executeApproval,
} from '../services/api';
import { EditQuantityModal } from './EditQuantityModal';
import { ExecutionConfirmModal } from './ExecutionConfirmModal';
import { Modal } from './Modal';

export interface ApprovalsSectionProps {
  onNotify: (type: 'success' | 'error' | 'warning' | 'info', message: string) => void;
  onTaskCreated: () => void;
}

export const ApprovalsSection: React.FC<ApprovalsSectionProps> = ({
  onNotify,
  onTaskCreated,
}) => {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Edit quantity modal state
  const [editingApproval, setEditingApproval] = useState<ApprovalRequest | null>(null);

  // Execution confirm modal state
  const [executingApproval, setExecutingApproval] = useState<ApprovalRequest | null>(null);

  // Reject modal state
  const [rejectingApproval, setRejectingApproval] = useState<ApprovalRequest | null>(null);
  const [rejectNotes, setRejectNotes] = useState('');
  const [rejectSubmitting, setRejectSubmitting] = useState(false);

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      setError(null);
      const res: ApprovalListResponse = await listApprovals({
        status: statusFilter === 'all' ? undefined : statusFilter,
        limit: 50,
        offset: 0,
      });
      setApprovals(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch approval requests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, [statusFilter]);

  const handleUpdateQuantity = async (
    approvalId: string,
    quantity: number,
    notes?: string
  ) => {
    await updateApprovalQuantity(approvalId, quantity, notes);
    onNotify('success', 'Proposed reorder quantity updated successfully.');
    fetchApprovals();
  };

  const handleApprove = async (approval: ApprovalRequest) => {
    try {
      await approveRequest(approval.id);
      onNotify('success', `Approval request for "${approval.product_name}" approved!`);
      fetchApprovals();
    } catch (err: any) {
      onNotify('error', err.message || 'Failed to approve request');
    }
  };

  const handleOpenReject = (approval: ApprovalRequest) => {
    setRejectingApproval(approval);
    setRejectNotes('');
  };

  const handleConfirmReject = async () => {
    if (!rejectingApproval) return;
    try {
      setRejectSubmitting(true);
      await rejectRequest(rejectingApproval.id, rejectNotes.trim() || undefined);
      onNotify('info', `Approval request for "${rejectingApproval.product_name}" rejected.`);
      setRejectingApproval(null);
      fetchApprovals();
    } catch (err: any) {
      onNotify('error', err.message || 'Failed to reject request');
    } finally {
      setRejectSubmitting(false);
    }
  };

  const handleConfirmExecution = async (approvalId: string, notes?: string) => {
    const task = await executeApproval(approvalId, notes);
    onNotify('success', `Internal reorder task created: ${task.id}`);
    fetchApprovals();
    onTaskCreated();
  };

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>Owner Approval Workflow</h2>
          <p className="section-subtitle">
            Small business owner authorization control. Review, modify, approve, reject, or execute proposed replenishment actions.
          </p>
        </div>
        <div className="section-header-actions">
          <button className="btn btn-secondary" onClick={fetchApprovals} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Approvals'}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-box alert-warning">
          <strong>Notice:</strong> {error}
        </div>
      )}

      {/* Status Filter Tabs */}
      <div className="filter-tabs">
        <button
          className={`filter-tab ${statusFilter === 'pending' ? 'active' : ''}`}
          onClick={() => setStatusFilter('pending')}
        >
          Pending Review
        </button>
        <button
          className={`filter-tab ${statusFilter === 'approved' ? 'active' : ''}`}
          onClick={() => setStatusFilter('approved')}
        >
          Approved (Ready to Execute)
        </button>
        <button
          className={`filter-tab ${statusFilter === 'executed' ? 'active' : ''}`}
          onClick={() => setStatusFilter('executed')}
        >
          Executed
        </button>
        <button
          className={`filter-tab ${statusFilter === 'rejected' ? 'active' : ''}`}
          onClick={() => setStatusFilter('rejected')}
        >
          Rejected
        </button>
        <button
          className={`filter-tab ${statusFilter === 'all' ? 'active' : ''}`}
          onClick={() => setStatusFilter('all')}
        >
          All Requests
        </button>
      </div>

      {/* Approvals Table / Card List */}
      <div className="card table-card">
        {loading ? (
          <div className="loading-state">
            <span className="spin">🔄</span>
            <p>Loading approval requests...</p>
          </div>
        ) : approvals.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">✅</div>
            <h3>No {statusFilter === 'all' ? '' : statusFilter} Approval Requests</h3>
            <p>
              {statusFilter === 'pending'
                ? 'All clear! There are no pending reorder requests awaiting your review.'
                : `There are currently no requests in "${statusFilter}" status.`}
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>Current Stock</th>
                  <th>Proposed Reorder</th>
                  <th>Estimated Cost</th>
                  <th>Status</th>
                  <th>Rationale / Notes</th>
                  <th style={{ textAlign: 'right' }}>Owner Decision</th>
                </tr>
              </thead>
              <tbody>
                {approvals.map((req) => (
                  <tr key={req.id}>
                    <td>
                      <div className="font-semibold">{req.product_name}</div>
                      <div className="text-muted" style={{ fontSize: '0.8rem' }}>
                        ID: {req.id}
                      </div>
                    </td>
                    <td className="code-cell">{req.sku}</td>
                    <td>{req.current_quantity} units</td>
                    <td>
                      <span className="font-bold text-primary">
                        {req.proposed_reorder_quantity} units
                      </span>
                      {req.status === 'pending' && (
                        <button
                          className="btn-link"
                          style={{ marginLeft: '0.5rem', fontSize: '0.8rem' }}
                          onClick={() => setEditingApproval(req)}
                          title="Edit proposed quantity"
                        >
                          ✏️ Edit
                        </button>
                      )}
                    </td>
                    <td>
                      {req.estimated_cost != null ? `$${req.estimated_cost.toFixed(2)}` : '—'}
                    </td>
                    <td>
                      {req.status === 'pending' && (
                        <span className="badge badge-warning">Pending</span>
                      )}
                      {req.status === 'approved' && (
                        <span className="badge badge-success">Approved</span>
                      )}
                      {req.status === 'executed' && (
                        <span className="badge badge-primary">Executed</span>
                      )}
                      {req.status === 'rejected' && (
                        <span className="badge badge-danger">Rejected</span>
                      )}
                    </td>
                    <td style={{ maxWidth: '280px', fontSize: '0.85rem' }}>
                      <div>{req.reason}</div>
                      {req.owner_notes && (
                        <div className="owner-notes-tag" style={{ marginTop: '0.25rem' }}>
                          <em>Owner note:</em> {req.owner_notes}
                        </div>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="table-actions">
                        {req.status === 'pending' && (
                          <>
                            <button
                              className="btn btn-sm btn-success"
                              onClick={() => handleApprove(req)}
                              title="Approve this reorder proposal"
                            >
                              Approve
                            </button>
                            <button
                              className="btn btn-sm btn-outline"
                              onClick={() => handleOpenReject(req)}
                              title="Reject this proposal"
                            >
                              Reject
                            </button>
                          </>
                        )}

                        {req.status === 'approved' && (
                          <button
                            className="btn btn-sm btn-primary"
                            onClick={() => setExecutingApproval(req)}
                            title="Execute this approved request into an internal task"
                          >
                            ⚡ Execute Task
                          </button>
                        )}

                        {req.status === 'executed' && (
                          <span className="text-muted" style={{ fontSize: '0.85rem' }}>
                            ✅ Task Created
                          </span>
                        )}

                        {req.status === 'rejected' && (
                          <span className="text-muted" style={{ fontSize: '0.85rem' }}>
                            ❌ Declined
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit Quantity Modal */}
      <EditQuantityModal
        isOpen={!!editingApproval}
        onClose={() => setEditingApproval(null)}
        approval={editingApproval}
        onSave={handleUpdateQuantity}
      />

      {/* Execution Confirmation Modal */}
      <ExecutionConfirmModal
        isOpen={!!executingApproval}
        onClose={() => setExecutingApproval(null)}
        approval={executingApproval}
        onConfirm={handleConfirmExecution}
      />

      {/* Reject Modal */}
      <Modal
        isOpen={!!rejectingApproval}
        onClose={() => setRejectingApproval(null)}
        title="Reject Reorder Proposal"
        footer={
          <div className="modal-footer-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setRejectingApproval(null)}
              disabled={rejectSubmitting}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleConfirmReject}
              disabled={rejectSubmitting}
            >
              {rejectSubmitting ? 'Rejecting...' : 'Confirm Reject'}
            </button>
          </div>
        }
      >
        <p>
          Are you sure you want to reject the reorder proposal for{' '}
          <strong>{rejectingApproval?.product_name}</strong> ({rejectingApproval?.proposed_reorder_quantity} units)?
        </p>

        <div className="form-group" style={{ marginTop: '1rem' }}>
          <label htmlFor="reject-notes">Reason for Rejection (Optional)</label>
          <textarea
            id="reject-notes"
            rows={3}
            className="form-control"
            placeholder="e.g. Supplier minimum order not met, will review next quarter..."
            value={rejectNotes}
            onChange={(e) => setRejectNotes(e.target.value)}
            disabled={rejectSubmitting}
          />
        </div>
      </Modal>
    </div>
  );
};
