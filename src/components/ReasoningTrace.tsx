import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Trash2, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";

interface LogEntry {
  id: string;
  message: string;
  timestamp: Date;
  type: "info" | "action" | "result" | "error";
}

const initialLogs: LogEntry[] = [
  { id: "1", message: "> Initializing Nexus Agent...", timestamp: new Date(Date.now() - 60000), type: "info" },
  { id: "2", message: "> Loading connected limbs...", timestamp: new Date(Date.now() - 55000), type: "info" },
  { id: "3", message: "> Slack MCP connected ✓", timestamp: new Date(Date.now() - 50000), type: "result" },
  { id: "4", message: "> Notion MCP connected ✓", timestamp: new Date(Date.now() - 48000), type: "result" },
  { id: "5", message: "> GitHub MCP connected ✓", timestamp: new Date(Date.now() - 46000), type: "result" },
  { id: "6", message: "> MongoDB MCP connected ✓", timestamp: new Date(Date.now() - 44000), type: "result" },
  { id: "7", message: "> Agent ready. Awaiting queries...", timestamp: new Date(Date.now() - 40000), type: "info" },
];

const logVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: { duration: 0.3, ease: "easeOut" as const }
  },
  exit: { 
    opacity: 0, 
    x: 10,
    transition: { duration: 0.2 }
  },
};

export const ReasoningTrace = () => {
  const [logs, setLogs] = useState<LogEntry[]>(initialLogs);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs appear
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  // Simulate incoming logs
  useEffect(() => {
    const simulatedLogs = [
      { message: "> User query received...", type: "info" as const },
      { message: "> Decomposing goal into sub-tasks...", type: "action" as const },
      { message: "> Calling Stripe MCP for payment data...", type: "action" as const },
      { message: "> Verifying user permissions...", type: "info" as const },
      { message: "> Retrieved 3 failed transactions", type: "result" as const },
      { message: "> Generating action cards...", type: "action" as const },
      { message: "> Ready for user approval", type: "result" as const },
    ];

    let index = 0;
    const interval = setInterval(() => {
      if (index < simulatedLogs.length) {
        const newLog = simulatedLogs[index];
        setLogs(prev => [...prev, {
          id: `sim-${Date.now()}-${index}`,
          message: newLog.message,
          timestamp: new Date(),
          type: newLog.type,
        }]);
        index++;
      } else {
        clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const clearLogs = () => {
    setLogs([{
      id: "cleared",
      message: "> Logs cleared. Agent idle.",
      timestamp: new Date(),
      type: "info",
    }]);
  };

  const getLogColor = (type: LogEntry["type"]) => {
    switch (type) {
      case "action": return "text-blue-400";
      case "result": return "text-emerald-400";
      case "error": return "text-red-400";
      default: return "text-emerald-500";
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", { 
      hour: "2-digit", 
      minute: "2-digit",
      second: "2-digit",
      hour12: false 
    });
  };

  return (
    <aside className="fixed right-0 top-16 bottom-0 w-80 glass-panel flex flex-col z-40">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <motion.div 
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-2"
        >
          <Terminal className="w-5 h-5 text-success" />
          <h2 className="text-lg font-bold text-foreground">Reasoning Trace</h2>
        </motion.div>
        <motion.div
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
        >
          <Button
            variant="ghost"
            size="icon"
            onClick={clearLogs}
            className="h-8 w-8 hover:bg-white/20"
            aria-label="Clear logs"
          >
            <Trash2 className="w-4 h-4 text-muted-foreground" />
          </Button>
        </motion.div>
      </div>

      {/* Logs Container */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-2"
      >
        <AnimatePresence mode="popLayout">
          {logs.length === 0 ? (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-muted-foreground text-sm text-center py-8"
            >
              Agent idle. Enter a query to activate.
            </motion.p>
          ) : (
            logs.map((log) => (
              <motion.div
                key={log.id}
                variants={logVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                layout
                className="flex items-start gap-2"
              >
                <span className="text-xs text-muted-foreground/60 font-mono shrink-0 mt-0.5">
                  {formatTime(log.timestamp)}
                </span>
                <p className={`terminal text-sm ${getLogColor(log.type)} leading-relaxed`}>
                  {log.message}
                </p>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {/* Processing Indicator */}
      <div className="p-4 border-t border-white/10">
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="flex items-center gap-2"
        >
          <div className="w-3 h-3 rounded-full bg-accent/20 backdrop-blur-sm flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-accent shadow-glow-blue" />
          </div>
          <span className="text-xs text-muted-foreground">Agent processing...</span>
        </motion.div>
      </div>
    </aside>
  );
};
