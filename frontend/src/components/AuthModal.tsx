import React, { useState } from 'react';
import { Modal } from './Modal';
import { isFirebaseClientConfigured, signInWithFirebase } from '../services/firebase';
import { setAuthToken, getAuthMe } from '../services/api';
import { AuthenticatedUser } from '../types';

export interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthenticated: (user: AuthenticatedUser) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onAuthenticated,
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [customToken, setCustomToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const firebaseReady = isFirebaseClientConfigured();

  const handleFirebaseSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Please provide both email and password.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const idToken = await signInWithFirebase(email.trim(), password);
      setAuthToken(idToken);
      const user = await getAuthMe();
      onAuthenticated(user);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Firebase sign-in failed. Please check credentials.');
      setAuthToken(null);
    } finally {
      setLoading(false);
    }
  };

  const handleDevSignIn = async () => {
    try {
      setLoading(true);
      setError(null);
      const token = 'shopops-dev-owner-token';
      setAuthToken(token);
      const user = await getAuthMe();
      onAuthenticated(user);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to authenticate in development mode.');
      setAuthToken(null);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomTokenSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customToken.trim()) return;

    try {
      setLoading(true);
      setError(null);
      setAuthToken(customToken.trim());
      const user = await getAuthMe();
      onAuthenticated(user);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Token verification failed.');
      setAuthToken(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Store Owner Authentication"
      footer={
        <div className="modal-footer-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Close
          </button>
        </div>
      }
    >
      <div className="auth-modal-content">
        <div className="alert-box alert-info" style={{ marginBottom: '1.25rem' }}>
          <strong>Secure Owner Access:</strong>
          <p style={{ marginTop: '0.25rem', fontSize: '0.85rem' }}>
            All inventory, planning, AI insights, and reorder approvals are protected and require store owner authentication.
          </p>
        </div>

        {firebaseReady ? (
          <form onSubmit={handleFirebaseSignIn} className="auth-form">
            <div className="form-group">
              <label htmlFor="auth-email">Owner Email</label>
              <input
                id="auth-email"
                type="email"
                className="form-control"
                placeholder="owner@yourstore.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <label htmlFor="auth-password">Password</label>
              <input
                id="auth-password"
                type="password"
                className="form-control"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary full-width"
              style={{ marginTop: '0.75rem' }}
              disabled={loading}
            >
              {loading ? 'Signing In...' : 'Sign In with Firebase'}
            </button>
          </form>
        ) : (
          <div className="dev-auth-box">
            <div className="alert-box alert-warning" style={{ marginBottom: '1rem' }}>
              <strong>Cloud Auth Notice:</strong>
              <p style={{ marginTop: '0.25rem', fontSize: '0.85rem' }}>
                Firebase Web credentials are not yet configured in <code>frontend/.env</code>.
                You can authenticate using the <strong>Local Store Owner (Dev Mode)</strong> token.
              </p>
            </div>

            <button
              type="button"
              className="btn btn-primary full-width"
              onClick={handleDevSignIn}
              disabled={loading}
            >
              {loading ? 'Authenticating...' : '🔑 Sign In as Store Owner (Dev Mode)'}
            </button>
          </div>
        )}

        {/* Advanced Manual Token Entry Toggle */}
        <div style={{ marginTop: '1.25rem', borderTop: '1px solid #e2e8f0', paddingTop: '0.75rem' }}>
          <button
            type="button"
            className="btn-link"
            style={{ fontSize: '0.8rem' }}
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? '▲ Hide Advanced Options' : '▼ Advanced: Manual Bearer Token'}
          </button>

          {showAdvanced && (
            <form onSubmit={handleCustomTokenSubmit} style={{ marginTop: '0.75rem' }}>
              <div className="form-group">
                <label htmlFor="custom-token" style={{ fontSize: '0.8rem' }}>
                  Custom Bearer / Firebase ID Token
                </label>
                <input
                  id="custom-token"
                  type="text"
                  className="form-control form-control-sm"
                  placeholder="Paste Bearer token here..."
                  value={customToken}
                  onChange={(e) => setCustomToken(e.target.value)}
                  disabled={loading}
                />
              </div>
              <button
                type="submit"
                className="btn btn-sm btn-outline full-width"
                disabled={loading || !customToken.trim()}
              >
                Apply Custom Token
              </button>
            </form>
          )}
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
