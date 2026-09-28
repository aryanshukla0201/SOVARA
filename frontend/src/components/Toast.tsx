import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle2, Download } from 'lucide-react';

interface ToastProps {
  message: string | null;
  type?: 'success' | 'download';
  onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({ message, type = 'success', onClose }) => {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 15, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#16161d] border border-[#2b2b38] shadow-2xl text-xs text-white"
        >
          {type === 'download' ? (
            <Download size={15} className="text-[#7adfd4] shrink-0" />
          ) : (
            <CheckCircle2 size={15} className="text-[#34d399] shrink-0" />
          )}
          <span className="font-medium text-[#e4e4e7]">{message}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
