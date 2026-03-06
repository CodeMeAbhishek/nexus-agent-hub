import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { QueryInput } from "./QueryInput";
import { ChatMessage, ChatMessageData } from "./ChatMessage";
import { ActionCard, ActionCardData } from "./ActionCard";
import { TypingIndicator } from "./TypingIndicator";
import { ProcessingIndicator } from "./ProcessingIndicator";
import { streamChat, getSessionMessages, createSession } from "@/lib/api";
import { useReasoningTrace } from "@/context/ReasoningTraceContext";
import { useAgentStream } from "@/hooks/useAgentStream";

interface CenterWorkspaceProps {
  currentSessionId: string | null;
  onSessionCreated: (id: string) => void;
}

export const CenterWorkspace = ({ currentSessionId, onSessionCreated }: CenterWorkspaceProps) => {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [cards, setCards] = useState<ActionCardData[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [processingStatus, setProcessingStatus] = useState("Planning...");

  const scrollRef = useRef<HTMLDivElement>(null);
  const { addLog, clearLogs } = useReasoningTrace();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, cards]);

  // Load history when session changes
  useEffect(() => {
    async function loadHistory() {
      if (currentSessionId) {
        setIsProcessing(true);
        try {
          const history = await getSessionMessages(currentSessionId);
          const formatted: ChatMessageData[] = history.map(msg => ({
            id: msg.id,
            role: msg.role === 'user' ? 'user' : 'agent',
            content: msg.content,
            timestamp: new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }));
          setMessages(formatted);
          clearLogs(); // Clear logs from previous session
        } catch (e) {
          console.error("Failed to load history", e);
        } finally {
          setIsProcessing(false);
        }
      } else {
        setMessages([]);
        clearLogs();
      }
    }
    loadHistory();
  }, [currentSessionId]);

  /* New Hook Usage */
  const { streamAgent } = useAgentStream();

  const handleSubmit = async (query: string) => {
    let sessionId = currentSessionId;

    // Create session if new
    if (!sessionId) {
      try {
        const newSession = await createSession(query.substring(0, 30));
        sessionId = newSession.id;
        onSessionCreated(sessionId);
      } catch (e) {
        console.error("Failed to create session", e);
        return; // Stop if we can't create session
      }
    }

    const userMessage: ChatMessageData = {
      id: `user-${Date.now()}`,
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true }),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Clear previous logs ONLY if it was a new query in same session?
    // Actually we keep logs for the *current action*.
    clearLogs();
    setIsProcessing(true);
    setIsTyping(true);
    setProcessingStatus("Initializing agent...");

    // Pass sessionId to streamAgent
    await streamAgent(query, {
      sessionId, // Pass the session ID
      onLog: (log) => {
        let traceType: "info" | "action" | "result" | "error" = "info";
        if (log.type === "action") traceType = "action";
        if (log.type === "result" || log.type === "response") traceType = "result";
        if (log.type === "error") traceType = "error";

        if (log.type !== "done") {
          addLog(traceType, log.message);
        }

        if (log.type === "info" || log.type === "action") {
          setProcessingStatus(log.message.slice(0, 40) + (log.message.length > 40 ? "..." : ""));
        }
      },
      onDone: (finalText) => {
        setIsTyping(false);
        const agentMessage: ChatMessageData = {
          id: `agent-${Date.now()}`,
          role: "agent",
          content: finalText || "No response.",
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true }),
        };
        setMessages((prev) => [...prev, agentMessage]);
        setIsProcessing(false);
        addLog("info", "✅ Request complete");
      },
      onError: (errMsg) => {
        setIsTyping(false);
        const agentMessage: ChatMessageData = {
          id: `agent-${Date.now()}`,
          role: "agent",
          content: `Error: ${errMsg}`,
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true }),
        };
        setMessages((prev) => [...prev, agentMessage]);
        setIsProcessing(false);
      }
    });
  };

  const handleCardAction = (cardId: string, action: "approved" | "rejected") => {
    setCards((prev) =>
      prev.map((card) =>
        card.id === cardId ? { ...card, status: action } : card
      )
    );
  };

  return (
    <main className="flex-1 flex flex-col h-full bg-gradient-to-br from-background via-background to-muted/30 relative overflow-hidden">
      {/* Processing Indicator */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
        <ProcessingIndicator isVisible={isProcessing} status={processingStatus} />
      </div>

      {/* Scrollable Content */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto scrollbar-thin p-6 pb-4"
      >
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="max-w-3xl mx-auto space-y-6"
        >
          {/* Chat Messages */}
          <div className="space-y-4">
            {messages.map((message, index) => (
              <ChatMessage key={message.id} message={message} index={index} />
            ))}
            <AnimatePresence>
              {isTyping && <TypingIndicator />}
            </AnimatePresence>
          </div>

          {/* Action Cards */}
          <div className="space-y-3">
            <AnimatePresence>
              {cards.map((card, index) => (
                <ActionCard
                  key={card.id}
                  data={card}
                  index={index}
                  onApprove={() => handleCardAction(card.id, "approved")}
                  onReject={() => handleCardAction(card.id, "rejected")}
                />
              ))}
            </AnimatePresence>
          </div>
        </motion.div>
      </div>

      {/* Query Input */}
      <div className="p-4 border-t border-white/10 glass-light">
        <div className="max-w-3xl mx-auto">
          <QueryInput onSubmit={handleSubmit} isProcessing={isProcessing} />
        </div>
      </div>
    </main>
  );
};
