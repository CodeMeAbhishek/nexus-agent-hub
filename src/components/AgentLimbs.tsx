import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  MessageSquare, 
  FileText, 
  Github, 
  Database, 
  CreditCard,
  Mail,
  Users,
  FolderOpen,
  HardDrive,
  Plus,
  Search
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface Limb {
  id: string;
  name: string;
  icon: React.ElementType;
  status: "active" | "disconnected";
  color: string;
  bgColor: string;
}

const limbs: Limb[] = [
  { id: "slack", name: "Slack", icon: MessageSquare, status: "active", color: "text-purple-600", bgColor: "bg-purple-500/10" },
  { id: "notion", name: "Notion", icon: FileText, status: "active", color: "text-gray-900", bgColor: "bg-gray-900/10" },
  { id: "github", name: "GitHub", icon: Github, status: "active", color: "text-gray-800", bgColor: "bg-gray-800/10" },
  { id: "mongodb", name: "MongoDB", icon: Database, status: "active", color: "text-green-600", bgColor: "bg-green-500/10" },
  { id: "stripe", name: "Stripe", icon: CreditCard, status: "disconnected", color: "text-blue-600", bgColor: "bg-blue-500/10" },
  { id: "gmail", name: "Gmail", icon: Mail, status: "active", color: "text-red-500", bgColor: "bg-red-500/10" },
  { id: "teams", name: "MS Teams", icon: Users, status: "active", color: "text-indigo-600", bgColor: "bg-indigo-500/10" },
  { id: "gdrive", name: "Google Drive", icon: FolderOpen, status: "active", color: "text-yellow-600", bgColor: "bg-yellow-500/10" },
  { id: "filesystem", name: "Local Files", icon: HardDrive, status: "active", color: "text-gray-600", bgColor: "bg-gray-500/10" },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: { duration: 0.4, ease: "easeOut" as const }
  },
};

export const AgentLimbs = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  const filteredLimbs = limbs.filter(limb => 
    limb.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside className="fixed left-0 top-16 bottom-0 w-56 glass-sidebar p-4 flex flex-col z-40">
      {/* Title */}
      <motion.h2 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-lg font-bold text-foreground mb-4"
      >
        Agent Limbs
      </motion.h2>

      {/* Limbs List */}
      <motion.div 
        className="flex-1 overflow-y-auto scrollbar-thin space-y-1"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <AnimatePresence>
          {filteredLimbs.map((limb) => (
            <motion.div
              key={limb.id}
              variants={itemVariants}
              whileHover={{ 
                scale: 1.02, 
                backgroundColor: "rgba(255, 255, 255, 0.3)",
              }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-all duration-200 group"
            >
              {/* Icon */}
              <div className={`w-8 h-8 rounded-lg ${limb.bgColor} flex items-center justify-center transition-transform group-hover:scale-110`}>
                <limb.icon className={`w-4 h-4 ${limb.color}`} />
              </div>

              {/* Name & Status */}
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium text-foreground truncate block">
                  {limb.name}
                </span>
              </div>

              {/* Status Indicator */}
              <div className="flex items-center gap-1.5">
                <motion.div
                  animate={limb.status === "active" ? {
                    scale: [1, 1.2, 1],
                    opacity: [1, 0.7, 1],
                  } : {}}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                  className={`w-2 h-2 rounded-full ${
                    limb.status === "active" 
                      ? "bg-green-500 shadow-glow-green" 
                      : "bg-red-500"
                  }`}
                />
                <span className={`text-xs font-medium ${
                  limb.status === "active" 
                    ? "text-green-600" 
                    : "text-red-500"
                }`}>
                  {limb.status === "active" ? "Active" : "Offline"}
                </span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </motion.div>

      {/* Query Input */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.4 }}
        className="mt-4 space-y-3"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search limbs..."
            className="pl-9 glass-input text-sm focus-ring"
          />
        </div>

        {/* Add Limb Button */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button 
              variant="outline" 
              className="w-full glass-light border-dashed border-muted-foreground/30 hover:border-accent hover:bg-accent/10 gap-2 text-muted-foreground hover:text-accent transition-all"
            >
              <Plus className="w-4 h-4" />
              Add Limb
            </Button>
          </DialogTrigger>
          <DialogContent className="glass-light sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-foreground">Add New Integration</DialogTitle>
              <DialogDescription className="text-muted-foreground">
                Connect a new platform to expand your agent's capabilities.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <Input 
                placeholder="Integration name..." 
                className="glass-input focus-ring"
              />
              <Input 
                placeholder="API endpoint..." 
                className="glass-input focus-ring"
              />
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                Connect Integration
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </motion.div>
    </aside>
  );
};
