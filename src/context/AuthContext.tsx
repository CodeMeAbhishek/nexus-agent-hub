import { createContext, useContext, useState, useEffect, ReactNode } from "react";

const API_BASE = import.meta.env.VITE_API_URL ??
    (typeof window !== "undefined"
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : "http://localhost:8000");

// ============================================================================
// Types
// ============================================================================

interface User {
    id: string;
    email: string;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<void>;
    signup: (email: string, password: string) => Promise<void>;
    logout: () => void;
    authStatus: "configured" | "not_configured" | "checking";
}

// ============================================================================
// Context
// ============================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ============================================================================
// Provider
// ============================================================================

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(() =>
        localStorage.getItem("auth_token")
    );
    const [isLoading, setIsLoading] = useState(true);
    const [authStatus, setAuthStatus] = useState<"configured" | "not_configured" | "checking">("checking");

    // Check if auth is configured
    useEffect(() => {
        fetch(`${API_BASE}/api/auth/status`)
            .then(res => res.json())
            .then(json => {
                const data = json.data;
                setAuthStatus(data.configured ? "configured" : "not_configured");
            })
            .catch(() => {
                setAuthStatus("not_configured");
            });
    }, []);

    // Verify token and get user on mount
    useEffect(() => {
        if (!token) {
            setIsLoading(false);
            return;
        }

        fetch(`${API_BASE}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then(res => {
                if (!res.ok) throw new Error("Invalid token");
                return res.json();
            })
            .then(json => {
                const data = json.data;
                setUser({ id: data.id, email: data.email });
            })
            .catch(() => {
                // Token invalid, clear it
                localStorage.removeItem("auth_token");
                setToken(null);
                setUser(null);
            })
            .finally(() => {
                setIsLoading(false);
            });
    }, [token]);

    const login = async (email: string, password: string) => {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: "Login failed" }));
            throw new Error(error.detail || "Login failed");
        }

        const json = await res.json();
        const data = json.data;
        localStorage.setItem("auth_token", data.access_token);
        setToken(data.access_token);
        setUser(data.user);
    };

    const signup = async (email: string, password: string) => {
        const res = await fetch(`${API_BASE}/api/auth/signup`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: "Signup failed" }));
            throw new Error(error.detail || "Signup failed");
        }

        const json = await res.json();
        const data = json.data;

        // Check if email confirmation is required
        if (data.email_confirmation_required) {
            // Throw a special error that Login.tsx can catch and display as success
            const confirmError = new Error(data.message || "Please check your email to confirm your account.");
            (confirmError as Error & { isEmailConfirmation?: boolean }).isEmailConfirmation = true;
            throw confirmError;
        }

        // If we have a token, sign in immediately
        localStorage.setItem("auth_token", data.access_token);
        setToken(data.access_token);
        setUser(data.user);
    };

    const logout = () => {
        localStorage.removeItem("auth_token");
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                token,
                isLoading,
                isAuthenticated: !!user,
                login,
                signup,
                logout,
                authStatus,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

// ============================================================================
// Hook
// ============================================================================

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
