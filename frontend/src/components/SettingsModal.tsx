import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, User, Shield, Terminal, Database, Sparkles, Check } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="relative z-10 w-full max-w-lg max-h-[90vh] overflow-y-auto bg-[#0e0e12] border border-[#24242e] rounded-2xl p-4 sm:p-6 shadow-2xl select-none scrollbar-none"
          >
            {/* Header */}
            <div className="flex items-center justify-between pb-3 sm:pb-4 border-b border-[#1c1c24]">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-[#181822] text-[#7adfd4]">
                  <Sparkles size={16} />
                </div>
                <h3 className="text-sm sm:text-base font-bold text-white tracking-tight">
                  Sovara Settings
                </h3>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-[#71717a] hover:text-white hover:bg-[#1a1a22] transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            {/* Content */}
            <div className="py-4 space-y-4 text-xs">
              {/* Profile Card */}
              <div className="p-3 sm:p-3.5 rounded-xl bg-[#14141a] border border-[#202028] flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-0">
                <div className="flex items-center gap-3">
                  <div className="w-9 sm:w-10 h-9 sm:h-10 rounded-full bg-[#1c1c26] border border-[#2f2f3d] flex items-center justify-center font-bold text-white text-xs sm:text-sm shrink-0">
                    AM
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs sm:text-sm font-semibold text-white truncate">Arpit Maaal</div>
                    <div className="text-[11px] sm:text-xs text-[#71717a] truncate">Senior intern • arpit.maaal@sovara.local</div>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full text-[10.5px] sm:text-[11px] bg-[#162723] text-[#7adfd4] border border-[#23453e] self-start sm:self-auto">
                  Active Workspace
                </span>
              </div>

              {/* Workspace details */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between p-3 rounded-lg bg-[#121217] border border-[#1e1e26]">
                  <div className="flex items-center gap-2.5 text-[#d4d4dc]">
                    <Shield size={14} className="text-[#7adfd4]" />
                    <span>Private Workspace</span>
                  </div>
                  <span className="text-[11px] text-[#34d399] font-medium flex items-center gap-1">
                    <Check size={12} /> Enabled
                  </span>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-[#121217] border border-[#1e1e26]">
                  <div className="flex items-center gap-2.5 text-[#d4d4dc]">
                    <Terminal size={14} className="text-[#7adfd4]" />
                    <span>Local Sandboxed Execution</span>
                  </div>
                  <span className="text-[11px] text-[#a1a1aa]">v2.6 Local</span>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-[#121217] border border-[#1e1e26]">
                  <div className="flex items-center gap-2.5 text-[#d4d4dc]">
                    <Database size={14} className="text-[#7adfd4]" />
                    <span>Knowledge Vault Sync</span>
                  </div>
                  <span className="text-[11px] text-[#34d399] font-medium flex items-center gap-1">
                    <Check size={12} /> Real-time
                  </span>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="pt-3 border-t border-[#1c1c24] flex justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-[#1e1e28] hover:bg-[#282836] text-xs font-semibold text-white transition-colors"
              >
                Close
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
