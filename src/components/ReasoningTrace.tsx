import { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Trash2, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useReasoningTrace, LogEntry } from "@/context/ReasoningTraceContext";

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
  const { logs, clearLogs } = useReasoningTrace();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const getLogColor = (type: LogEntry["type"]) => {
    switch (type) {
      case "action": return "text-[hsl(var(--log-action))]";
      case "result": return "text-[hsl(var(--log-result))]";
      case "error": return "text-[hsl(var(--log-error))]";
      default: return "text-[hsl(var(--log-info))]";
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
    <aside className="fixed right-0 top-16 bottom-0 w-80 bg-card/80 backdrop-blur-xl border-l border-border/30 flex flex-col z-40">
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
                <span className="text-xs text-[hsl(var(--log-timestamp))] font-mono shrink-0 mt-0.5">
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
    </aside>
  );
};
