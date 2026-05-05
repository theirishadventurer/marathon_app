import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { api, registerUnauthorizedHandler } from '@/api/client';
import type { LoginRequest, TokenResponse } from '@/api/types';
import { clearAuth, loadToken, saveAuth } from './secure-store';

interface AuthState {
  token: string | null;
  loading: boolean;
  login: (creds: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const stored = await loadToken();
      if (!cancelled) {
        setToken(stored);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const logout = useCallback(async () => {
    await clearAuth();
    setToken(null);
  }, []);

  useEffect(() => {
    registerUnauthorizedHandler(() => {
      setToken(null);
    });
  }, []);

  const login = useCallback(async (creds: LoginRequest) => {
    const res = await api.post<TokenResponse>('/auth/login', creds);
    await saveAuth(res.data.token, res.data.expires_at);
    setToken(res.data.token);
  }, []);

  const value = useMemo(
    () => ({ token, loading, login, logout }),
    [token, loading, login, logout],
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (ctx === null) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
