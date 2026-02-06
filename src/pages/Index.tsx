import { TopNav } from "@/components/TopNav";
import { AgentLimbs } from "@/components/AgentLimbs";
import { CenterWorkspace } from "@/components/CenterWorkspace";
import { ReasoningTrace } from "@/components/ReasoningTrace";
import heroBg from "@/assets/hero-bg.jpg";

const Index = () => {
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
      <TopNav />

      {/* Three-Panel Layout */}
      <div className="flex w-full">
        {/* Left Sidebar - Agent Limbs */}
        <AgentLimbs />

        {/* Center Workspace */}
        <CenterWorkspace />

        {/* Right Panel - Reasoning Trace */}
        <ReasoningTrace />
      </div>
    </div>
  );
};

export default Index;
