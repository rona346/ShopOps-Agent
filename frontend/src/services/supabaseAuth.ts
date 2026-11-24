/**
 * Supabase Web Client Authentication Service.
 * Direct, zero-external-dependency authentication against the Supabase GoTrue Auth API.
 * Securely manages access and refresh tokens, automatic token refresh, and sign-in/sign-out.
 */

const SUPABASE_URL: string =
  (import.meta as any).env?.VITE_SUPABASE_URL || '';
const SUPABASE_ANON_KEY: string =
  (import.meta as any).env?.VITE_SUPABASE_ANON_KEY || '';

const ACCESS_TOKEN_KEY = 'shopops_auth_token';
const REFRESH_TOKEN_KEY = 'shopops_refresh_token';
const EXPIRES_AT_KEY = 'shopops_token_expires_at';

export interface SupabaseAuthSession {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  expires_at: number;
  user: {
    id: string;
    email: string;
    role?: string;
  };
}

export function isSupabaseClientConfigured(): boolean {
  return Boolean(
    SUPABASE_URL &&
    SUPABASE_URL.trim() &&
    !SUPABASE_URL.includes('your_supabase') &&
    SUPABASE_ANON_KEY &&
    SUPABASE_ANON_KEY.trim() &&
    !SUPABASE_ANON_KEY.includes('your_supabase')
  );
}

export function getStoredAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function storeAuthSession(session: {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
}): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(ACCESS_TOKEN_KEY, session.access_token);
  if (session.refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
  }
  if (session.expires_in) {
    const expiresAt = Date.now() + session.expires_in * 1000;
    localStorage.setItem(EXPIRES_AT_KEY, expiresAt.toString());
  }
}

export function clearAuthSession(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
}

export function isTokenExpired(): boolean {
  if (typeof window === 'undefined') return true;
  const expiresAt = localStorage.getItem(EXPIRES_AT_KEY);
  if (!expiresAt) return false;
  // Consider expired if within 60 seconds of expiry
  return Date.now() > parseInt(expiresAt, 10) - 60000;
}

/**
 * Sign in with email and password via Supabase Auth GoTrue API.
 */
export async function signInWithSupabase(email: string, pass: string): Promise<string> {
  if (!isSupabaseClientConfigured()) {
    throw new Error(
      'Supabase client is not configured. Please check VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env.'
    );
  }

  const endpoint = `${SUPABASE_URL.replace(/\/$/, '')}/auth/v1/token?grant_type=password`;
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      apikey: SUPABASE_ANON_KEY,
    },
    body: JSON.stringify({ email: email.trim(), password: pass }),
  });

  const data = await response.json();
  if (!response.ok) {
    const msg =
      data.error_description ||
      data.msg ||
      data.message ||
      `Authentication failed (status ${response.status})`;
    throw new Error(msg);
  }

  storeAuthSession({
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_in: data.expires_in,
  });

  return data.access_token;
}

/**
 * Refresh access token using stored refresh token.
 */
export async function refreshSupabaseToken(): Promise<string | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken || !isSupabaseClientConfigured()) {
    return null;
  }

  const endpoint = `${SUPABASE_URL.replace(/\/$/, '')}/auth/v1/token?grant_type=refresh_token`;
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        apikey: SUPABASE_ANON_KEY,
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

/**
 * Sign out and clear stored sessions.
 */
export async function signOutFromSupabase(): Promise<void> {
  const token = getStoredAccessToken();
  clearAuthSession();

  if (isSupabaseClientConfigured() && token) {
    try {
      const endpoint = `${SUPABASE_URL.replace(/\/$/, '')}/auth/v1/logout`;
      await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${token}`,
        },
      });
    } catch {
      // Ignore network errors on logout
    }
  }
}
