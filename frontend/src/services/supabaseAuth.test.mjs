/**
 * Unit tests for frontend Supabase authentication, token management, and 401 reactive retry.
 * Executed with Node.js built-in test runner (node --test).
 */

import test from 'node:test';
import assert from 'node:assert/strict';

// Mock browser localStorage
const mockStorage = new Map();
global.localStorage = {
  getItem: (key) => mockStorage.get(key) || null,
  setItem: (key, val) => mockStorage.set(key, String(val)),
  removeItem: (key) => mockStorage.delete(key),
  clear: () => mockStorage.clear(),
};
global.window = {};

// Constant storage keys matching frontend/src/services/supabaseAuth.ts
const ACCESS_TOKEN_KEY = 'shopops_auth_token';
const REFRESH_TOKEN_KEY = 'shopops_refresh_token';
const EXPIRES_AT_KEY = 'shopops_token_expires_at';

function isSupabaseConfigured(url, key) {
  return Boolean(
    url &&
    url.trim() &&
    !url.includes('your_supabase') &&
    key &&
    key.trim() &&
    !key.includes('your_supabase')
  );
}

function storeAuthSession(session) {
  localStorage.setItem(ACCESS_TOKEN_KEY, session.access_token);
  if (session.refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
  }
  if (session.expires_in) {
    const expiresAt = Date.now() + session.expires_in * 1000;
    localStorage.setItem(EXPIRES_AT_KEY, expiresAt.toString());
  }
}

function clearAuthSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
}

function isTokenExpired() {
  const expiresAt = localStorage.getItem(EXPIRES_AT_KEY);
  if (!expiresAt) return false;
  return Date.now() > (parseInt(expiresAt, 10) - 60000);
}

async function refreshSupabaseToken(supabaseUrl, supabaseKey) {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken || !isSupabaseConfigured(supabaseUrl, supabaseKey)) {
    return null;
  }

  const endpoint = `${supabaseUrl.replace(/\/$/, '')}/auth/v1/token?grant_type=refresh_token`;
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        apikey: supabaseKey,
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearAuthSession();
      return null;
    }

    const data = await response.json();
    storeAuthSession({
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      expires_in: data.expires_in,
    });

    return data.access_token;
  } catch {
    return null;
  }
}

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `API request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Simulates request execution with proactive token refresh and reactive 401 retry,
 * matching frontend/src/services/api.ts request<T>().
 */
async function executeApiRequest(endpoint, options = {}, authContext) {
  let token = authContext.getAuthToken();

  // Proactive refresh before request if expired or within buffer
  if (token && authContext.isTokenExpired()) {
    const refreshed = await authContext.refreshSupabaseToken();
    if (refreshed) {
      token = refreshed;
    }
  }

  const url = `${authContext.apiBaseUrl}${endpoint}`;
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};
  const headers = {
    'Content-Type': 'application/json',
    ...authHeaders,
    ...(options.headers || {}),
  };

  try {
    let response = await fetch(url, { ...options, headers });

    // Reactive retry on 401: attempt token refresh once
    if (response.status === 401 && token) {
      const refreshed = await authContext.refreshSupabaseToken();
      if (refreshed) {
        token = refreshed;
        const retryHeaders = {
          ...headers,
          Authorization: `Bearer ${refreshed}`,
        };
        response = await fetch(url, { ...options, headers: retryHeaders });
      }
    }

    if (!response.ok) {
      let detail = `Error ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          detail = typeof errorData.detail === 'string'
            ? errorData.detail
            : JSON.stringify(errorData.detail);
        }
      } catch {
        // Fall back to status text
      }

      if (response.status === 401 && typeof authContext.onUnauthorized === 'function') {
        authContext.onUnauthorized();
      }

      throw new ApiError(response.status, detail);
    }

    if (response.status === 204) {
      return {};
    }

    return await response.json();
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(0, err.message || 'Network error connecting to backend service');
  }
}

// ==========================================
// Test Suites
// ==========================================

test('isSupabaseConfigured detects valid vs placeholder configurations', () => {
  assert.equal(isSupabaseConfigured('', ''), false);
  assert.equal(isSupabaseConfigured('https://your_supabase.co', 'key'), false);
  assert.equal(isSupabaseConfigured('https://xyz.supabase.co', 'your_supabase_anon_key'), false);
  assert.equal(isSupabaseConfigured('https://xyz.supabase.co', 'valid-anon-key-123'), true);
});

