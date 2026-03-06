import { useState } from "react";
import { motion } from "framer-motion";
import { Check, X, MoreVertical, ExternalLink, RefreshCw, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { connectLimb, disconnectLimb } from "@/lib/api";
import { toast } from "sonner";
import { GmailConnectModal } from "./GmailConnectModal";
import { CalendarConnectModal } from "./CalendarConnectModal";
import { DriveConnectModal } from "./DriveConnectModal";

interface ConnectionCardProps {
    limb: {
        id: string;
        name: string;
        description: string;
        icon: string;
        status: string;
        toolsCount: number;
    };
    index: number;
    onRefresh: () => void;
}

// Configuration for each limb's connection method
const LIMB_CONFIG: Record<string, { type: "token" | "oauth" | "apikey"; envVar?: string; helpUrl?: string }> = {
    notion: { type: "token", envVar: "NOTION_TOKEN", helpUrl: "https://www.notion.so/my-integrations" },
    slack: { type: "token", envVar: "SLACK_BOT_TOKEN", helpUrl: "https://api.slack.com/apps" },
    gmail: { type: "oauth", helpUrl: "https://console.cloud.google.com/" },
    calendar: { type: "oauth", helpUrl: "https://console.cloud.google.com/" },
    github: { type: "token", envVar: "Personal Access Token (Classic)", helpUrl: "https://github.com/settings/tokens" },
    mongodb: { type: "apikey", envVar: "MONGODB_URI", helpUrl: "https://cloud.mongodb.com/v2#/clusters" },
    googledrive: { type: "oauth", helpUrl: "https://console.cloud.google.com/" },
    filesystem: { type: "token", envVar: "LOCAL_PATH" },
};

export function ConnectionCard({ limb, index, onRefresh }: ConnectionCardProps) {
    const [isConnecting, setIsConnecting] = useState(false);
    const [showConnectModal, setShowConnectModal] = useState(false);
    const [showDisconnectConfirm, setShowDisconnectConfirm] = useState(false);
    const [showGmailModal, setShowGmailModal] = useState(false);
    const [showCalendarModal, setShowCalendarModal] = useState(false);
    const [showDriveModal, setShowDriveModal] = useState(false);
    const [tokenInput, setTokenInput] = useState("");
    const [teamIdInput, setTeamIdInput] = useState("");

    const isConnected = limb.status === "active";
    const config = LIMB_CONFIG[limb.id] || { type: "token" };

    const handleConnect = async () => {
        if (limb.id === "gmail") {
            setShowGmailModal(true);
            return;
        }

        if (limb.id === "calendar") {
            setShowCalendarModal(true);
            return;
        }

        if (limb.id === "googledrive") {
            setShowDriveModal(true);
            return;
        }

        if (config.type === "oauth") {
            // TODO: Implement OAuth flow
            window.open(config.helpUrl, "_blank");
            return;
        }
        setShowConnectModal(true);
    };

    const handleSubmitToken = async () => {
        setIsConnecting(true);
        try {
            // Always send as 'token' to match backend ConnectionRequest model
            const payload: Record<string, string> = { token: tokenInput };
            if (limb.id === "slack" && teamIdInput) {
                payload.team_id = teamIdInput;
            }
            const result = await connectLimb(limb.id, payload);

            if (result.success) {
                toast.success(`Connected to ${limb.name}`);
                setShowConnectModal(false);
                setTokenInput("");
                onRefresh();
            } else {
                toast.error(result.error || "Failed to connect");
            }
        } catch (error) {
            console.error("Failed to connect:", error);
            toast.error("Connection failed");
        } finally {
            setIsConnecting(false);
        }
    };

    const handleDisconnect = async () => {
        setIsConnecting(true);
        try {
            const result = await disconnectLimb(limb.id);

            if (result.success) {
                toast.success(`Disconnected from ${limb.name}`);
                setShowDisconnectConfirm(false);
                onRefresh();
            } else {
                toast.error(result.error || "Failed to disconnect");
            }
        } catch (error) {
            console.error("Failed to disconnect:", error);
            toast.error("Disconnect failed");
        } finally {
            setIsConnecting(false);
        }
    };

    return (
        <>
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`
          relative p-4 rounded-xl border transition-all duration-200
          ${isConnected
                        ? "bg-success/5 border-success/30 hover:border-success/50"
                        : "bg-card/50 border-border/30 hover:border-border/50"
                    }
        `}
            >
                <div className="flex items-start gap-3">
                    {/* Icon */}
                    <div className={`
            w-12 h-12 rounded-lg flex items-center justify-center text-2xl
            ${isConnected ? "bg-success/10" : "bg-muted/50"}
          `}>
                        {limb.icon}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-foreground">{limb.name}</h3>
                            {isConnected ? (
                                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-success/20 text-success">
                                    <Check className="w-3 h-3" />
                                    Connected
                                </span>
                            ) : (
                                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-muted text-muted-foreground">
                                    <X className="w-3 h-3" />
                                    Offline
                                </span>
                            )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-0.5 truncate">
                            {limb.description}
                        </p>
                        {isConnected && limb.toolsCount > 0 && (
                            <p className="text-xs text-muted-foreground mt-1">
                                {limb.toolsCount} tools available
                            </p>
                        )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                        {!isConnected ? (
                            <Button
                                size="sm"
                                onClick={handleConnect}
                                className="bg-primary hover:bg-primary/90"
                            >
                                Connect
                            </Button>
                        ) : (
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="icon" className="h-8 w-8">
                                        <MoreVertical className="w-4 h-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                    <DropdownMenuItem onClick={onRefresh}>
                                        <RefreshCw className="w-4 h-4 mr-2" />
                                        Refresh Status
                                    </DropdownMenuItem>
                                    {config.helpUrl && (
                                        <DropdownMenuItem onClick={() => window.open(config.helpUrl, "_blank")}>
                                            <ExternalLink className="w-4 h-4 mr-2" />
                                            Open {limb.name}
                                        </DropdownMenuItem>
                                    )}
                                    <DropdownMenuItem
                                        onClick={() => setShowDisconnectConfirm(true)}
                                        className="text-destructive focus:text-destructive"
                                    >
                                        <X className="w-4 h-4 mr-2" />
                                        Disconnect
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        )}
                    </div>
                </div>
            </motion.div>

            {/* Connect Modal */}
            <Dialog open={showConnectModal} onOpenChange={setShowConnectModal}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <span className="text-2xl">{limb.icon}</span>
                            Connect to {limb.name}
                        </DialogTitle>
                        <DialogDescription>
                            Enter your {config.type === "apikey" ? "API key" : "access token"} to connect.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="token">
                                {config.envVar || "Token"}
                            </Label>
                            <Input
                                id="token"
                                type="password"
                                placeholder={`Enter your ${limb.name} token...`}
                                value={tokenInput}
                                onChange={(e) => setTokenInput(e.target.value)}
                                className="font-mono"
                            />
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                                🔒 Stored securely and never shown again.
                            </p>
                        </div>

                        {limb.id === "slack" && (
                            <div className="space-y-2">
                                <Label htmlFor="teamId">Team ID (Required)</Label>
                                <Input
                                    id="teamId"
                                    placeholder="Starting with T..."
                                    value={teamIdInput}
                                    onChange={(e) => setTeamIdInput(e.target.value)}
                                    className="font-mono"
                                />
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    Found in your Slack Workspace URL (e.g., app.slack.com/client/T12345/...)
                                </p>
                            </div>
                        )}
                        {config.helpUrl && (
                            <Button variant="link" size="sm" className="p-0 h-auto" asChild>
                                <a href={config.helpUrl} target="_blank" rel="noopener noreferrer">
                                    <ExternalLink className="w-3 h-3 mr-1" />
                                    Where do I find this?
                                </a>
                            </Button>
                        )}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowConnectModal(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleSubmitToken} disabled={!tokenInput || isConnecting}>
                            {isConnecting ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Connecting...
                                </>
                            ) : (
                                "Connect"
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Disconnect Confirmation */}
            <Dialog open={showDisconnectConfirm} onOpenChange={setShowDisconnectConfirm}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Disconnect {limb.name}?</DialogTitle>
                        <DialogDescription>
                            This will revoke Nexus's access to {limb.name}. You can reconnect anytime.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowDisconnectConfirm(false)}>
                            Cancel
                        </Button>
                        <Button variant="destructive" onClick={handleDisconnect} disabled={isConnecting}>
                            {isConnecting ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Disconnecting...
                                </>
                            ) : (
                                "Disconnect"
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
            <GmailConnectModal
                isOpen={showGmailModal}
                onClose={() => setShowGmailModal(false)}
                onSuccess={onRefresh}
            />
            <CalendarConnectModal
                isOpen={showCalendarModal}
                onClose={() => setShowCalendarModal(false)}
                onSuccess={onRefresh}
            />
            <DriveConnectModal
                isOpen={showDriveModal}
                onClose={() => setShowDriveModal(false)}
                onSuccess={onRefresh}
            />
        </>
    );
}
