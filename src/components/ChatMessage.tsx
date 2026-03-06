import { motion } from "framer-motion";
import { User, Bot, Clock } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${isUser
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
      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[85%]`}>
        <motion.div
          whileHover={{ scale: 1.01 }}
          className={`px-5 py-4 rounded-2xl shadow-sm ${isUser
            ? "bg-blue-100/40 backdrop-blur-md rounded-br-sm"
            : "bg-white/60 backdrop-blur-md rounded-bl-sm border border-white/20"
            }`}
        >
          <div className={`prose prose-sm max-w-none 
            ${isUser ? "prose-p:text-slate-700" : "prose-p:text-slate-800 prose-headings:text-slate-900"}
            prose-headings:font-semibold prose-headings:mb-2 prose-headings:mt-4
            prose-p:leading-relaxed prose-p:my-2
            prose-ul:my-2 prose-li:my-0.5
            prose-table:w-full prose-table:border-collapse prose-table:text-sm prose-table:my-4
            prose-th:bg-slate-100/50 prose-th:p-2 prose-th:text-left prose-th:border-b prose-th:border-slate-200
            prose-td:p-2 prose-td:border-b prose-td:border-slate-100/50
          `}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        </motion.div>

        {/* Timestamp */}
        <span className="text-[10px] text-muted-foreground/60 mt-1 flex items-center gap-1 px-1">
          <Clock className="w-2.5 h-2.5" />
          {message.timestamp}
        </span>
      </div>
    </motion.div>
  );
};
