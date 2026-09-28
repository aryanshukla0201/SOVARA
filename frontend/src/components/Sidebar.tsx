import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Edit, 
  Library, 
  Sparkles, 
  Settings, 
  Menu, 
  X,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Pin,
  Archive,
  Trash2,
  Check,
  ChevronDown,
  ChevronRight,
  RotateCcw
} from 'lucide-react';
import { NavigationTab, ChatSession } from '../types';
import { SovaraSidebarLogo } from './SovaraLogo';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  onSelectChat: (chatId: string) => void;
  onNewChat?: () => void;
  onOpenSettings: () => void;
  activeChatTitle?: string;
  activeChatId?: string;
  chatSessions?: ChatSession[];
  onRenameChat?: (id: string, newTitle: string) => void;
  onPinChat?: (id: string) => void;
  onArchiveChat?: (id: string) => void;
  onDeleteChat?: (id: string) => void;
  recentChats?: string[];
  isMobile?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onToggle,
  activeTab,
  onSelectTab,
  onSelectChat,
  onNewChat,
  onOpenSettings,
  activeChatTitle = 'Help me with homework',
  activeChatId,
  chatSessions,
  onRenameChat,
  onPinChat,
  onArchiveChat,
  onDeleteChat,
  isMobile = false,
}) => {
  // Normalize chat sessions from props or fallback to recentChats strings
  const sessions: ChatSession[] = chatSessions ?? [];

  const [activeMenuChatId, setActiveMenuChatId] = useState<string | null>(null);
  const [menuCoords, setMenuCoords] = useState<{ top: number; left: number } | null>(null);
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editTitleValue, setEditTitleValue] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  // Close 3-dot menu on click outside or escape
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setActiveMenuChatId(null);
        setMenuCoords(null);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveMenuChatId(null);
        setMenuCoords(null);
        setEditingChatId(null);
      }
    };

    if (activeMenuChatId) {
      document.addEventListener('pointerdown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('pointerdown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeMenuChatId]);

  // Focus rename input on entering edit mode
  useEffect(() => {
    if (editingChatId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [editingChatId]);

  const activeChats = sessions.filter((s) => !s.isArchived);
  const archivedChats = sessions.filter((s) => s.isArchived);

  // Sort pinned chats to top
  const sortedActiveChats = [...activeChats].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return 0;
  });

  const handleToggleMenu = (id: string, e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    if (activeMenuChatId === id) {
      setActiveMenuChatId(null);
      setMenuCoords(null);
      return;
    }
    const rect = e.currentTarget.getBoundingClientRect();
    const dropdownWidth = 160;
    const dropdownHeight = 160;

    let top = rect.bottom + 4;
    if (top + dropdownHeight > window.innerHeight) {
      top = rect.top - dropdownHeight - 4;
    }
    let left = rect.right - dropdownWidth;
    if (left < 10) left = 10;

    setMenuCoords({ top, left });
    setActiveMenuChatId(id);
  };

  const handleStartRename = (session: ChatSession) => {
    setEditingChatId(session.id);
    setEditTitleValue(session.title);
    setActiveMenuChatId(null);
    setMenuCoords(null);
  };

  const handleSaveRename = (id: string) => {
    const trimmed = editTitleValue.trim();
    if (trimmed && onRenameChat) {
      onRenameChat(id, trimmed);
    }
    setEditingChatId(null);
  };

  const handleCancelRename = () => {
    setEditingChatId(null);
  };

  const selectedMenuSession = sessions.find((s) => s.id === activeMenuChatId);

  const content = (
    <div className="h-full flex flex-col justify-between py-4 px-3 bg-[#0d0d10] border-r border-[#1e1e23] w-64 select-none relative">
      {/* Top Header & Navigation */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Brand Lockup & Collapse Button */}
        <div className="flex items-center justify-between px-2 mb-6 shrink-0">
          <button 
            onClick={() => onSelectTab('chat')}
            className="flex items-center gap-2 hover:opacity-85 transition-opacity text-left active:scale-[0.98]"
          >
            <SovaraSidebarLogo size="md" />
          </button>
          
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg text-[#858591] hover:text-white hover:bg-[#1a1a20] transition-colors active:scale-95"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <Menu size={18} />
          </button>
        </div>

        {/* Primary Nav Items */}
        <div className="space-y-1 shrink-0">
          <motion.button
            whileHover={{ x: 2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => {
              if (onNewChat) {
                onNewChat();
              } else {
                onSelectTab('chat');
                onSelectChat('New Chat');
              }
            }}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium text-[#c4c4cc] hover:text-white hover:bg-[#18181e] transition-colors group relative"
          >
            <Edit size={16} className="text-[#9999a5] group-hover:text-white transition-colors" />
            <span>New chat</span>
          </motion.button>

          <button
            onClick={() => onSelectTab('vault')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium transition-colors relative active:scale-[0.99] ${
              activeTab === 'vault' ? 'text-white font-semibold' : 'text-[#c4c4cc] hover:text-white hover:bg-[#15151b]'
            }`}
          >
            {activeTab === 'vault' && (
              <motion.div
                layoutId="sidebarActiveIndicator"
                className="absolute inset-0 bg-[#191922] border border-[#2b2b38] rounded-xl shadow-xs"
                transition={{ type: 'spring', damping: 28, stiffness: 320 }}
              />
            )}
            <Library 
              size={16} 
              className={`relative z-10 transition-colors ${activeTab === 'vault' ? 'text-[#7adfd4]' : 'text-[#9999a5]'}`} 
            />
            <span className="relative z-10">Knowledge Vault</span>
          </button>

          <button
            onClick={() => onSelectTab('artifacts')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium transition-colors relative active:scale-[0.99] ${
              activeTab === 'artifacts' ? 'text-white font-semibold' : 'text-[#c4c4cc] hover:text-white hover:bg-[#15151b]'
            }`}
          >
            {activeTab === 'artifacts' && (
              <motion.div
                layoutId="sidebarActiveIndicator"
                className="absolute inset-0 bg-[#191922] border border-[#2b2b38] rounded-xl shadow-xs"
                transition={{ type: 'spring', damping: 28, stiffness: 320 }}
              />
            )}
            <Sparkles 
              size={16} 
              className={`relative z-10 transition-colors ${activeTab === 'artifacts' ? 'text-[#7adfd4]' : 'text-[#9999a5]'}`} 
            />
            <span className="relative z-10">Artifacts</span>
          </button>
        </div>

        {/* Recent Chats Section with custom scrolling */}
        <div className="mt-7 flex-1 flex flex-col min-h-0 overflow-y-auto scrollbar-none pr-0.5">
          <div className="flex items-center justify-between px-3 mb-2 shrink-0">
            <span className="text-[11px] font-medium text-[#686873] tracking-wide uppercase">
              Recent chats
            </span>
            <span className="text-[10px] text-[#555562] font-mono">
              {sortedActiveChats.length}
            </span>
          </div>

          <div className="space-y-0.5 flex-1">
            {sortedActiveChats.map((chat) => {
              const isCurrent = activeTab === 'chat' && (activeChatId ? activeChatId === chat.id : activeChatTitle === chat.title);
              const isEditing = editingChatId === chat.id;

              return (
                <div key={chat.id} className="relative group">
                  {isEditing ? (
                    <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-xl bg-[#161622] border border-[#7adfd4]/50 shadow-sm">
                      <input
                        ref={renameInputRef}
                        type="text"
                        value={editTitleValue}
                        onChange={(e) => setEditTitleValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveRename(chat.id);
                          if (e.key === 'Escape') handleCancelRename();
                        }}
                        className="flex-1 bg-transparent text-xs text-white focus:outline-none min-w-0"
                      />
                      <button
                        onClick={() => handleSaveRename(chat.id)}
                        className="p-1 rounded text-[#7adfd4] hover:bg-[#20202e] transition-colors"
                        title="Save rename"
                      >
                        <Check size={13} />
                      </button>
                      <button
                        onClick={handleCancelRename}
                        className="p-1 rounded text-[#828292] hover:text-white hover:bg-[#20202e] transition-colors"
                        title="Cancel"
                      >
                        <X size={13} />
                      </button>
                    </div>
                  ) : (
                    <div
                      onClick={() => {
                        onSelectTab('chat');
                        onSelectChat(chat.id);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-[13px] transition-colors cursor-pointer group ${
                        isCurrent
                          ? 'text-white bg-[#17171e] font-medium shadow-xs border border-[#23232c]'
                          : 'text-[#9e9ea8] hover:text-white hover:bg-[#141419]'
                      }`}
                      title={chat.title}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1 mr-1">
                        {chat.isPinned && (
                          <Pin size={11} className="shrink-0 text-[#7adfd4] fill-[#7adfd4]/25 -rotate-45" />
                        )}
                        <span className="truncate">{chat.title}</span>
                      </div>

                      {/* 3-dot menu trigger button */}
                      <button
                        type="button"
                        onClick={(e) => handleToggleMenu(chat.id, e)}
                        className={`p-1 rounded-md text-[#787886] hover:text-white hover:bg-[#22222d] transition-all shrink-0 ${
                          activeMenuChatId === chat.id ? 'opacity-100 bg-[#22222d] text-white' : 'opacity-0 group-hover:opacity-100'
                        }`}
                        title="Chat options"
                        aria-label="Chat options"
                      >
                        <MoreHorizontal size={14} />
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Archived Chats Collapsible Subsection */}
          {archivedChats.length > 0 && (
            <div className="mt-4 pt-3 border-t border-[#181820]">
              <button
                onClick={() => setShowArchived((prev) => !prev)}
                className="w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs text-[#6e6e7c] hover:text-[#d1d1dc] hover:bg-[#14141a] transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Archive size={12} className="text-[#6e6e7c]" />
                  <span>Archived ({archivedChats.length})</span>
                </div>
                {showArchived ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>

              <AnimatePresence>
                {showArchived && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-0.5 mt-1 overflow-hidden"
                  >
                    {archivedChats.map((chat) => (
                      <div
                        key={chat.id}
                        className="flex items-center justify-between px-3 py-1.5 rounded-lg text-xs text-[#737380] hover:text-white hover:bg-[#141419] group cursor-pointer"
                        onClick={() => {
                          onSelectTab('chat');
                          onSelectChat(chat.id);
                        }}
                      >
                        <span className="truncate flex-1 mr-1">{chat.title}</span>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onArchiveChat?.(chat.id);
                            }}
                            className="p-1 rounded text-[#71717e] hover:text-[#7adfd4] hover:bg-[#1d1d26] transition-colors"
                            title="Unarchive"
                          >
                            <RotateCcw size={12} />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onDeleteChat?.(chat.id);
                            }}
                            className="p-1 rounded text-[#71717e] hover:text-red-400 hover:bg-red-500/15 transition-colors"
                            title="Delete"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      {/* User Profile & Settings Footer */}
      <div className="pt-3 border-t border-[#1a1a20] shrink-0">
        <div className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-[#16161b] transition-colors group">
          <div className="flex items-center gap-2.5 min-w-0">
            {/* AM Avatar */}
            <div className="w-8 h-8 rounded-full bg-[#181820] border border-[#2c2c36] flex items-center justify-center text-xs font-semibold text-[#e4e4e7] shrink-0 tracking-wider">
              AM
            </div>
            <div className="min-w-0 text-left">
              <div className="text-xs font-semibold text-[#f4f4f5] truncate">
                Arpit Maaal
              </div>
              <div className="text-[11px] text-[#71717a] truncate">
                Senior intern
              </div>
            </div>
          </div>

          <button
            onClick={onOpenSettings}
            className="p-1.5 rounded-md text-[#71717a] hover:text-white hover:bg-[#202028] transition-colors"
            title="User settings"
            aria-label="User settings"
          >
            <Settings size={15} />
          </button>
        </div>
      </div>

      {/* Floating 3-dot Popover Menu */}
      {activeMenuChatId && menuCoords && selectedMenuSession && (
        <div
          ref={menuRef}
          style={{ top: menuCoords.top, left: menuCoords.left }}
          className="fixed z-50 w-44 bg-[#14141c] border border-[#262634] rounded-xl shadow-2xl p-1.5 space-y-0.5 text-xs text-[#d1d1dc] backdrop-blur-md"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Rename */}
          <button
            onClick={() => handleStartRename(selectedMenuSession)}
            className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-[#1f1f2b] hover:text-white transition-colors text-left"
          >
            <Pencil size={13} className="text-[#888898]" />
            <span>Rename</span>
          </button>

          {/* Pin / Unpin */}
          <button
            onClick={() => {
              onPinChat?.(selectedMenuSession.id);
              setActiveMenuChatId(null);
            }}
            className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-[#1f1f2b] hover:text-white transition-colors text-left"
          >
            <Pin size={13} className={selectedMenuSession.isPinned ? "text-[#7adfd4]" : "text-[#888898]"} />
            <span>{selectedMenuSession.isPinned ? 'Unpin chat' : 'Pin chat'}</span>
          </button>

          {/* Archive / Unarchive */}
          <button
            onClick={() => {
              onArchiveChat?.(selectedMenuSession.id);
              setActiveMenuChatId(null);
            }}
            className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-[#1f1f2b] hover:text-white transition-colors text-left"
          >
            <Archive size={13} className="text-[#888898]" />
            <span>{selectedMenuSession.isArchived ? 'Unarchive' : 'Archive'}</span>
          </button>

          <div className="h-px bg-[#20202c] my-1" />

          {/* Delete */}
          <button
            onClick={() => {
              onDeleteChat?.(selectedMenuSession.id);
              setActiveMenuChatId(null);
            }}
            className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-red-500/15 text-red-400 hover:text-red-300 transition-colors text-left"
          >
            <Trash2 size={13} />
            <span>Delete</span>
          </button>
        </div>
      )}
    </div>
  );

  // Mobile drawer mode
  if (isMobile) {
    return (
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onToggle}
              className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            />
            {/* Drawer */}
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 28, stiffness: 300 }}
              className="relative z-10 h-full"
            >
              {content}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    );
  }

  // Desktop smooth calibrated spring collapsing sidebar
  return (
    <AnimatePresence initial={false}>
      {isOpen && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 256, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{
            type: 'spring',
            damping: 30,
            stiffness: 280,
            mass: 0.8,
          }}
          className="h-full shrink-0 overflow-hidden z-20"
        >
          <motion.div
            initial={{ x: -40, opacity: 0.5 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -40, opacity: 0 }}
            transition={{
              type: 'spring',
              damping: 30,
              stiffness: 280,
              mass: 0.8,
            }}
            className="h-full w-64"
          >
            {content}
          </motion.div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
};


