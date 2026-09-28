import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Trash2, Edit2 } from 'lucide-react';

interface DeleteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmDelete: () => void;
  onSwitchToEdit: () => void;
  documentTitle?: string;
}

export const DeleteModal: React.FC<DeleteModalProps> = ({
  isOpen,
  onClose,
  onConfirmDelete,
  onSwitchToEdit,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop with blur */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm"
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="relative z-10 w-[92vw] sm:max-w-lg bg-[#0e0e11] border border-[#23232b] rounded-2xl p-5 sm:p-7 md:p-9 shadow-2xl text-center select-none"
          >
            {/* Title */}
            <h2 className="text-xl sm:text-2xl md:text-[26px] font-bold text-white tracking-tight mb-3 sm:mb-5">
              Permanently delete document?
            </h2>

            {/* Content description */}
            <div className="space-y-3 sm:space-y-4 text-[#a1a1aa] text-xs sm:text-sm md:text-[15px] leading-relaxed max-w-md mx-auto mb-6 sm:mb-8">
              <p>
                If deleted, documents can not be recovered, and context will also be deleted. Make sure you have backup of this document
              </p>
              <p className="text-[#d4d4d8] font-medium pt-1">
                Why not consider editing this document?
              </p>
            </div>

            {/* Buttons Row matching Frame 1321315918.svg exactly */}
            <div className="flex items-center justify-center gap-3 sm:gap-4">
              <button
                onClick={onConfirmDelete}
                className="flex items-center justify-center gap-2 px-5 sm:px-6 py-2.5 rounded-xl border border-[#dc2626]/70 bg-[#160b0d] hover:bg-[#280d11] text-white text-xs sm:text-sm font-semibold transition-all hover:border-[#ef4444] shadow-sm hover:scale-[1.02] active:scale-[0.98]"
              >
                <Trash2 size={16} className="text-[#ef4444]" />
                <span>Delete</span>
              </button>

              <button
                onClick={onSwitchToEdit}
                className="flex items-center justify-center gap-2 px-6 sm:px-7 py-2.5 rounded-xl border border-[#e4e4e7]/80 bg-[#121217] hover:bg-[#1e1e26] text-white text-xs sm:text-sm font-semibold transition-all hover:border-white shadow-sm hover:scale-[1.02] active:scale-[0.98]"
              >
                <Edit2 size={15} className="text-white" />
                <span>Edit</span>
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
