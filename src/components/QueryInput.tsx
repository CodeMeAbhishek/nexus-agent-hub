import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Paperclip, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isProcessing: boolean;
}

export const QueryInput = ({ onSubmit, isProcessing }: QueryInputProps) => {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (query.trim() && !isProcessing) {
      onSubmit(query.trim());
      setQuery("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.5 }}
      className="w-full"
    >
      <div 
        className={`glass-input rounded-2xl p-3 transition-all duration-300 ${
          isFocused ? "ring-2 ring-accent/50 shadow-glow-blue" : "shadow-glass"
        }`}
      >
        <div className="flex items-end gap-3">
          {/* Attach Button */}
          <motion.div
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 shrink-0 text-muted-foreground hover:text-foreground hover:bg-white/30"
              aria-label="Attach files"
            >
              <Paperclip className="w-4 h-4" />
            </Button>
          </motion.div>

          {/* Textarea */}
          <Textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Nexus anything... Query data, execute actions, analyze documents"
            className="flex-1 min-h-[40px] max-h-[120px] resize-none border-0 bg-transparent focus-visible:ring-0 placeholder:text-muted-foreground/60 text-foreground text-sm leading-relaxed"
            rows={1}
          />

          {/* Send Button */}
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              onClick={handleSubmit}
              disabled={!query.trim() || isProcessing}
              className="h-9 w-9 shrink-0 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              aria-label="Send query"
            >
              <AnimatePresence mode="wait">
                {isProcessing ? (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0, rotate: 0 }}
                    animate={{ opacity: 1, rotate: 360 }}
                    exit={{ opacity: 0 }}
                    transition={{ rotate: { duration: 1, repeat: Infinity, ease: "linear" } }}
                  >
                    <Loader2 className="w-4 h-4" />
                  </motion.div>
                ) : (
                  <motion.div
                    key="send"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                  >
                    <Send className="w-4 h-4" />
                  </motion.div>
                )}
              </AnimatePresence>
            </Button>
          </motion.div>
        </div>

        {/* Keyboard Hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: isFocused ? 1 : 0 }}
          className="flex items-center justify-end gap-2 mt-2 pt-2 border-t border-white/10"
        >
          <span className="text-xs text-muted-foreground/60">
            <kbd className="px-1.5 py-0.5 rounded bg-white/20 font-mono text-[10px]">⌘</kbd>
            {" + "}
            <kbd className="px-1.5 py-0.5 rounded bg-white/20 font-mono text-[10px]">Enter</kbd>
            {" to send"}
          </span>
          <Sparkles className="w-3 h-3 text-accent/60" />
        </motion.div>
      </div>
    </motion.div>
  );
};
