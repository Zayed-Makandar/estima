import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface User {
    id: number;
    username: string;
    email: string;
    role: "admin" | "normal";
    is_active: boolean;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isAdmin: boolean;
    login: (usernameOrEmail: string, password: string) => Promise<{ success: boolean; error?: string }>;
    logout: () => void;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = "http://localhost:8000";

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    // Initialize from localStorage
    useEffect(() => {
        const storedToken = localStorage.getItem("estim_token");
        if (storedToken) {
            setToken(storedToken);
            fetchUser(storedToken);
        } else {
            setLoading(false);
        }
    }, []);

    const fetchUser = async (authToken: string) => {
        try {
            const resp = await fetch(`${API_BASE}/auth/me`, {
                headers: {
                    Authorization: `Bearer ${authToken}`,
                },
            });
            if (resp.ok) {
                const userData = await resp.json();
                setUser(userData);
            } else {
                // Token invalid, clear it
                localStorage.removeItem("estim_token");
                setToken(null);
            }
        } catch (e) {
            console.error("Failed to fetch user:", e);
            localStorage.removeItem("estim_token");
            setToken(null);
        } finally {
            setLoading(false);
        }
    };

    const login = async (usernameOrEmail: string, password: string): Promise<{ success: boolean; error?: string }> => {
        try {
            const resp = await fetch(`${API_BASE}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    username_or_email: usernameOrEmail,
                    password: password,
                }),
            });

            if (!resp.ok) {
                const data = await resp.json();
                return { success: false, error: data.detail || "Login failed" };
            }

            const data = await resp.json();
            const newToken = data.access_token;

            // Save token
            localStorage.setItem("estim_token", newToken);
            setToken(newToken);

            // Fetch user info
            await fetchUser(newToken);

            return { success: true };
        } catch (e: any) {
            return { success: false, error: e.message || "Network error" };
        }
    };

    const logout = () => {
        localStorage.removeItem("estim_token");
        setToken(null);
        setUser(null);
    };

    const value: AuthContextType = {
        user,
        token,
        isAuthenticated: !!user && !!token,
        isAdmin: user?.role === "admin",
        login,
        logout,
        loading,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
