import { motion } from "framer-motion";
import { User, Bot, Clock } from "lucide-react";

export interface ChatMessageData {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: string;
}

interface ChatMessageProps {
  message: ChatMessageData;
  index: number;
}

const messageVariants = {
  hidden: { opacity: 0, y: 10, scale: 0.98 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: i * 0.05,
      duration: 0.3,
      ease: "easeOut" as const,
    },
  }),
};

export const ChatMessage = ({ message, index }: ChatMessageProps) => {
  const isUser = message.role === "user";

  return (
    <motion.div
      custom={index}
      variants={messageVariants}
      initial="hidden"
      animate="visible"
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      <motion.div
        whileHover={{ scale: 1.1 }}
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser 
            ? "bg-accent/20 backdrop-blur-sm" 
            : "bg-gradient-to-br from-primary/20 to-accent/20 backdrop-blur-sm"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-accent" />
        ) : (
          <Bot className="w-4 h-4 text-primary" />
        )}
      </motion.div>

      {/* Message Bubble */}
      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[70%]`}>
        <motion.div
          whileHover={{ scale: 1.01 }}
          className={`px-4 py-3 rounded-2xl ${
            isUser 
              ? "bg-blue-100/30 backdrop-blur-sm rounded-br-md" 
              : "bg-zinc-100/30 backdrop-blur-sm rounded-bl-md"
          }`}
        >
          <p className="text-sm text-card-foreground leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </motion.div>
        
        {/* Timestamp */}
        <span className="text-[10px] text-muted-foreground/60 mt-1 flex items-center gap-1">
          <Clock className="w-2.5 h-2.5" />
          {message.timestamp}
        </span>
      </div>
    </motion.div>
  );
};
