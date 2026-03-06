import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

interface ProtectedRouteProps {
    children: React.ReactNode;
}

/**
 * Wrapper component that requires authentication.
 * Redirects to /login if not authenticated.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
    const { isAuthenticated, isLoading, authStatus } = useAuth();
    const location = useLocation();

    // Show loading while checking auth status
    if (isLoading || authStatus === "checking") {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    // If auth is not configured, allow access without login
    if (authStatus === "not_configured") {
        return <>{children}</>;
    }

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return <>{children}</>;
}
