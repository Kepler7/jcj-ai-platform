import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { api } from '../lib/apiClient';

type Role = 'platform_admin' | 'school_admin' | 'teacher';

export type Me = {
  id: string;
  email: string;
  role: Role;
  school_id: string | null;
};

type AuthState = {
  me: Me | null;
  loading: boolean;
  token: string | null;
  signIn: (email: string, password: string) => Promise<string>;
  signOut: () => void;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthState | undefined>(undefined);

function getStoredToken(): string | null {
  return localStorage.getItem('access_token');
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshMe(tokenOverride?: string) {
    const t = tokenOverride ?? token;
    if (!t) {
      setMe(null);
      return;
    }

    const data = await api<Me>('/v1/auth/me', {
      auth: true,
      headers: { Authorization: `Bearer ${t}` }, // fuerza usar este token
    });

    setMe(data);
  }

  async function signIn(email: string, password: string): Promise<string> {
    const res = await api<{ access_token: string; token_type: string }>(
      '/v1/auth/login',
      {
        method: 'POST',
        body: { email, password },
        auth: false,
      }
    );

    localStorage.setItem('access_token', res.access_token);
    setToken(res.access_token);
    return res.access_token;
  }

  function signOut() {
    localStorage.removeItem('access_token');
    setToken(null);
    setMe(null);
  }

  useEffect(() => {
    (async () => {
      try {
        await refreshMe();
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const value = useMemo(
    () => ({ me, loading, token, signIn, signOut, refreshMe }),
    [me, loading, token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
