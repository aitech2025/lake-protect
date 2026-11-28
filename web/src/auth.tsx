import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken, type User } from "./api";
import i18n from "./i18n";

type AuthState = { user: User | null; ready: boolean; login: (username: string) => Promise<User>; logout: () => void };

const AuthContext = createContext<AuthState>({ user: null, ready: false, login: async () => Promise.reject(), logout: () => {} });

function cachedUser(): User | null {
  try {
    const raw = localStorage.getItem("lp.user");
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getToken() ? cachedUser() : null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api<User>("/auth/me")
      .then((u) => setUser(u))
      .catch((err) => {
        // Offline: keep the cached user so the field app still opens. A refused token signs out.
        if (err?.status === 401) {
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (username: string) => {
    const out = await api<{ token: string; user: User }>("/auth/login", { json: { username } });
    setToken(out.token);
    try {
      localStorage.setItem("lp.user", JSON.stringify(out.user));
    } catch {
      /* convenience only */
    }
    setUser(out.user);
    if (out.user.language && out.user.language !== i18n.language) void i18n.changeLanguage(out.user.language);
    return out.user;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    try {
      localStorage.removeItem("lp.user");
    } catch {
      /* ignore */
    }
    setUser(null);
  }, []);

  return <AuthContext.Provider value={{ user, ready, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}

/** Officers start at the overview of what they may see (D-060); a field officer at their field visits (D-067). */
export function homeFor(role: string): string {
  return role === "field_officer" ? "/alerts" : "/dashboard";
}

type Who = { role: string } | null | undefined;

/** Four personas (D-067). The server decides every step; these only shape the screens. */
export function isAdmin(user: Who): boolean {
  return user?.role === "admin";
}
export function isSenior(user: Who): boolean {
  return user?.role === "senior_official";
}
export function isDistrictOfficer(user: Who): boolean {
  return user?.role === "district_officer";
}
export function isFieldOfficer(user: Who): boolean {
  return user?.role === "field_officer";
}
/** The admin and senior officials see the whole State. */
export function isStatewide(user: Who): boolean {
  return isAdmin(user) || isSenior(user);
}
/** The officers who work incidents: never the admin. */
export function isCasework(user: Who): boolean {
  return isSenior(user) || isDistrictOfficer(user);
}
