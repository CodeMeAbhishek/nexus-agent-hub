import { useState } from "react";
import { motion } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Lock, ArrowRight, Loader2, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
    const navigate = useNavigate();
    const { login, signup, authStatus } = useAuth();

    const [isSignup, setIsSignup] = useState(false);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccessMessage(null);
        setIsLoading(true);

        try {
            if (isSignup) {
                await signup(email, password);
            } else {
                await login(email, password);
            }
            navigate("/");
        } catch (err) {
            // Check if this is an email confirmation message (success, not error)
            if (err instanceof Error && (err as Error & { isEmailConfirmation?: boolean }).isEmailConfirmation) {
                setSuccessMessage(err.message);
                setIsSignup(false); // Switch to sign-in mode
            } else {
                setError(err instanceof Error ? err.message : "Authentication failed");
            }
        } finally {
            setIsLoading(false);
        }
    };

    // If auth is not configured, show a message
    if (authStatus === "not_configured") {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/30 p-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="max-w-md w-full bg-card/50 border border-border/30 rounded-2xl p-8 text-center"
                >
                    <div className="w-16 h-16 mx-auto rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center text-2xl font-bold mb-6">
                        N
                    </div>
                    <h1 className="text-2xl font-bold mb-2">Authentication Not Configured</h1>
                    <p className="text-muted-foreground mb-6">
                        Supabase is not set up yet. You can use the app without authentication for now,
                        or configure Supabase in your backend environment.
                    </p>
                    <Button asChild>
                        <Link to="/">
                            Continue without login
                            <ArrowRight className="w-4 h-4 ml-2" />
                        </Link>
                    </Button>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/30 p-6">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="max-w-md w-full"
            >
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="w-16 h-16 mx-auto rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center text-2xl font-bold mb-4">
                        N
                    </div>
                    <h1 className="text-3xl font-bold">Welcome to Nexus</h1>
                    <p className="text-muted-foreground mt-2">
                        {isSignup ? "Create your account" : "Sign in to your account"}
                    </p>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="bg-card/50 border border-border/30 rounded-2xl p-6 space-y-4">
                        {/* Error */}
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive text-sm"
                            >
                                <AlertCircle className="w-4 h-4 shrink-0" />
                                {error}
                            </motion.div>
                        )}

                        {/* Success (email confirmation) */}
                        {successMessage && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex items-center gap-2 p-3 rounded-lg bg-success/10 text-success text-sm"
                            >
                                <CheckCircle className="w-4 h-4 shrink-0" />
                                {successMessage}
                            </motion.div>
                        )}

                        {/* Email */}
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="you@company.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="pl-10"
                                    required
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                <Input
                                    id="password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="pl-10"
                                    minLength={6}
                                    required
                                />
                            </div>
                        </div>

                        {/* Submit */}
                        <Button type="submit" className="w-full" disabled={isLoading}>
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    {isSignup ? "Creating account..." : "Signing in..."}
                                </>
                            ) : (
                                <>
                                    {isSignup ? "Create Account" : "Sign In"}
                                    <ArrowRight className="w-4 h-4 ml-2" />
                                </>
                            )}
                        </Button>
                    </div>

                    {/* Toggle */}
                    <p className="text-center text-sm text-muted-foreground">
                        {isSignup ? "Already have an account?" : "Don't have an account?"}{" "}
                        <button
                            type="button"
                            onClick={() => {
                                setIsSignup(!isSignup);
                                setError(null);
                            }}
                            className="text-primary hover:underline font-medium"
                        >
                            {isSignup ? "Sign in" : "Sign up"}
                        </button>
                    </p>

                    {/* Skip */}
                    <div className="text-center">
                        <Link
                            to="/"
                            className="text-sm text-muted-foreground hover:text-foreground"
                        >
                            Skip for now →
                        </Link>
                    </div>
                </form>
            </motion.div>
        </div>
    );
}
