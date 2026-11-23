import React, { useState, useEffect } from 'react';
import { ReorderTask, ReorderTaskListResponse } from '../types';
import { listTasks } from '../services/api';

export interface TasksSectionProps {
  onNotify: (type: 'success' | 'error' | 'warning' | 'info', message: string) => void;
}

export const TasksSection: React.FC<TasksSectionProps> = ({ onNotify }) => {
  const [tasks, setTasks] = useState<ReorderTask[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      setError(null);
      const res: ReorderTaskListResponse = await listTasks({
        status: statusFilter === 'all' ? undefined : statusFilter,
        limit: 50,
        offset: 0,
      });
      setTasks(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err.message || 'Failed to fetch reorder tasks';
      setError(msg);
      onNotify('error', msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [statusFilter]);

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>Internal Reorder Tasks</h2>
          <p className="section-subtitle">
            Audit log and tracking of internal replenishment tasks created from owner-approved recommendations.
          </p>
        </div>
        <div className="section-header-actions">
          <button className="btn btn-secondary" onClick={fetchTasks} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Tasks'}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-box alert-warning">
          <strong>Notice:</strong> {error}
        </div>
      )}

      {/* Safety Policy Notice */}
      <div className="alert-box alert-info" style={{ marginBottom: '1.25rem' }}>
        <strong>Internal Operations Scope:</strong>
        <p style={{ marginTop: '0.25rem', fontSize: '0.875rem' }}>
          These tasks represent authorized internal replenishment workflows for your stock receiving team.
          ShopOps Agent enforces strict separation between decision approval and external actions—no real supplier contacts, orders, or credit card charges are made.
        </p>
      </div>

      {/* Status Filter Tabs */}
      <div className="filter-tabs">
        <button
          className={`filter-tab ${statusFilter === 'all' ? 'active' : ''}`}
          onClick={() => setStatusFilter('all')}
        >
          All Tasks ({total})
        </button>
        <button
          className={`filter-tab ${statusFilter === 'created' ? 'active' : ''}`}
          onClick={() => setStatusFilter('created')}
        >
          Created
        </button>
        <button
          className={`filter-tab ${statusFilter === 'in_progress' ? 'active' : ''}`}
          onClick={() => setStatusFilter('in_progress')}
        >
          In Progress
        </button>
        <button
          className={`filter-tab ${statusFilter === 'completed' ? 'active' : ''}`}
          onClick={() => setStatusFilter('completed')}
        >
          Completed
        </button>
      </div>

      {/* Tasks Table */}
      <div className="card table-card">
        {loading ? (
          <div className="loading-state">
            <span className="spin">🔄</span>
            <p>Loading reorder tasks...</p>
          </div>
        ) : tasks.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>No Reorder Tasks Found</h3>
            <p>
              {statusFilter === 'all'
                ? 'No reorder tasks have been executed yet. Go to the Approvals tab to approve and execute a replenishment recommendation.'
                : `No tasks match the "${statusFilter}" status filter.`}
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Task ID</th>
                  <th>Product Name</th>
                  <th>SKU</th>
                  <th>Approved Units</th>
                  <th>Estimated Cost</th>
                  <th>Status</th>
                  <th>Source Approval ID</th>
                  <th>Created At</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id}>
                    <td className="code-cell font-semibold">{task.id}</td>
                    <td>
                      <div className="font-semibold">{task.product_name}</div>
                    </td>
                    <td className="code-cell">{task.sku}</td>
                    <td>
                      <span className="font-bold text-primary">
                        {task.approved_reorder_quantity} units
                      </span>
                    </td>
                    <td>
                      {task.estimated_cost != null
                        ? `$${task.estimated_cost.toFixed(2)}`
                        : '—'}
                    </td>
                    <td>
                      {task.status === 'created' && (
                        <span className="badge badge-primary">Created</span>
                      )}
                      {task.status === 'in_progress' && (
                        <span className="badge badge-warning">In Progress</span>
                      )}
                      {task.status === 'completed' && (
                        <span className="badge badge-success">Completed</span>
                      )}
                      {task.status === 'cancelled' && (
                        <span className="badge badge-danger">Cancelled</span>
                      )}
                    </td>
                    <td className="code-cell text-muted" style={{ fontSize: '0.8rem' }}>
                      {task.approval_id}
                    </td>
                    <td className="text-muted" style={{ fontSize: '0.85rem' }}>
                      {formatDate(task.created_at)}
                    </td>
                    <td style={{ maxWidth: '200px', fontSize: '0.85rem' }}>
                      {task.notes || <span className="text-muted">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
