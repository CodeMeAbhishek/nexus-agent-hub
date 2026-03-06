import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { exchangeCalendarToken } from "@/lib/api";
import { toast } from "sonner";
import { Loader2, ExternalLink } from "lucide-react";

interface CalendarConnectModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export function CalendarConnectModal({ isOpen, onClose, onSuccess }: CalendarConnectModalProps) {
    const [step, setStep] = useState<1 | 2 | 3>(1);
    const [credsJson, setCredsJson] = useState("");
    const [authCode, setAuthCode] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [authUrl, setAuthUrl] = useState("");

    const handleStep1 = () => {
        try {
            const data = JSON.parse(credsJson);
            const content = data.installed || data.web;
            if (!content || !content.client_id) {
                toast.error("Invalid credentials.json. Look for 'installed' or 'web' key with 'client_id'.");
                return;
            }

            const scope = "https://www.googleapis.com/auth/calendar";
            const redirectUri = "urn:ietf:wg:oauth:2.0:oob";
            const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${content.client_id}&redirect_uri=${redirectUri}&response_type=code&scope=${scope}&access_type=offline`;

            setAuthUrl(url);
            setStep(2);
        } catch (e) {
            toast.error("Invalid JSON format");
        }
    };

    const handleStep3 = async () => {
        setIsSubmitting(true);
        try {
            const clientConfig = JSON.parse(credsJson);
            const result = await exchangeCalendarToken(authCode, clientConfig);

            if (result.success) {
                toast.success("Google Calendar connected successfully!");
                onSuccess();
                onClose();
            } else {
                toast.error(result.message || "Failed to connect");
            }
        } catch (e) {
            toast.error("An error occurred");
        } finally {
            setIsSubmitting(false);
        }
    };

    const reset = () => {
        setStep(1);
        setCredsJson("");
        setAuthCode("");
        setAuthUrl("");
        onClose();
    };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && reset()}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Connect Google Calendar</DialogTitle>
                    <DialogDescription>
                        Follow these steps to authorize Nexus to access your Google Calendar.
                    </DialogDescription>
                </DialogHeader>

                {step === 1 && (
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Step 1: Paste credentials.json</Label>
                            <p className="text-xs text-muted-foreground">
                                Download <code>credentials.json</code> from Google Cloud Console (OAuth 2.0 Client ID).
                                Enable the <b>Google Calendar API</b> in your project first.
                            </p>
                            <Textarea
                                placeholder='{"installed": {"client_id": "...", ...}}'
                                value={credsJson}
                                onChange={(e) => setCredsJson(e.target.value)}
                                className="font-mono text-xs h-32"
                            />
                        </div>
                        <DialogFooter>
                            <Button onClick={handleStep1} disabled={!credsJson}>
                                Next
                            </Button>
                        </DialogFooter>
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Step 2: Authorize Nexus</Label>
                            <p className="text-sm text-muted-foreground">
                                Click the link below to open Google Login. Authorize the app, then copy the <b>authorization code</b> shown.
                            </p>
                            <Button variant="outline" className="w-full gap-2" asChild>
                                <a href={authUrl} target="_blank" rel="noopener noreferrer">
                                    <ExternalLink className="h-4 w-4" />
                                    Open Authorization Link
                                </a>
                            </Button>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
                            <Button onClick={() => setStep(3)}>
                                I have the code
                            </Button>
                        </DialogFooter>
                    </div>
                )}

                {step === 3 && (
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Step 3: Enter Authorization Code</Label>
                            <Input
                                placeholder="4/0A..."
                                value={authCode}
                                onChange={(e) => setAuthCode(e.target.value)}
                            />
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
                            <Button onClick={handleStep3} disabled={!authCode || isSubmitting}>
                                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Connect Calendar
                            </Button>
                        </DialogFooter>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
