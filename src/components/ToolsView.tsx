import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
    MessageSquare,
    FileText,
    Github,
    Database,
    Mail,
    FolderOpen,
    HardDrive,
    Plus,
    Search,
    Calendar
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
import { listTools } from "@/lib/api";

interface Limb {
    id: string;
    name: string;
    icon: React.ElementType;
    status: "active" | "disconnected";
    color: string;
    bgColor: string;
}

const LIMB_UI: Record<string, { icon: React.ElementType; color: string; bgColor: string }> = {
    slack: { icon: MessageSquare, color: "text-white", bgColor: "bg-[#4A154B]" },
    notion: { icon: FileText, color: "text-foreground", bgColor: "bg-background" },
    github: { icon: Github, color: "text-white", bgColor: "bg-gray-900" },
    mongodb: { icon: Database, color: "text-white", bgColor: "bg-green-700" },
    gmail: { icon: Mail, color: "text-white", bgColor: "bg-red-600" },
    calendar: { icon: Calendar, color: "text-white", bgColor: "bg-teal-600" },
    googledrive: { icon: FolderOpen, color: "text-white", bgColor: "bg-blue-500" },
    filesystem: { icon: HardDrive, color: "text-foreground", bgColor: "bg-muted" },
};

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

function toLimb(api: { id: string; name: string; status: "active" | "disconnected" }): Limb {
    const ui = LIMB_UI[api.id] ?? { icon: FileText, color: "text-muted-foreground", bgColor: "bg-muted" };
    return {
        id: api.id,
        name: api.name,
        icon: ui.icon,
        status: api.status,
        color: ui.color,
        bgColor: ui.bgColor,
    };
}

export const ToolsView = () => {
    const [searchQuery, setSearchQuery] = useState("");
    const [dialogOpen, setDialogOpen] = useState(false);

    const { data, isLoading, isError } = useQuery({
        queryKey: ["tools"],
        queryFn: listTools,
        refetchInterval: 10_000,
        retry: 2,
        retryDelay: 2000,
    });

    const limbs: Limb[] = useMemo(
        () => (data?.limbs ?? []).map(toLimb),
        [data?.limbs]
    );

    const filteredLimbs = limbs.filter((limb) =>
        limb.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="flex flex-col h-full">
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
                {isLoading ? (
                    <p className="text-sm text-muted-foreground py-4 px-2 text-center">
                        Checking limbs…
                    </p>
                ) : isError ? (
                    <p className="text-sm text-destructive/90 py-4 px-2 text-center">
                        Backend unreachable. Start the API on port 8000.
                    </p>
                ) : filteredLimbs.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-4 px-2 text-center">
                        No limbs connected. Start the backend and add integrations.
                    </p>
                ) : (
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
                                        className={`w-2 h-2 rounded-full ${limb.status === "active"
                                            ? "bg-green-500 shadow-glow-green"
                                            : "bg-red-500"
                                            }`}
                                    />
                                    <span className={`text-xs font-medium ${limb.status === "active"
                                        ? "text-green-600"
                                        : "text-red-500"
                                        }`}>
                                        {limb.status === "active" ? "Active" : "Offline"}
                                    </span>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                )}
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
        </div>
    );
};
