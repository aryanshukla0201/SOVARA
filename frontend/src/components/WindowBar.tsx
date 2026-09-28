import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Menu, Edit } from 'lucide-react';

interface WindowBarProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  onNewChat: () => void;
  className?: string;
}

export const WindowBar: React.FC<WindowBarProps> = ({
  sidebarOpen,
  onToggleSidebar,
  onNewChat,
  className = '',
}) => {
  return (
    <AnimatePresence initial={false}>
      {!sidebarOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0, x: -16 }}
          animate={{ width: 48, opacity: 1, x: 0 }}
          exit={{ width: 0, opacity: 0, x: -16 }}
          transition={{
            type: 'spring',
            damping: 30,
            stiffness: 280,
            mass: 0.8,
          }}
          className={`hidden md:flex flex-col items-center gap-3 py-4 px-2 text-[#71717a] select-none z-30 shrink-0 overflow-hidden ${className}`}
        >
          <button
            onClick={onToggleSidebar}
            className="p-2 rounded-xl text-[#94949f] hover:text-white hover:bg-[#1a1a24] transition-all duration-150 active:scale-95"
            title="Open sidebar"
            aria-label="Open sidebar"
          >
            <Menu size={18} />
          </button>

          <button
            onClick={onNewChat}
            className="p-2 rounded-xl text-[#94949f] hover:text-white hover:bg-[#1a1a24] transition-all duration-150 active:scale-95"
            title="New chat"
            aria-label="New chat"
          >
            <Edit size={16} />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
