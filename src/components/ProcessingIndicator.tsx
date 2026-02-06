import { motion, AnimatePresence } from "framer-motion";
import { Brain } from "lucide-react";

interface ProcessingIndicatorProps {
  isVisible: boolean;
  status?: string;
}

export const ProcessingIndicator = ({ isVisible, status = "Planning..." }: ProcessingIndicatorProps) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          className="flex items-center gap-2 px-3 py-1.5 rounded-full glass-light"
        >
          <motion.div
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.5, 1, 0.5],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            className="relative"
          >
            <div className="w-5 h-5 rounded-full bg-accent/20 backdrop-blur-sm flex items-center justify-center">
              <Brain className="w-3 h-3 text-accent" />
            </div>
            <motion.div
              animate={{
                opacity: [0.3, 0.6, 0.3],
                scale: [1, 1.5, 1],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="absolute inset-0 rounded-full bg-accent/20"
            />
          </motion.div>
          <span className="text-xs font-medium text-muted-foreground">{status}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
