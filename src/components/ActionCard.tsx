import { motion } from "framer-motion";
import { CreditCard, FileText, Github, AlertTriangle, CheckCircle, XCircle, Edit, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface ActionCardData {
  id: string;
  type: "stripe" | "notion" | "github";
  title: string;
  description: string;
  details?: Record<string, string>;
  timestamp: string;
  status?: "pending" | "approved" | "rejected";
}

interface ActionCardProps {
  data: ActionCardData;
  onApprove?: () => void;
  onReject?: () => void;
  index: number;
}

const cardVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      delay: i * 0.1,
      duration: 0.4,
      type: "spring" as const,
      stiffness: 100,
      damping: 15,
    },
  }),
};

const platformConfig = {
  stripe: {
    icon: CreditCard,
    color: "text-blue-600",
    bgColor: "bg-blue-500/10",
    badgeColor: "bg-blue-100 text-blue-700",
    borderColor: "border-blue-200/30",
  },
  notion: {
    icon: FileText,
    color: "text-gray-900",
    bgColor: "bg-gray-900/10",
    badgeColor: "bg-gray-100 text-gray-700",
    borderColor: "border-gray-200/30",
  },
  github: {
    icon: Github,
    color: "text-gray-800",
    bgColor: "bg-gray-800/10",
    badgeColor: "bg-gray-100 text-gray-800",
    borderColor: "border-gray-200/30",
  },
};

export const ActionCard = ({ data, onApprove, onReject, index }: ActionCardProps) => {
  const config = platformConfig[data.type];
  const Icon = config.icon;

  return (
    <motion.div
      custom={index}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover={{ 
        scale: 1.01,
        boxShadow: "0 12px 40px 0 rgba(0, 0, 0, 0.08)",
      }}
      className={`glass-card p-4 rounded-xl ${config.borderColor} transition-all duration-200`}
    >
      <div className="flex items-start gap-3">
        {/* Platform Icon */}
        <motion.div 
          className={`w-10 h-10 rounded-full ${config.bgColor} flex items-center justify-center shrink-0`}
          whileHover={{ scale: 1.1, rotate: 5 }}
        >
          <Icon className={`w-5 h-5 ${config.color}`} />
        </motion.div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-foreground text-sm truncate">
              {data.title}
            </h3>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${config.badgeColor}`}>
              {data.type.charAt(0).toUpperCase() + data.type.slice(1)}
            </span>
          </div>
          
          <p className="text-muted-foreground text-sm line-clamp-2 mb-3">
            {data.description}
          </p>

          {/* Details */}
          {data.details && (
            <div className="space-y-1 mb-3">
              {Object.entries(data.details).map(([key, value]) => (
                <div key={key} className="flex items-center gap-2 text-xs">
                  <span className="text-muted-foreground capitalize">{key}:</span>
                  <span className="font-medium text-foreground">{value}</span>
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {data.status === "pending" && (
                <>
                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                    <Button
                      size="sm"
                      onClick={onApprove}
                      className="bg-success text-success-foreground hover:bg-success/90 h-7 text-xs gap-1"
                    >
                      <CheckCircle className="w-3 h-3" />
                      Approve
                    </Button>
                  </motion.div>
                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onReject}
                      className="border-destructive/30 text-destructive hover:bg-destructive/10 h-7 text-xs gap-1"
                    >
                      <XCircle className="w-3 h-3" />
                      Reject
                    </Button>
                  </motion.div>
                </>
              )}
              {data.status === "approved" && (
                <span className="text-xs text-success flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" />
                  Approved
                </span>
              )}
              {data.status === "rejected" && (
                <span className="text-xs text-destructive flex items-center gap-1">
                  <XCircle className="w-3 h-3" />
                  Rejected
                </span>
              )}
              {data.type === "notion" && (
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground"
                  >
                    <Edit className="w-3 h-3" />
                    Edit
                  </Button>
                </motion.div>
              )}
            </div>
            
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {data.timestamp}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
