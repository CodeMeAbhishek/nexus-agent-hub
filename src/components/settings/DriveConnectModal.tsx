import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { exchangeDriveToken } from "@/lib/api";

interface DriveConnectModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export function DriveConnectModal({ isOpen, onClose, onSuccess }: DriveConnectModalProps) {
    const [step, setStep] = useState<1 | 2 | 3>(1);
    const [credsJson, setCredsJson] = useState("");
    const [authCode, setAuthCode] = useState("");
    const [authUrl, setAuthUrl] = useState("");
    const [clientConfig, setClientConfig] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const reset = () => {
        setStep(1);
        setCredsJson("");
        setAuthCode("");
        setAuthUrl("");
        setClientConfig(null);
        setLoading(false);
        setError("");
        onClose();
    };

    const handleStep1 = () => {
        try {
            const parsed = JSON.parse(credsJson);
            // Detect shape: could be {installed: {...}} or {web: {...}}
            const content = parsed.installed || parsed.web;
            if (!content || !content.client_id) {
                setError("Invalid credentials.json — missing client_id");
                return;
            }

            setClientConfig(parsed);

            // Build the auth URL
            const redirectUri = "urn:ietf:wg:oauth:2.0:oob";
            const scope = encodeURIComponent("https://www.googleapis.com/auth/drive.readonly");
            const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${content.client_id}&redirect_uri=${redirectUri}&response_type=code&scope=${scope}&access_type=offline`;

            setAuthUrl(url);
            setError("");
            setStep(2);
        } catch {
            setError("Invalid JSON. Please paste valid credentials.json content.");
        }
    };

    const handleStep3 = async () => {
        if (!authCode.trim()) {
            setError("Please enter the authorization code.");
            return;
        }

        setLoading(true);
        setError("");

        try {
            const result = await exchangeDriveToken(authCode.trim(), clientConfig);
            if (result.success) {
                onSuccess();
                reset();
            } else {
                setError(result.message || "Failed to connect Google Drive.");
            }
        } catch (e: any) {
            setError(e.message || "An error occurred.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && reset()}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Connect Google Drive</DialogTitle>
                    <DialogDescription>
                        {step === 1 && "Step 1 of 3: Paste your Google OAuth credentials"}
                        {step === 2 && "Step 2 of 3: Authorize with Google"}
                        {step === 3 && "Step 3 of 3: Enter the authorization code"}
                    </DialogDescription>
                </DialogHeader>

                {error && (
                    <div className="text-sm text-red-500 bg-red-500/10 p-2 rounded">{error}</div>
                )}

                {step === 1 && (
                    <div className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                            Paste the contents of your <code>credentials.json</code> file from{" "}
                            <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-primary underline">
                                Google Cloud Console
                            </a>.
                            Make sure the <strong>Google Drive API</strong> is enabled.
                        </p>
                        <Textarea
                            placeholder='{"installed": {"client_id": "...", ...}}'
                            value={credsJson}
                            onChange={(e) => setCredsJson(e.target.value)}
                            rows={6}
                            className="font-mono text-xs"
                        />
                        <Button onClick={handleStep1} className="w-full" disabled={!credsJson.trim()}>
                            Next →
                        </Button>
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                            Click the button below to authorize Google Drive access. After granting permission, you'll receive an authorization code.
                        </p>
                        <Button
                            onClick={() => window.open(authUrl, "_blank")}
                            className="w-full"
                            variant="outline"
                        >
                            🔗 Open Google Authorization
                        </Button>
                        <Button onClick={() => setStep(3)} className="w-full">
                            I have the code →
                        </Button>
                    </div>
                )}

                {step === 3 && (
                    <div className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                            Paste the authorization code you received from Google below.
                        </p>
                        <Input
                            placeholder="Paste authorization code here"
                            value={authCode}
                            onChange={(e) => setAuthCode(e.target.value)}
                            className="font-mono"
                        />
                        <Button onClick={handleStep3} className="w-full" disabled={loading || !authCode.trim()}>
                            {loading ? "Connecting..." : "Connect Google Drive ✓"}
                        </Button>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
