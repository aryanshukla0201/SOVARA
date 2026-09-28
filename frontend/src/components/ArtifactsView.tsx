import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Search, 
  MoreHorizontal, 
  ExternalLink, 
  FileText, 
  Image as ImageIcon,
  Trash2,
  FileCode,
  X,
  FileSpreadsheet,
  File,
  Sparkles,
  Layers
} from 'lucide-react';
import { ArtifactItem } from '../types';

interface ArtifactsViewProps {
  artifacts: ArtifactItem[];
  onSelectChatReference: (chatRef: string) => void;
  onDeleteArtifact?: (id: string) => void;
}

type FilterType = 'All' | 'PDF' | 'Docx' | 'PPT' | 'Code' | '.Md' | 'Txt';

export const ArtifactsView: React.FC<ArtifactsViewProps> = ({
  artifacts,
  onSelectChatReference,
  onDeleteArtifact,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<FilterType>('All');
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const filterTabs: FilterType[] = ['All', 'PDF', 'Docx', 'PPT', 'Code', '.Md', 'Txt'];

  const filteredArtifacts = useMemo(() => {
    return artifacts.filter((art) => {
      const matchesFilter = selectedFilter === 'All' || art.fileType.toLowerCase() === selectedFilter.toLowerCase();
      const matchesSearch =
        art.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        art.chatReference.toLowerCase().includes(searchQuery.toLowerCase()) ||
        art.fileType.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
    });
  }, [artifacts, selectedFilter, searchQuery]);

  const getFileIcon = (fileType: string) => {
    const type = fileType.toLowerCase();
    if (type.includes('code')) {
      return <FileCode size={16} className="text-[#7adfd4]" />;
    }
    if (type.includes('pdf')) {
      return <FileText size={16} className="text-[#f87171]" />;
    }
    if (type.includes('docx')) {
      return <FileText size={16} className="text-[#60a5fa]" />;
    }
    if (type.includes('ppt')) {
      return <FileSpreadsheet size={16} className="text-[#fb923c]" />;
    }
    if (type.includes('image') || type.includes('png') || type.includes('svg')) {
      return <ImageIcon size={16} className="text-[#c084fc]" />;
    }
    return <File size={16} className="text-[#94a3b8]" />;
  };

  const getBadgeStyle = (fileType: string) => {
    const type = fileType.toLowerCase();
    if (type.includes('code')) return 'bg-[#7adfd4]/10 text-[#7adfd4]';
    if (type.includes('pdf')) return 'bg-[#ef4444]/10 text-[#fca5a5]';
    if (type.includes('docx')) return 'bg-[#3b82f6]/10 text-[#93c5fd]';
    if (type.includes('ppt')) return 'bg-[#f97316]/10 text-[#fdba74]';
    return 'bg-[#272732] text-[#a1a1aa]';
  };

  const isSearching = searchQuery.trim().length > 0;

  return (
    <div className="flex-1 flex flex-col h-full bg-[#09090c] overflow-y-auto px-4 sm:px-8 md:px-12 lg:px-16 py-6 sm:py-8 select-none">
      <div className="max-w-6xl w-full mx-auto flex-1 flex flex-col">
        {/* Header section with responsive typography and spacing */}
        <div className="mb-6 sm:mb-8">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 sm:gap-4">
            <div>
              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white tracking-tight">
                Artifacts
              </h1>
              <p className="text-xs sm:text-[13px] text-[#71717e] mt-1 sm:mt-1.5">
                Outputs, generated documents, and synthesized assets produced by Sovara
              </p>
            </div>

            <div className="text-xs text-[#555562] font-mono">
              {filteredArtifacts.length} {filteredArtifacts.length === 1 ? 'file' : 'files'}
            </div>
          </div>
        </div>

        {/* Control Bar: Search and Horizontal Scrolling Filters */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3.5 mb-6 sm:mb-8">
          {/* Minimalist Search Box */}
          <div className="relative w-full sm:w-80">
            <Search
              size={14}
              className={`absolute left-3.5 top-1/2 -translate-y-1/2 transition-colors duration-150 ${
                isSearching ? 'text-[#7adfd4]' : 'text-[#565664]'
              }`}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search artifacts..."
              className="w-full bg-[#111116] border border-[#1b1b24] rounded-xl pl-9 pr-8 py-2 text-xs text-[#e4e4e7] placeholder-[#50505d] focus:outline-none focus:border-[#7adfd4]/35 focus:bg-[#13131a] transition-colors"
            />
            <AnimatePresence>
              {searchQuery && (
                <motion.button
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0.12 }}
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded-md text-[#656574] hover:text-white transition-colors"
                  title="Clear search"
                  aria-label="Clear search"
                >
                  <X size={13} />
                </motion.button>
              )}
            </AnimatePresence>
          </div>

          {/* Minimalist Filter Navigation Tabs with touch-friendly scroll */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none -mx-1 px-1">
            {filterTabs.map((tab) => {
              const isSelected = selectedFilter === tab;
              return (
                <button
                  key={tab}
                  onClick={() => setSelectedFilter(tab)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 relative active:scale-95 ${
                    isSelected
                      ? 'text-white font-semibold'
                      : 'text-[#717180] hover:text-[#c4c4cf] hover:bg-[#111116]'
                  }`}
                >
                  {isSelected && (
                    <motion.div
                      layoutId="activeArtifactFilter"
                      className="absolute inset-0 bg-[#181824] border border-[#272738] rounded-lg shadow-xs"
                      transition={{ type: 'spring', damping: 28, stiffness: 320 }}
                    />
                  )}
                  <span className="relative z-10">{tab}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Listings or Empty State */}
        {filteredArtifacts.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.15 }}
            className="flex-1 min-h-[300px] sm:min-h-[360px] flex flex-col items-center justify-center text-center px-4 py-12 sm:py-16"
          >
            <div className="w-12 sm:w-14 h-12 sm:h-14 rounded-2xl bg-[#121218] flex items-center justify-center text-[#555566] mb-4">
              <Layers size={22} />
            </div>
            <h3 className="text-base sm:text-lg font-semibold text-white/90 tracking-tight">
              No artifacts found
            </h3>
            <p className="text-xs text-[#6e6e7d] mt-1.5 max-w-sm leading-relaxed">
              {isSearching ? 'No documents match your query. Try a different search term.' : 'Generated artifacts will appear here when artifact library sync is enabled.'}
            </p>
          </motion.div>
        ) : (
          <div className="flex-1 flex flex-col">
            {/* Desktop Column Headers (hidden on mobile) */}
            <div className="hidden sm:grid grid-cols-12 gap-4 px-4 pb-3 text-[11px] font-medium uppercase tracking-wider text-[#555562]">
              <div className="col-span-5">Name</div>
              <div className="col-span-2">Format</div>
              <div className="hidden md:block md:col-span-2">Generated</div>
              <div className="col-span-3 md:col-span-2">Origin Chat</div>
              <div className="col-span-2 md:col-span-1 text-right">Actions</div>
            </div>

            {/* List Items */}
            <div className="space-y-2 sm:space-y-1.5">
              {filteredArtifacts.map((art, idx) => (
                <motion.div
                  key={art.id}
                  initial={isSearching ? { opacity: 0 } : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    duration: isSearching ? 0.12 : 0.18,
                    delay: isSearching ? 0 : Math.min(idx * 0.02, 0.14),
                    ease: [0.16, 1, 0.3, 1],
                  }}
                  whileHover={{ y: -1 }}
                  className="rounded-xl bg-[#0e0e13]/60 sm:bg-transparent hover:bg-[#111116] border border-[#181822] sm:border-transparent transition-colors p-3 sm:px-4 sm:py-3.5 group relative"
                >
                  {/* MOBILE LAYOUT (< sm screens) */}
                  <div className="flex sm:hidden flex-col gap-2.5">
                    <div className="flex items-center justify-between gap-2.5">
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <div className="p-2 rounded-lg bg-[#14141c] shrink-0">
                          {getFileIcon(art.fileType)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-[13px] font-medium text-white/95 truncate">
                            {art.name}
                          </div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span className={`px-1.5 py-0.2 rounded text-[9.5px] font-medium tracking-wide uppercase ${getBadgeStyle(art.fileType)}`}>
                              {art.fileType}
                            </span>
                            <span className="text-[10.5px] text-[#636373]">•</span>
                            <span className="text-[10.5px] text-[#636373]">{art.pages}p</span>
                          </div>
                        </div>
                      </div>

                      {/* Mobile Actions */}
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          onClick={() => setActiveMenuId(activeMenuId === art.id ? null : art.id)}
                          className="p-1.5 rounded-lg text-[#71717e] hover:text-white hover:bg-[#181822] transition-colors"
                          title="More options"
                          aria-label="More options"
                        >
                          <MoreHorizontal size={14} />
                        </button>
                      </div>
                    </div>

                    {/* Mobile Secondary Row: Chat ref & Date */}
                    <div className="flex items-center justify-between text-[11px] text-[#636373] pt-1 border-t border-[#161620]">
                      <button
                        onClick={() => onSelectChatReference(art.chatReference)}
                        className="flex items-center gap-1 text-[#8e8e9c] hover:text-[#7adfd4] truncate max-w-[65%]"
                      >
                        <span className="truncate">{art.chatReference}</span>
                        <ExternalLink size={10} className="shrink-0 opacity-60" />
                      </button>
                      <span className="shrink-0">{art.generatedOn}</span>
                    </div>
                  </div>

                  {/* DESKTOP / TABLET LAYOUT (>= sm screens) */}
                  <div className="hidden sm:grid grid-cols-12 gap-4 items-center">
                    {/* File Name & Icon */}
                    <div className="col-span-5 flex items-center gap-3.5 min-w-0">
                      <div className="p-2.5 rounded-xl bg-[#14141c] shrink-0 group-hover:bg-[#181822] transition-colors">
                        {getFileIcon(art.fileType)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-[13.5px] font-medium text-white/95 truncate group-hover:text-white transition-colors">
                          {art.name}
                        </div>
                        <div className="text-[11px] text-[#636373] mt-0.5 flex items-center gap-2">
                          <span>{art.pages} pages</span>
                          <span>•</span>
                          <span>{art.uploadedDate}</span>
                        </div>
                      </div>
                    </div>

                    {/* Format Badge */}
                    <div className="col-span-2 flex items-center">
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-medium tracking-wide uppercase ${getBadgeStyle(art.fileType)}`}>
                        {art.fileType}
                      </span>
                    </div>

                    {/* Generated Date */}
                    <div className="hidden md:block md:col-span-2 text-xs text-[#6e6e7c]">
                      {art.generatedOn}
                    </div>

                    {/* Origin Chat Reference Link */}
                    <div className="col-span-3 md:col-span-2 min-w-0">
                      <button
                        onClick={() => onSelectChatReference(art.chatReference)}
                        className="flex items-center gap-1.5 text-xs text-[#8e8e9c] hover:text-[#7adfd4] transition-colors truncate max-w-full text-left group/link"
                        title={`Jump to chat: ${art.chatReference}`}
                      >
                        <span className="truncate">{art.chatReference}</span>
                        <ExternalLink size={11} className="shrink-0 opacity-40 group-hover/link:opacity-100 transition-opacity" />
                      </button>
                    </div>

                    {/* Action Controls */}
                    <div className="col-span-2 md:col-span-1 flex items-center justify-end gap-1 relative">
                      <button
                        onClick={() => setActiveMenuId(activeMenuId === art.id ? null : art.id)}
                        className="p-2 rounded-lg text-[#686878] hover:text-white hover:bg-[#181822] transition-all"
                        title="More options"
                        aria-label="More options"
                      >
                        <MoreHorizontal size={14} />
                      </button>
                    </div>
                  </div>

                  {/* Shared Dropdown Menu (Popout for both mobile and desktop) */}
                  <AnimatePresence>
                    {activeMenuId === art.id && (
                      <>
                        <div
                          className="fixed inset-0 z-30"
                          onClick={() => setActiveMenuId(null)}
                        />
                        <motion.div
                          initial={{ opacity: 0, scale: 0.96, y: -4 }}
                          animate={{ opacity: 1, scale: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.96, y: -4 }}
                          transition={{ duration: 0.12 }}
                          className="absolute right-3 sm:right-4 top-12 z-40 w-44 bg-[#13131a] border border-[#20202b] rounded-xl shadow-2xl py-1 text-xs select-none"
                        >

                          {onDeleteArtifact && (
                            <button
                              onClick={() => {
                                onDeleteArtifact(art.id);
                                setActiveMenuId(null);
                              }}
                              className="w-full flex items-center gap-2.5 px-3 py-2 text-[#f87171] hover:text-[#fca5a5] hover:bg-[#201014] transition-colors text-left border-t border-[#1c1c26] mt-1"
                            >
                              <Trash2 size={13} />
                              <span>Delete artifact</span>
                            </button>
                          )}
                        </motion.div>
                      </>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