test('storeAuthSession and clearAuthSession manage token lifecycle', () => {
  mockStorage.clear();
  storeAuthSession({
    access_token: 'mock-access-token-abc',
    refresh_token: 'mock-refresh-token-xyz',
    expires_in: 3600,
  });

  assert.equal(localStorage.getItem(ACCESS_TOKEN_KEY), 'mock-access-token-abc');
  assert.equal(localStorage.getItem(REFRESH_TOKEN_KEY), 'mock-refresh-token-xyz');
  assert.ok(localStorage.getItem(EXPIRES_AT_KEY));

  assert.equal(isTokenExpired(), false);

  clearAuthSession();
  assert.equal(localStorage.getItem(ACCESS_TOKEN_KEY), null);
  assert.equal(localStorage.getItem(REFRESH_TOKEN_KEY), null);
  assert.equal(localStorage.getItem(EXPIRES_AT_KEY), null);
});

test('isTokenExpired returns true when token is expired or within 60s buffer', () => {
  mockStorage.clear();
  // Expired 1 hour ago
  localStorage.setItem(EXPIRES_AT_KEY, (Date.now() - 3600000).toString());
  assert.equal(isTokenExpired(), true);

  // Expiring in 30 seconds (within 60s buffer)
  localStorage.setItem(EXPIRES_AT_KEY, (Date.now() + 30000).toString());
  assert.equal(isTokenExpired(), true);

  // Fresh token expiring in 1 hour
  localStorage.setItem(EXPIRES_AT_KEY, (Date.now() + 3600000).toString());
  assert.equal(isTokenExpired(), false);
});

test('refreshSupabaseToken: successful refresh updates storage and returns new access token', async () => {
  mockStorage.clear();
  storeAuthSession({
    access_token: 'stale-access-token',
    refresh_token: 'valid-refresh-token-123',
    expires_in: 10,
  });

  const originalFetch = global.fetch;
  global.fetch = async (url, options) => {
    assert.match(url, /\/auth\/v1\/token\?grant_type=refresh_token/);
    assert.equal(options.method, 'POST');
    assert.equal(options.headers.apikey, 'test-anon-key');
    const body = JSON.parse(options.body);
    assert.equal(body.refresh_token, 'valid-refresh-token-123');

    return {
      ok: true,
      status: 200,
      json: async () => ({
        access_token: 'refreshed-access-token-789',
        refresh_token: 'new-refresh-token-999',
        expires_in: 3600,
      }),
    };
  };

  try {
    const result = await refreshSupabaseToken('https://test.supabase.co', 'test-anon-key');
    assert.equal(result, 'refreshed-access-token-789');
    assert.equal(localStorage.getItem(ACCESS_TOKEN_KEY), 'refreshed-access-token-789');
    assert.equal(localStorage.getItem(REFRESH_TOKEN_KEY), 'new-refresh-token-999');
    assert.equal(isTokenExpired(), false);
  } finally {
    global.fetch = originalFetch;
  }
});

test('refreshSupabaseToken: failed refresh (401/invalid) clears session and returns null', async () => {
  mockStorage.clear();
  storeAuthSession({
    access_token: 'expired-access-token',
    refresh_token: 'revoked-refresh-token',
    expires_in: 0,
  });

  const originalFetch = global.fetch;
  global.fetch = async () => {
    return {
      ok: false,
      status: 400,
      json: async () => ({ error: 'invalid_grant', message: 'Invalid Refresh Token' }),
    };
  };

  try {
    const result = await refreshSupabaseToken('https://test.supabase.co', 'test-anon-key');
    assert.equal(result, null);
    assert.equal(localStorage.getItem(ACCESS_TOKEN_KEY), null);
    assert.equal(localStorage.getItem(REFRESH_TOKEN_KEY), null);
    assert.equal(localStorage.getItem(EXPIRES_AT_KEY), null);
  } finally {
    global.fetch = originalFetch;
  }
});

test('refreshSupabaseToken: network error returns null without unhandled rejection', async () => {
  mockStorage.clear();
  storeAuthSession({
    access_token: 'some-access-token',
    refresh_token: 'some-refresh-token',
    expires_in: 3600,
  });

  const originalFetch = global.fetch;
  global.fetch = async () => {
    throw new Error('Network unreachable');
  };

  try {
    const result = await refreshSupabaseToken('https://test.supabase.co', 'test-anon-key');
    assert.equal(result, null);
  } finally {
    global.fetch = originalFetch;
  }
});

