import { motion } from "framer-motion";
import { ArrowRight, Settings, User, Plug, LogIn, LogOut, Menu } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useAuth } from "@/context/AuthContext";

interface TopNavProps {
  onMenuClick?: () => void;
}

export const TopNav = ({ onMenuClick }: TopNavProps) => {
  const { user, isAuthenticated, logout, authStatus } = useAuth();

  // Get initials for avatar
  const initials = user?.email
    ? user.email.charAt(0).toUpperCase()
    : "U";

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="fixed top-0 left-0 right-0 z-50 h-16 glass-nav px-6 flex items-center justify-between"
    >
      <div className="flex items-center gap-4">
        {/* Mobile Menu Button */}
        <button
          onClick={onMenuClick}
          className="md:hidden p-2 text-muted-foreground hover:text-foreground hover:bg-white/10 rounded-md transition-colors"
          aria-label="Toggle Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Logo / Brand */}
        <Link to="/">
          <motion.div
            className="flex items-center gap-3"
            whileHover={{ scale: 1.02 }}
            transition={{ duration: 0.2 }}
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">N</span>
            </div>
            <h1 className="text-xl font-bold text-foreground tracking-tight hidden sm:block">
              Nexus Agent
            </h1>
          </motion.div>
        </Link>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-4">
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
        >
          <Button
            asChild
            className="bg-primary text-primary-foreground hover:bg-primary/90 gap-2 font-medium shadow-lg"
          >
            <Link to="/settings">
              Get Started
              <ArrowRight className="w-4 h-4" />
            </Link>
          </Button>
        </motion.div>

        {/* User Avatar / Login */}
        {isAuthenticated ? (
          <motion.div
            whileHover={{ scale: 1.05 }}
            transition={{ duration: 0.2 }}
          >
            <Avatar className="w-9 h-9 border-2 border-white/30 cursor-pointer">
              <AvatarImage src="" alt={user?.email || "User"} />
              <AvatarFallback className="bg-gradient-to-br from-accent to-primary text-white font-medium text-sm">
                {initials}
              </AvatarFallback>
            </Avatar>
          </motion.div>
        ) : authStatus === "configured" ? (
          <Button variant="ghost" size="sm" asChild>
            <Link to="/login" className="flex items-center gap-2">
              <LogIn className="w-4 h-4" />
              Sign In
            </Link>
          </Button>
        ) : null}

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
            <DropdownMenuItem asChild className="cursor-pointer hover:bg-white/30">
              <Link to="/settings" className="flex items-center w-full">
                <Plug className="w-4 h-4 mr-2" />
                Connections
              </Link>
            </DropdownMenuItem>
            {isAuthenticated && (
              <>
                <DropdownMenuItem className="cursor-pointer hover:bg-white/30">
                  <User className="w-4 h-4 mr-2" />
                  {user?.email || "Profile"}
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-border/30" />
                <DropdownMenuItem
                  onClick={logout}
                  className="cursor-pointer hover:bg-white/30 text-destructive"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Log out
                </DropdownMenuItem>
              </>
            )}
            {!isAuthenticated && authStatus === "configured" && (
              <>
                <DropdownMenuSeparator className="bg-border/30" />
                <DropdownMenuItem asChild className="cursor-pointer hover:bg-white/30">
                  <Link to="/login" className="flex items-center w-full">
                    <LogIn className="w-4 h-4 mr-2" />
                    Sign In
                  </Link>
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </motion.header>
  );
};

