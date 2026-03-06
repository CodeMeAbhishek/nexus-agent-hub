import { useState } from "react";
import { TopNav } from "@/components/TopNav";
import { LeftSidebar } from "@/components/LeftSidebar";
import { CenterWorkspace } from "@/components/CenterWorkspace";
import { ReasoningTrace } from "@/components/ReasoningTrace";
import heroBg from "@/assets/hero-bg.jpg";

const Index = () => {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div
      className="min-h-screen bg-background"
      style={{
        backgroundImage: `url(${heroBg})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
      }}
    >
      {/* Top Navigation */}
      <TopNav onMenuClick={() => setIsMobileOpen(!isMobileOpen)} />

      {/* Three-Panel Layout */}
      <div className="flex w-full h-[calc(100vh-64px)] overflow-hidden pt-16">
        {/* Left Sidebar - Chat History & Tools */}
        <LeftSidebar
          currentSessionId={currentSessionId}
          onSelectSession={setCurrentSessionId}
          onNewChat={() => setCurrentSessionId(null)}
          isMobileOpen={isMobileOpen}
          onCloseMobile={() => setIsMobileOpen(false)}
        />

        {/* Center Workspace */}
        <CenterWorkspace
          currentSessionId={currentSessionId}
          onSessionCreated={setCurrentSessionId}
        />

        {/* Right Panel - Reasoning Trace */}
        <ReasoningTrace />
      </div>
    </div>
  );
};

export default Index;
