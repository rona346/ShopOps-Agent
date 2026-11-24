import React, { useState, useEffect, useCallback } from 'react';
import {
  InventoryAnalysisSummary,
  ApprovalListResponse,
  ReorderTaskListResponse,
  AuthenticatedUser,
} from './types';
import {
  checkBackendHealth,
  getInventoryAnalysis,
  listApprovals,
  listTasks,
  getAuthMe,
  getAuthToken,
  setAuthToken,
} from './services/api';
import { signOutFromSupabase } from './services/supabaseAuth';
import { Navbar } from './components/Navbar';
import { ToastContainer, ToastMessage } from './components/Toast';
import { AuthModal } from './components/AuthModal';
import { OverviewSection } from './components/OverviewSection';
import { InventorySection } from './components/InventorySection';
import { AnalysisSection } from './components/AnalysisSection';
import { AgentSection } from './components/AgentSection';
import { ApprovalsSection } from './components/ApprovalsSection';
import { TasksSection } from './components/TasksSection';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Authentication State
  const [currentUser, setCurrentUser] = useState<AuthenticatedUser | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Global shared state for overview metrics
  const [analysis, setAnalysis] = useState<InventoryAnalysisSummary | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalListResponse | null>(null);
  const [tasks, setTasks] = useState<ReorderTaskListResponse | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback(
    (type: 'success' | 'error' | 'warning' | 'info', message: string) => {
      const id = Date.now().toString() + Math.random().toString().substring(2, 6);
      setToasts((prev) => [...prev, { id, type, message }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 5000);
    },
    []
  );

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Check existing session on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = getAuthToken();
      if (token) {
        try {
          const user = await getAuthMe();
          setCurrentUser(user);
        } catch {
          // Token is invalid/expired
          setAuthToken(null);
          setCurrentUser(null);
        }
      }
    };
    initAuth();

    // Listen to unauthorized event dispatched by api.ts
    const handleUnauthorized = () => {
      setCurrentUser(null);
      setAuthToken(null);
      addToast('warning', 'Session expired or authentication required. Please sign in.');
      setIsAuthModalOpen(true);
    };

    window.addEventListener('shopops-auth-unauthorized', handleUnauthorized);
    return () => window.removeEventListener('shopops-auth-unauthorized', handleUnauthorized);
  }, [addToast]);

  const loadGlobalOverviewData = useCallback(async () => {
    try {
      setIsRefreshing(true);
      setOverviewError(null);

      // Check health (Public endpoint)
      try {
        await checkBackendHealth();
        setBackendOnline(true);
      } catch {
        setBackendOnline(false);
      }

      // If not authenticated, prompt sign-in instead of spamming 401s
      if (!getAuthToken()) {
        setAnalysis(null);
        setPendingApprovals(null);
        setTasks(null);
        return;
      }

      // Fetch overview metrics in parallel
      const [analysisRes, approvalsRes, tasksRes] = await Promise.allSettled([
        getInventoryAnalysis(),
        listApprovals({ status: 'pending', limit: 100 }),
        listTasks({ limit: 100 }),
      ]);

      if (analysisRes.status === 'fulfilled') {
        setAnalysis(analysisRes.value);
      } else {
        setOverviewError(analysisRes.reason?.message || 'Failed to load inventory analysis');
      }

      if (approvalsRes.status === 'fulfilled') {
        setPendingApprovals(approvalsRes.value);
      }

      if (tasksRes.status === 'fulfilled') {
        setTasks(tasksRes.value);
      }
    } catch (err: any) {
      setOverviewError(err.message || 'Error communicating with backend');
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadGlobalOverviewData();
  }, [loadGlobalOverviewData, currentUser]);

  const handleSignOut = () => {
    signOutFromSupabase();
    setAuthToken(null);
    setCurrentUser(null);
    setAnalysis(null);
    setPendingApprovals(null);
    setTasks(null);
    addToast('info', 'Store owner signed out.');
  };

  const pendingCount = pendingApprovals?.total ?? 0;

  return (
    <div className="app-layout">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingApprovalsCount={pendingCount}
        backendOnline={backendOnline}
        onRefresh={loadGlobalOverviewData}
        isRefreshing={isRefreshing}
        currentUser={currentUser}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onSignOut={handleSignOut}
      />

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthenticated={(u) => {
          setCurrentUser(u);
          addToast('success', `Authenticated as ${u.email || 'Store Owner'}`);
          loadGlobalOverviewData();
        }}
      />

      <main className="main-content">
        {!currentUser && (
          <div className="alert-box alert-warning" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <strong>Store Owner Authentication Required:</strong> You are currently unauthenticated.
              Protected APIs (inventory, approvals, reorder tasks, and AI insights) require an authorized store owner session.
            </div>
            <button
              className="btn btn-sm btn-primary"
              style={{ marginLeft: '1rem', whiteSpace: 'nowrap' }}
              onClick={() => setIsAuthModalOpen(true)}
            >
              Sign In Now
            </button>
          </div>
        )}

        {activeTab === 'overview' && (
          <OverviewSection
            analysis={analysis}
            pendingApprovals={pendingApprovals}
            tasks={tasks}
            loading={isRefreshing}
            error={overviewError}
            onNavigateTab={setActiveTab}
            onRefresh={loadGlobalOverviewData}
          />
        )}

        {activeTab === 'inventory' && (
          <InventorySection
            onNotify={addToast}
          />
        )}

        {activeTab === 'analysis' && (
          <AnalysisSection
            onNotify={addToast}
            onNavigateToApprovals={() => setActiveTab('approvals')}
          />
        )}

        {activeTab === 'agent' && (
          <AgentSection
            onNotify={addToast}
          />
        )}

        {activeTab === 'approvals' && (
          <ApprovalsSection
            onNotify={addToast}
            onTaskCreated={() => {
              loadGlobalOverviewData();
            }}
          />
        )}

        {activeTab === 'tasks' && (
          <TasksSection
            onNotify={addToast}
          />
        )}
      </main>

      <footer className="app-footer">
        <div className="footer-container">
          <p>
            <strong>ShopOps Agent</strong> &mdash; Autonomous retail inventory & operations assistant with deterministic guardrails.
          </p>
          <p className="footer-subtext">
            Non-destructive MVP &bull; Human-in-the-loop approvals &bull; Grounded Gemini AI &bull; Supabase Auth &amp; PostgreSQL
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
