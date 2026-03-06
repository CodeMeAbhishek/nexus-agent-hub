import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Plug, Settings2, Info, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConnectionCard } from "@/components/settings/ConnectionCard";
import { useQuery } from "@tanstack/react-query";
import { getUserConnections, ApiLimb, UserConnection } from "@/lib/api";

// Define all available limbs (including offline ones)
const ALL_LIMBS = [
    { id: "notion", name: "Notion", description: "Access pages, databases, and tasks", icon: "📝", category: "productivity" },
    { id: "slack", name: "Slack", description: "Send messages and read channels", icon: "💬", category: "communication" },
    { id: "gmail", name: "Gmail", description: "Read and send emails", icon: "📧", category: "communication" },
    { id: "calendar", name: "Google Calendar", description: "View and create calendar events", icon: "📅", category: "productivity" },
    { id: "github", name: "GitHub", description: "Manage repos, issues, and PRs", icon: "🐙", category: "developer" },
    { id: "mongodb", name: "MongoDB", description: "Query databases and collections", icon: "🍃", category: "developer" },
    { id: "googledrive", name: "Google Drive", description: "Search and read files", icon: "📁", category: "productivity" },
    { id: "filesystem", name: "Local Files", description: "Access local file system", icon: "💾", category: "developer" },
];

export default function SettingsPage() {
    const [activeTab, setActiveTab] = useState("connections");

    // Fetch current limb statuses for the user
    const { data: userConnections, isLoading, refetch } = useQuery({
        queryKey: ["user-connections"],
        queryFn: getUserConnections,
    });

    // Merge static limb definitions with user connection status
    const limbs = ALL_LIMBS.map((limb) => {
        const connection = userConnections?.find((c) => c.limb_id === limb.id);
        const isConnected = connection?.is_enabled ?? false;

        return {
            ...limb,
            status: isConnected ? "active" : "disconnected", // Use explicit active/disconnected status
            toolsCount: isConnected ? 10 : 0, // Placeholder tools count for now
        };
    });

    const connectedCount = limbs.filter((l) => l.status === "active").length;

    return (
        <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/30">
            {/* Header */}
            <header className="sticky top-0 z-50 border-b border-border/30 bg-card/80 backdrop-blur-xl">
                <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
                    <Link to="/">
                        <Button variant="ghost" size="icon" className="hover:bg-white/10">
                            <ArrowLeft className="w-5 h-5" />
                        </Button>
                    </Link>
                    <div>
                        <h1 className="text-xl font-bold text-foreground">Settings</h1>
                        <p className="text-sm text-muted-foreground">
                            Manage your integrations and preferences
                        </p>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-5xl mx-auto px-6 py-8">
                <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                    <TabsList className="bg-card/50 border border-border/30">
                        <TabsTrigger value="connections" className="gap-2">
                            <Plug className="w-4 h-4" />
                            Connections
                            <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-success/20 text-success">
                                {connectedCount}
                            </span>
                        </TabsTrigger>
                        <TabsTrigger value="preferences" className="gap-2">
                            <Settings2 className="w-4 h-4" />
                            Preferences
                        </TabsTrigger>
                        <TabsTrigger value="about" className="gap-2">
                            <Info className="w-4 h-4" />
                            About
                        </TabsTrigger>
                    </TabsList>

                    {/* Connections Tab */}
                    <TabsContent value="connections" className="space-y-6">
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="space-y-4"
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-lg font-semibold">Connected Services</h2>
                                    <p className="text-sm text-muted-foreground">
                                        Connect your tools to enable Nexus to access and automate them
                                    </p>
                                </div>
                                <Button variant="outline" size="sm" onClick={() => refetch()}>
                                    Refresh Status
                                </Button>
                            </div>

                            {isLoading ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {[1, 2, 3, 4].map((i) => (
                                        <div key={i} className="h-24 rounded-xl bg-card/50 animate-pulse" />
                                    ))}
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {limbs.map((limb, index) => (
                                        <ConnectionCard
                                            key={limb.id}
                                            limb={limb}
                                            index={index}
                                            onRefresh={refetch}
                                        />
                                    ))}
                                </div>
                            )}
                        </motion.div>
                    </TabsContent>

                    {/* Preferences Tab */}
                    <TabsContent value="preferences" className="space-y-6">
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="space-y-4"
                        >
                            <h2 className="text-lg font-semibold">Preferences</h2>
                            <div className="bg-card/50 border border-border/30 rounded-xl p-6">
                                <p className="text-muted-foreground text-center py-8">
                                    Preferences coming soon — theme, notifications, and default behaviors.
                                </p>
                            </div>
                        </motion.div>
                    </TabsContent>

                    {/* About Tab */}
                    <TabsContent value="about" className="space-y-6">
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="space-y-4"
                        >
                            <h2 className="text-lg font-semibold">About Nexus Agent</h2>
                            <div className="bg-card/50 border border-border/30 rounded-xl p-6 space-y-4">
                                <div className="flex items-center gap-4">
                                    <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center text-2xl font-bold">
                                        N
                                    </div>
                                    <div>
                                        <h3 className="text-xl font-bold">Nexus Agent Hub</h3>
                                        <p className="text-muted-foreground">Version 1.0.0</p>
                                    </div>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    Nexus is an autonomous AI teammate that connects your tools and automates
                                    workflows using natural language. Built for Tinkerthon 4.0 (TEC-4).
                                </p>
                                <div className="flex gap-2">
                                    <Button variant="outline" size="sm" asChild>
                                        <a href="https://github.com" target="_blank" rel="noopener noreferrer">
                                            <ExternalLink className="w-4 h-4 mr-2" />
                                            Documentation
                                        </a>
                                    </Button>
                                </div>
                            </div>
                        </motion.div>
                    </TabsContent>
                </Tabs>
            </main>
        </div>
    );
}
