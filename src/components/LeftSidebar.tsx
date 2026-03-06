import { useState } from "react";
import { MessageSquare, LayoutGrid } from "lucide-react";
import { ChatSidebar } from "./ChatSidebar";
import { ToolsView } from "./ToolsView";

interface LeftSidebarProps {
    currentSessionId: string | null;
    onSelectSession: (id: string) => void;
    onNewChat: () => void;
    isMobileOpen?: boolean;
    onCloseMobile?: () => void;
}

export function LeftSidebar({
    currentSessionId,
    onSelectSession,
    onNewChat,
    isMobileOpen = false,
    onCloseMobile
}: LeftSidebarProps) {
    const [activeTab, setActiveTab] = useState<"chat" | "tools">("chat");

    return (
        <aside
            className={`fixed left-0 top-16 bottom-0 w-64 glass-sidebar flex flex-col z-30 transition-transform duration-300 ${isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
                }`}
        >
            {/* Tabs */}
            <div className="flex border-b border-border">
                <button
                    onClick={() => setActiveTab("chat")}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${activeTab === "chat"
                            ? "text-primary border-b-2 border-primary bg-primary/5"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                        }`}
                >
                    <MessageSquare className="w-4 h-4" />
                    Chats
                </button>
                <button
                    onClick={() => setActiveTab("tools")}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${activeTab === "tools"
                            ? "text-primary border-b-2 border-primary bg-primary/5"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                        }`}
                >
                    <LayoutGrid className="w-4 h-4" />
                    Limbs
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden relative">
                <div className={`absolute inset-0 transition-opacity duration-300 ${activeTab === "chat" ? "opacity-100 z-10" : "opacity-0 z-0"}`}>
                    <ChatSidebar
                        currentSessionId={currentSessionId}
                        onSelectSession={(id) => {
                            onSelectSession(id);
                            if (window.innerWidth < 768 && onCloseMobile) onCloseMobile();
                        }}
                        onNewChat={() => {
                            onNewChat();
                            if (window.innerWidth < 768 && onCloseMobile) onCloseMobile();
                        }}
                        isOpen={true} // Always open within the tab
                        onClose={() => { }} // Handle inside parent if needed
                    />
                </div>

                <div className={`absolute inset-0 transition-opacity duration-300 p-4 ${activeTab === "tools" ? "opacity-100 z-10" : "opacity-0 z-0"}`}>
                    <ToolsView />
                </div>
            </div>
        </aside>
    );
}
