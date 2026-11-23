import React from 'react';
import { AuthenticatedUser } from '../types';

export interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingApprovalsCount: number;
  backendOnline: boolean | null;
  onRefresh: () => void;
  isRefreshing: boolean;
  currentUser: AuthenticatedUser | null;
  onOpenAuth: () => void;
  onSignOut: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  pendingApprovalsCount,
  backendOnline,
  onRefresh,
  isRefreshing,
  currentUser,
  onOpenAuth,
  onSignOut,
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview' },
    { id: 'inventory', label: 'Inventory' },
    { id: 'analysis', label: 'Analysis & Planning' },
    { id: 'agent', label: 'AI Insights' },
    {
      id: 'approvals',
      label: 'Approvals',
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined,
    },
    { id: 'tasks', label: 'Reorder Tasks' },
  ];

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand" onClick={() => setActiveTab('overview')}>
          <div className="brand-icon">📦</div>
          <div>
            <div className="brand-title">ShopOps Agent</div>
            <div className="brand-subtitle">Retail Inventory & Operations AI</div>
          </div>
        </div>

        <div className="navbar-links">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-link ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              {item.label}
              {item.badge !== undefined && (
                <span className="nav-badge">{item.badge}</span>
              )}
            </button>
          ))}
        </div>

        <div className="navbar-status">
          <div
            className={`status-indicator ${
              backendOnline === true ? 'online' : backendOnline === false ? 'offline' : 'checking'
            }`}
            title={
              backendOnline === true
                ? 'Backend connected'
                : backendOnline === false
                ? 'Backend unreachable'
                : 'Checking status...'
            }
          >
            <span className="status-dot"></span>
            <span className="status-text">
              {backendOnline === true ? 'Live API' : backendOnline === false ? 'Offline' : 'Connecting...'}
            </span>
          </div>

          {/* Owner Authentication Badge */}
          {currentUser ? (
            <div className="navbar-auth-user" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span className="badge badge-primary" title={`UID: ${currentUser.uid}`}>
                👤 {currentUser.email || 'Store Owner'}
              </span>
              <button
                className="btn btn-sm btn-outline"
                onClick={onSignOut}
                title="Sign out from dashboard"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <button
              className="btn btn-sm btn-primary"
              onClick={onOpenAuth}
              title="Sign in to unlock inventory management"
            >
              Sign In
            </button>
          )}

          <button
            className="btn-icon"
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Refresh current view"
          >
            <span className={isRefreshing ? 'spin' : ''}>🔄</span>
          </button>
        </div>
      </div>
    </nav>
  );
};