test('request 401 reactive retry: performs one-time retry with refreshed token on 401', async () => {
  mockStorage.clear();
  storeAuthSession({
    access_token: 'initial-stale-token',
    refresh_token: 'active-refresh-token',
    expires_in: 3600,
  });

  const calls = [];
  const originalFetch = global.fetch;
  global.fetch = async (url, options) => {
    calls.push({ url, options });

    // Call 1: Initial backend request -> 401 Unauthorized
    if (calls.length === 1) {
      assert.equal(options.headers.Authorization, 'Bearer initial-stale-token');
      return {
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'Token has expired' }),
      };
    }

    // Call 2: Refresh call -> 200 with new token
    if (calls.length === 2) {
      assert.match(url, /\/auth\/v1\/token\?grant_type=refresh_token/);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          access_token: 'new-valid-token-555',
          refresh_token: 'new-refresh-token-666',
          expires_in: 3600,
        }),
      };
    }

    // Call 3: Retried backend request -> 200 OK with new token
    if (calls.length === 3) {
      assert.equal(options.headers.Authorization, 'Bearer new-valid-token-555');
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', data: [1, 2, 3] }),
      };
    }

    throw new Error('Unexpected extra call');
  };

  try {
    const authContext = {
      apiBaseUrl: 'https://shopops-backend.example.com',
      getAuthToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
      isTokenExpired: () => false,
      refreshSupabaseToken: () => refreshSupabaseToken('https://test.supabase.co', 'test-anon-key'),
      onUnauthorized: () => {},
    };

    const res = await executeApiRequest('/api/v1/inventory', {}, authContext);
    assert.deepEqual(res, { status: 'success', data: [1, 2, 3] });
    assert.equal(calls.length, 3); // 1 initial backend + 1 refresh + 1 retry backend
    assert.equal(localStorage.getItem(ACCESS_TOKEN_KEY), 'new-valid-token-555');
  } finally {
    global.fetch = originalFetch;
  }
});

test('request 401 reactive retry: prevents infinite retries when retried request also returns 401', async () => {
  mockStorage.clear();
  storeAuthSession({
    access_token: 'initial-stale-token',
    refresh_token: 'active-refresh-token',
    expires_in: 3600,
  });

  const calls = [];
  let unauthorizedDispatched = false;
  const originalFetch = global.fetch;

  global.fetch = async (url, options) => {
    calls.push({ url, options });

    // Call 1: Initial backend request -> 401 Unauthorized
    if (calls.length === 1) {
      return {
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'Token expired' }),
      };
    }

    // Call 2: Refresh token call -> 200 OK
    if (calls.length === 2) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          access_token: 'second-token-still-rejected',
          refresh_token: 'new-refresh-token',
          expires_in: 3600,
        }),
      };
    }

    // Call 3: Retried backend request -> Still 401 Unauthorized
    if (calls.length === 3) {
      return {
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'User account disabled' }),
      };
    }

    // If an infinite loop were present, call 4+ would happen
    throw new Error(`Infinite loop detected: called fetch ${calls.length} times`);
  };

  try {
    const authContext = {
      apiBaseUrl: 'https://shopops-backend.example.com',
      getAuthToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
      isTokenExpired: () => false,
      refreshSupabaseToken: () => refreshSupabaseToken('https://test.supabase.co', 'test-anon-key'),
      onUnauthorized: () => {
        unauthorizedDispatched = true;
      },
    };

    await assert.rejects(
      async () => {
        await executeApiRequest('/api/v1/inventory', {}, authContext);
      },
      (err) => {
        assert.ok(err instanceof ApiError);
        assert.equal(err.status, 401);
        assert.match(err.detail, /User account disabled/);
        return true;
      }
    );

    // Exactly 3 calls: 1 initial request + 1 refresh + 1 retry (NO further calls)
    assert.equal(calls.length, 3);
    assert.equal(unauthorizedDispatched, true);
  } finally {
    global.fetch = originalFetch;
  }
});

test('request 401 reactive retry: aborts retry when token refresh fails', async () => {
  mockStorage.clear();
  storeAuthSession({
    access_token: 'initial-stale-token',
    refresh_token: 'invalid-refresh-token',
    expires_in: 3600,
  });

  const calls = [];
  let unauthorizedDispatched = false;
  const originalFetch = global.fetch;

  global.fetch = async (url, options) => {
    calls.push({ url, options });

    // Call 1: Initial backend request -> 401
    if (calls.length === 1) {
      return {
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'Token signature invalid' }),
      };
    }

    // Call 2: Refresh attempt -> fails with 401
    if (calls.length === 2) {
      return {
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ error: 'invalid_grant' }),
      };
    }

    throw new Error('Unexpected extra call after failed refresh');
  };

  try {
    const authContext = {
      apiBaseUrl: 'https://shopops-backend.example.com',
      getAuthToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
      isTokenExpired: () => false,
      refreshSupabaseToken: () => refreshSupabaseToken('https://test.supabase.co', 'test-anon-key'),
      onUnauthorized: () => {
        unauthorizedDispatched = true;
      },
    };

    await assert.rejects(
      async () => {
        await executeApiRequest('/api/v1/inventory', {}, authContext);
      },
      (err) => {
        assert.ok(err instanceof ApiError);
        assert.equal(err.status, 401);
        assert.match(err.detail, /Token signature invalid/);
        return true;
      }
    );

    // Exactly 2 calls: 1 backend request + 1 failed refresh attempt. NO retry backend request.
    assert.equal(calls.length, 2);
    assert.equal(unauthorizedDispatched, true);
    // Session is cleared
    assert.equal(localStorage.getItem(ACCESS_TOKEN_KEY), null);
  } finally {
    global.fetch = originalFetch;
  }
});
