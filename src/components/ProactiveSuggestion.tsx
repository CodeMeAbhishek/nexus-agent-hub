import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ProactiveSuggestionProps {
  suggestion: string;
  isVisible: boolean;
  onAccept: () => void;
  onDismiss: () => void;
}

export const ProactiveSuggestion = ({ 
  suggestion, 
  isVisible, 
  onAccept, 
  onDismiss 
}: ProactiveSuggestionProps) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
          className="glass-light p-4 rounded-xl shadow-glass border border-accent/20"
        >
          <div className="flex items-start gap-3">
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center shrink-0"
            >
              <Sparkles className="w-4 h-4 text-accent" />
            </motion.div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground mb-1">
                Ready to execute
              </p>
              <p className="text-sm text-muted-foreground mb-3">
                {suggestion}
              </p>

              <div className="flex items-center gap-2">
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button
                    size="sm"
                    onClick={onAccept}
                    className="bg-primary text-primary-foreground hover:bg-primary/90 h-8 gap-1"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Yes, execute
                  </Button>
                </motion.div>
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={onDismiss}
                    className="h-8 gap-1 text-muted-foreground hover:text-foreground"
                  >
                    <X className="w-3.5 h-3.5" />
                    No
                  </Button>
                </motion.div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
