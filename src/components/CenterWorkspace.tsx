import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { QueryInput } from "./QueryInput";
import { ChatMessage, ChatMessageData } from "./ChatMessage";
import { ActionCard, ActionCardData } from "./ActionCard";
import { TypingIndicator } from "./TypingIndicator";
import { ProactiveSuggestion } from "./ProactiveSuggestion";
import { ProcessingIndicator } from "./ProcessingIndicator";

const initialMessages: ChatMessageData[] = [
  {
    id: "1",
    role: "agent",
    content: "Hello! I'm Nexus Agent, your enterprise AI assistant. I can help you query data across connected platforms, execute automated actions, and analyze documents. What would you like to do?",
    timestamp: "10:30 AM",
  },
];

const initialCards: ActionCardData[] = [
  {
    id: "1",
    type: "stripe",
    title: "Failed Payment Alert",
    description: "Payment attempt failed for customer invoice #INV-2024-001",
    details: {
      "Amount": "$299.00",
      "Date": "Feb 5, 2026",
      "Reason": "Card declined",
    },
    timestamp: "12m ago",
    status: "pending",
  },
  {
    id: "2",
    type: "notion",
    title: "Q1 Sprint Planning",
    description: "New task created in Engineering workspace requiring review",
    details: {
      "Assignee": "Engineering Team",
      "Priority": "High",
      "Due": "Feb 10, 2026",
    },
    timestamp: "24m ago",
    status: "pending",
  },
  {
    id: "3",
    type: "github",
    title: "PR Review Required",
    description: "Pull request #428 - feat: implement OAuth2 flow awaiting approval",
    details: {
      "Branch": "feature/oauth2",
      "Author": "john.dev",
      "Changes": "+342 / -28",
    },
    timestamp: "1h ago",
    status: "pending",
  },
];

export const CenterWorkspace = () => {
  const [messages, setMessages] = useState<ChatMessageData[]>(initialMessages);
  const [cards, setCards] = useState<ActionCardData[]>(initialCards);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [showSuggestion, setShowSuggestion] = useState(false);
  const [processingStatus, setProcessingStatus] = useState("Planning...");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, cards]);

  // Show proactive suggestion after initial load
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSuggestion(true);
    }, 4000);
    return () => clearTimeout(timer);
  }, []);

  const handleSubmit = async (query: string) => {
    // Add user message
    const userMessage: ChatMessageData = {
      id: `user-${Date.now()}`,
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString("en-US", { 
        hour: "numeric", 
        minute: "2-digit",
        hour12: true 
      }),
    };
    setMessages(prev => [...prev, userMessage]);
    
    // Start processing
    setIsProcessing(true);
    setIsTyping(true);
    setProcessingStatus("Analyzing query...");

    // Simulate processing steps
    await new Promise(r => setTimeout(r, 1000));
    setProcessingStatus("Querying connected platforms...");
    await new Promise(r => setTimeout(r, 1500));
    setProcessingStatus("Generating response...");
    await new Promise(r => setTimeout(r, 1000));

    setIsTyping(false);

    // Add agent response
    const agentMessage: ChatMessageData = {
      id: `agent-${Date.now()}`,
      role: "agent",
      content: `I've analyzed your query about "${query.slice(0, 50)}${query.length > 50 ? '...' : ''}". Based on the connected platforms, I found relevant data and have prepared action cards for your review. Would you like me to execute any specific actions?`,
      timestamp: new Date().toLocaleTimeString("en-US", { 
        hour: "numeric", 
        minute: "2-digit",
        hour12: true 
      }),
    };
    setMessages(prev => [...prev, agentMessage]);
    setIsProcessing(false);
  };

  const handleCardAction = (cardId: string, action: "approved" | "rejected") => {
    setCards(prev => prev.map(card => 
      card.id === cardId ? { ...card, status: action } : card
    ));
  };

  const handleSuggestionAccept = () => {
    setShowSuggestion(false);
    handleSubmit("Query Stripe for all failed payments in the last 7 days");
  };

  return (
    <main className="fixed left-56 right-80 top-16 bottom-0 flex flex-col bg-gradient-to-br from-background via-background to-muted/30">
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

          {/* Proactive Suggestion */}
          <ProactiveSuggestion
            suggestion="Query Stripe for failed payments in the last 7 days?"
            isVisible={showSuggestion}
            onAccept={handleSuggestionAccept}
            onDismiss={() => setShowSuggestion(false)}
          />

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
