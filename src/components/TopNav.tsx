import { motion } from "framer-motion";
import { ArrowRight, Settings, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export const TopNav = () => {
  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="fixed top-0 left-0 right-0 z-50 h-16 glass-nav px-6 flex items-center justify-between"
    >
      {/* Logo / Brand */}
      <motion.div 
        className="flex items-center gap-3"
        whileHover={{ scale: 1.02 }}
        transition={{ duration: 0.2 }}
      >
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <span className="text-primary-foreground font-bold text-sm">N</span>
        </div>
        <h1 className="text-xl font-bold text-foreground tracking-tight">
          Nexus Agent
        </h1>
      </motion.div>

      {/* Right Actions */}
      <div className="flex items-center gap-4">
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
        >
          <Button 
            className="bg-primary text-primary-foreground hover:bg-primary/90 gap-2 font-medium shadow-lg"
          >
            Get Started
            <ArrowRight className="w-4 h-4" />
          </Button>
        </motion.div>

        {/* User Avatar */}
        <motion.div
          whileHover={{ scale: 1.05 }}
          transition={{ duration: 0.2 }}
        >
          <Avatar className="w-9 h-9 border-2 border-white/30 cursor-pointer">
            <AvatarImage src="" alt="User" />
            <AvatarFallback className="bg-gradient-to-br from-accent to-primary text-white font-medium text-sm">
              JD
            </AvatarFallback>
          </Avatar>
        </motion.div>

        {/* Settings Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <motion.button
              whileHover={{ scale: 1.1, rotate: 45 }}
              whileTap={{ scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="p-2 rounded-lg hover:bg-white/20 transition-colors focus-ring"
              aria-label="Settings"
            >
              <Settings className="w-5 h-5 text-muted-foreground" />
            </motion.button>
          </DropdownMenuTrigger>
          <DropdownMenuContent 
            align="end" 
            className="glass-light w-48 rounded-lg shadow-glass"
          >
            <DropdownMenuItem className="cursor-pointer hover:bg-white/30">
              <User className="w-4 h-4 mr-2" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-border/30" />
            <DropdownMenuItem className="cursor-pointer hover:bg-white/30 text-destructive">
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </motion.header>
  );
};
