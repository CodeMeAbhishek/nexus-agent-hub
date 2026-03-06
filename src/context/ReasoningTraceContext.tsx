/**
 * Context for sharing reasoning trace logs between CenterWorkspace and ReasoningTrace.
 * Allows StreamChat to emit events that appear in the ReasoningTrace panel.
 */
import { createContext, useContext, useState, useCallback, ReactNode } from "react";

export interface LogEntry {
    id: string;
    message: string;
    timestamp: Date;
    type: "info" | "action" | "result" | "error";
}

interface ReasoningTraceContextType {
    logs: LogEntry[];
    addLog: (type: LogEntry["type"], message: string) => void;
    clearLogs: () => void;
}

const ReasoningTraceContext = createContext<ReasoningTraceContextType | null>(null);

export function ReasoningTraceProvider({ children }: { children: ReactNode }) {
    const [logs, setLogs] = useState<LogEntry[]>([]);

    const addLog = useCallback((type: LogEntry["type"], message: string) => {
        const entry: LogEntry = {
            id: `log-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
            message,
            timestamp: new Date(),
            type,
        };
        setLogs((prev) => [...prev, entry]);
    }, []);

    const clearLogs = useCallback(() => {
        setLogs([]);
    }, []);

    return (
        <ReasoningTraceContext.Provider value={{ logs, addLog, clearLogs }}>
            {children}
        </ReasoningTraceContext.Provider>
    );
}

export function useReasoningTrace() {
    const context = useContext(ReasoningTraceContext);
    if (!context) {
        throw new Error("useReasoningTrace must be used within a ReasoningTraceProvider");
    }
    return context;
}
