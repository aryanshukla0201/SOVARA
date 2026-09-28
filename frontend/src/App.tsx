/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { NavigationTab, VaultDocument, ArtifactItem, ChatSession, ChatMessage } from './types';
import { Sidebar } from './components/Sidebar';
import { WindowBar } from './components/WindowBar';
import { MainChat } from './components/MainChat';
import { KnowledgeVault } from './components/KnowledgeVault';
import { ArtifactsView } from './components/ArtifactsView';
import { RightBar } from './components/RightBar';
import { SettingsModal } from './components/SettingsModal';
import { Toast } from './components/Toast';
import { Menu, Edit, Sparkles, Plus, BookOpen } from 'lucide-react';
import { SovaraSidebarLogo } from './components/SovaraLogo';
import { sovaraApi } from './api/client';

export default function App() {
  const [activeTab, setActiveTab] = useState<NavigationTab>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [rightBarOpen, setRightBarOpen] = useState(false);
  const [rightBarTab, setRightBarTab] = useState<
    'activity' | 'sources' | 'approvals'
  >('activity');
  
  // Independent chat session state - default to fresh new chat on startup
  const [activeChatId, setActiveChatId] = useState<string>(() => localStorage.getItem('sovara_active_chat_id') ?? ('chat-session-' + Date.now()));
  const [activeChatTitle, setActiveChatTitle] = useState('New Chat');
  const [chatSessions, setChatSessions] = useState<ChatSession[]>(() => { try { const stored = localStorage.getItem('sovara_chat_sessions'); return stored ? JSON.parse(stored) : []; } catch { return []; } });
  const [chatMessages, setChatMessages] = useState<Record<string, ChatMessage[]>>(() => { try { const stored = localStorage.getItem('sovara_chat_messages'); return stored ? JSON.parse(stored) : {}; } catch { return {}; } });
  
  useEffect(() => {
    const restoredSession = chatSessions.find((session) => session.id === activeChatId);
    if (restoredSession) setActiveChatTitle(restoredSession.title);

    localStorage.setItem('sovara_chat_sessions', JSON.stringify(chatSessions));
  }, [chatSessions]);

  useEffect(() => {
    localStorage.setItem('sovara_chat_messages', JSON.stringify(chatMessages));
  }, [chatMessages]);

  useEffect(() => {
    localStorage.setItem('sovara_active_chat_id', activeChatId);
  }, [activeChatId]);
  // Data collections with CRUD capabilities
  const [vaultDocs, setVaultDocs] = useState<VaultDocument[]>([]);
      const loadVaultDocuments = async () => {
    try {
      const response = await sovaraApi.listVaultDocuments();

      const documents: VaultDocument[] = response.map((doc: any) => ({
        id: doc.document_id,
        name: doc.filename,
        pages: 0,
        uploadedDate: doc.created_at,
        typeBadge: doc.file_type?.toUpperCase() ?? 'FILE',
        fileName: doc.filename,
        description: '',
      }));

      setVaultDocs(documents);
    } catch (error) {
      console.error('Failed to load Vault documents:', error);
    }
  };

  useEffect(() => {
    void loadVaultDocuments();
  }, []);
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  
  // Modals & Feedback
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastType, setToastType] = useState<'success' | 'download'>('success');

  // Detect mobile viewport
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setSidebarOpen(false);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const showToast = (message: string, type: 'success' | 'download' = 'success') => {
    setToastMessage(message);
    setToastType(type);
    setTimeout(() => setToastMessage(null), 2500);
  };

  const handleAddVaultDocument = (newDoc: Omit<VaultDocument, 'id'>) => {
    const created: VaultDocument = {
      ...newDoc,
      id: `vault-${Date.now()}`,
    };
    setVaultDocs((prev) => [created, ...prev]);
    showToast(`Added "${created.name}" to Knowledge Vault`);
  };

  const handleUpdateVaultDocument = (updatedDoc: VaultDocument) => {
    setVaultDocs((prev) =>
      prev.map((d) => (d.id === updatedDoc.id ? updatedDoc : d))
    );
    showToast(`Updated "${updatedDoc.name}"`);
  };

  const handleDeleteVaultDocument = (id: string) => {
    setVaultDocs((prev) => prev.filter((d) => d.id !== id));
    showToast('Document permanently deleted from Knowledge Vault');
  };

  const handleDownloadFile = (fileName: string) => {
    showToast(`Downloading ${fileName}...`, 'download');
    const element = document.createElement('a');
    const file = new Blob(
      [`Sovara AI Exported Document: ${fileName}\nGenerated on ${new Date().toISOString()}`],
      { type: 'text/plain' }
    );
    element.href = URL.createObjectURL(file);
    element.download = fileName.endsWith('.pdf')
      ? fileName.replace('.pdf', '.txt')
      : `${fileName}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };
  const handleDeleteArtifact = (id: string) => {
    setArtifacts((prev) => prev.filter((a) => a.id !== id));
    showToast('Artifact deleted');
  };

  const handleOpenRightBar = (
    tab: 'activity' | 'sources' | 'approvals',
  ) => {
    setRightBarTab(tab);
    setRightBarOpen(true);
  };

  const handleRenameChat = (id: string, newTitle: string) => {
    setChatSessions((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
    );
    if (activeChatId === id) {
      setActiveChatTitle(newTitle);
    }
    showToast(`Chat renamed to "${newTitle}"`);
  };

  const handlePinChat = (id: string) => {
    setChatSessions((prev) =>
      prev.map((c) => {
        if (c.id === id) {
          const nextPinned = !c.isPinned;
          showToast(nextPinned ? 'Chat pinned to top' : 'Chat unpinned');
          return { ...c, isPinned: nextPinned };
        }
        return c;
      })
    );
  };

  const handleArchiveChat = (id: string) => {
    const target = chatSessions.find((c) => c.id === id);
    if (!target) return;
    const nextArchived = !target.isArchived;
    setChatSessions((prev) =>
      prev.map((c) => (c.id === id ? { ...c, isArchived: nextArchived } : c))
    );
    showToast(nextArchived ? 'Chat moved to archive' : 'Chat restored from archive');
    if (nextArchived && activeChatId === id) {
      handleNewChat();
    }
  };

  const handleDeleteChat = (id: string) => {
    setChatSessions((prev) => prev.filter((c) => c.id !== id));
    setChatMessages((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    showToast('Chat deleted');
    if (activeChatId === id) {
      handleNewChat();
    }
  };

  const handleSaveMessages = (chatId: string, msgs: ChatMessage[]) => {
    setChatMessages((prev) => ({
      ...prev,
      [chatId]: msgs,
    }));
  };

  const handleChatTitleUpdate = (chatId: string, newTitle: string) => {
    setActiveChatTitle(newTitle);
    setChatSessions((prev) => {
      const existing = prev.find((c) => c.id === chatId);
      if (existing) {
        return prev.map((c) => (c.id === chatId ? { ...c, title: newTitle } : c));
      }
      return [
        { id: chatId, title: newTitle, isPinned: false, isArchived: false, createdAt: Date.now() },
        ...prev,
      ];
    });
  };

  const handleNewChat = () => {
    const newId = `chat-session-${Date.now()}`;
    setActiveChatId(newId);
    setActiveChatTitle('New Chat');
    setChatMessages((prev) => ({ ...prev, [newId]: [] }));
    setActiveTab('chat');
    setRightBarOpen(false);
    if (isMobile) setSidebarOpen(false);
  };

  const handleSelectChat = (idOrTitle: string) => {
    if (idOrTitle === 'New Chat') {
      handleNewChat();
      return;
    }
    const foundSession = chatSessions.find((c) => c.id === idOrTitle || c.title === idOrTitle);
    if (foundSession) {
      setActiveChatId(foundSession.id);
      setActiveChatTitle(foundSession.title);
    } else {
      const newId = `chat-ref-${Date.now()}`;
      setActiveChatId(newId);
      setActiveChatTitle(idOrTitle);
      if (!chatMessages[newId]) {
        setChatMessages((prev) => ({
          ...prev,
          [newId]: [
            {
              id: `msg-${Date.now()}`,
              sender: 'sovara',
              text: `Workspace artifacts and context loaded for "${idOrTitle}". All documentation references are ready.`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              hasSources: true,
            },
          ],
        }));
      }
    }
    setActiveTab('chat');
    setRightBarOpen(false);
    if (isMobile) setSidebarOpen(false);
  };

  const getMobileHeaderTitle = () => {
    if (activeTab === 'chat') {
      return activeChatTitle === 'New Chat' ? 'Sovara' : activeChatTitle;
    }
    if (activeTab === 'vault') {
      return 'Knowledge Vault';
    }
    return 'Artifacts';
  };

  const handleConversationIdUpdate = (
    chatId: string,
    conversationId: string,
  ) => {
    setChatSessions((prev) => {
      const existingSession = prev.find((session) => session.id === chatId);

      if (existingSession) {
        return prev.map((session) =>
          session.id === chatId
            ? { ...session, conversationId }
            : session,
        );
      }

      return [
        ...prev,
        {
          id: chatId,
          title: activeChatTitle || 'New Chat',
          conversationId,
          createdAt: Date.now(),
        },
      ];
    });
  };

  const activeChatMessages = chatMessages[activeChatId] ?? [];
  const latestSovaraMessage = [...activeChatMessages]
    .reverse()
    .find((message) => message.sender === 'sovara');

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0a0a0d] text-[#e4e4e7] antialiased">
      {/* Collapsible Sidebar (Drawer on mobile, spring collapsing column on desktop) */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          if (isMobile) setSidebarOpen(false);
        }}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onOpenSettings={() => setIsSettingsOpen(true)}
        activeChatTitle={activeChatTitle}
        activeChatId={activeChatId}
        chatSessions={chatSessions}
        onRenameChat={handleRenameChat}
        onPinChat={handlePinChat}
        onArchiveChat={handleArchiveChat}
        onDeleteChat={handleDeleteChat}
        isMobile={isMobile}
      />

      {/* Main App Workspace */}
      <div className="flex-1 flex flex-col h-full min-w-0 relative overflow-hidden">
        {/* Sleek Mobile Navigation Header (Shown on < 768px devices) */}
        <header className="md:hidden flex items-center justify-between px-3.5 py-2.5 bg-[#0a0a0d] border-b border-[#181820] shrink-0 z-30 select-none">
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-xl text-[#94949f] hover:text-white hover:bg-[#16161e] transition-colors active:scale-95 shrink-0"
              title="Open menu"
              aria-label="Open menu"
            >
              <Menu size={18} />
            </button>

            <button 
              onClick={() => {
                setActiveTab('chat');
              }}
              className="flex items-center gap-2 min-w-0 text-left"
            >
              <span className="text-xs sm:text-sm font-semibold text-white tracking-tight truncate max-w-[160px] sm:max-w-xs">
                {getMobileHeaderTitle()}
              </span>
            </button>
          </div>

          {/* Quick Header Actions */}
          <div className="flex items-center gap-1 shrink-0">
            {activeTab === 'chat' && (
              <>
                <button
                  onClick={() => handleOpenRightBar('activity')}
                  className="p-2 rounded-xl text-[#858592] hover:text-[#7adfd4] hover:bg-[#16161e] transition-colors active:scale-95"
                  title="View activity"
                  aria-label="View activity"
                >
                  <Sparkles size={16} />
                </button>

                <button
                  onClick={handleNewChat}
                  className="p-2 rounded-xl text-[#858592] hover:text-white hover:bg-[#16161e] transition-colors active:scale-95"
                  title="New chat"
                  aria-label="New chat"
                >
                  <Edit size={16} />
                </button>
              </>
            )}

            {activeTab === 'vault' && (
              <button
                onClick={handleNewChat}
                className="p-2 rounded-xl text-[#858592] hover:text-white hover:bg-[#16161e] transition-colors active:scale-95"
                title="New chat"
              >
                <Edit size={16} />
              </button>
            )}

            {activeTab === 'artifacts' && (
              <button
                onClick={handleNewChat}
                className="p-2 rounded-xl text-[#858592] hover:text-white hover:bg-[#16161e] transition-colors active:scale-95"
                title="New chat"
              >
                <Edit size={16} />
              </button>
            )}
          </div>
        </header>

        {/* Workspace Body */}
        <div className="flex-1 flex h-full min-w-0 relative overflow-hidden">
          {/* Collapsed sidebar trigger rail (≡ and ✏) for Desktop */}
          <WindowBar
            sidebarOpen={sidebarOpen}
            onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
            onNewChat={handleNewChat}
            className="border-r border-[#1a1a22] bg-[#0c0c0f]"
          />

          {/* Dynamic Viewport Content */}
          <main className="flex-1 flex overflow-hidden relative">
            <AnimatePresence mode="wait">
              {activeTab === 'chat' && (
                <motion.div
                  key={activeChatId}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
                  className="flex-1 flex overflow-hidden relative"
                >
                  <MainChat
                    key={activeChatId}
                    chatId={activeChatId}
                    chatTitle={activeChatTitle}
                    conversationId={
                      chatSessions.find((session) => session.id === activeChatId)?.conversationId
                    }
                    initialMessages={chatMessages[activeChatId] || []}
                    onOpenRightBar={handleOpenRightBar}
                    onDownloadFile={handleDownloadFile}
                    sidebarOpen={sidebarOpen}
                    onChatTitleUpdate={handleChatTitleUpdate}
                    onSaveMessages={handleSaveMessages}
                    onConversationIdUpdate={handleConversationIdUpdate}
                  />
                </motion.div>
              )}

              {activeTab === 'vault' && (
                <motion.div
                  key="vault"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
                  className="flex-1 flex overflow-hidden relative"
                >
                  <KnowledgeVault
                    documents={vaultDocs}
                    onAddDocument={handleAddVaultDocument}
                    onRefreshDocuments={loadVaultDocuments}
                    onUpdateDocument={handleUpdateVaultDocument}
                    onDeleteDocument={handleDeleteVaultDocument}
                    onDownloadFile={handleDownloadFile}
                  />
                </motion.div>
              )}

              {activeTab === 'artifacts' && (
                <motion.div
                  key="artifacts"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
                  className="flex-1 flex overflow-hidden relative"
                >
                  <ArtifactsView
                    artifacts={artifacts}
                    onSelectChatReference={(chatRef) => {
                      setActiveChatTitle(chatRef);
                      setActiveTab('chat');
                    }}

                    onDeleteArtifact={handleDeleteArtifact}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Right Sliding Drawer for Activity & Sources */}
            <RightBar
              isOpen={rightBarOpen}
              onClose={() => setRightBarOpen(false)}
              defaultTab={rightBarTab}
              isMobile={isMobile}
              latestMessage={latestSovaraMessage}
            />
          </main>
        </div>
      </div>

      {/* Settings Dialog */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      {/* Notification Toast */}
      <Toast
        message={toastMessage}
        type={toastType}
        onClose={() => setToastMessage(null)}
      />
    </div>
  );
}









