import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Plus, Search, FileText, Download, Edit3, Trash2, UploadCloud, Check, X, Loader2,
  ChevronDown, 
  ArrowLeft,
  Calendar,
  Layers,
  Sparkles,
  FileCheck
} from 'lucide-react';
import { VaultDocument } from '../types';
import { DeleteModal } from './DeleteModal';
import { sovaraApi } from '../api/client';

interface KnowledgeVaultProps {
  documents: VaultDocument[];
  onAddDocument: (doc: Omit<VaultDocument, 'id'>) => void;
  onUpdateDocument: (doc: VaultDocument) => void;
  onDeleteDocument: (id: string) => void;
  onDownloadFile: (fileName: string) => void;
  onRefreshDocuments: () => Promise<void>;
}

type VaultViewMode = 'default' | 'view' | 'add' | 'edit';

export const KnowledgeVault: React.FC<KnowledgeVaultProps> = ({
  documents,
  onAddDocument,
  onUpdateDocument,
  onDeleteDocument,
  onDownloadFile,
  onRefreshDocuments,
}) => {
  const [selectedDocId, setSelectedDocId] = useState<string | null>(
    documents.length > 0 ? documents[0].id : null
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<VaultViewMode>(
    documents.length > 0 ? 'view' : 'default'
  );
  // Mobile master-detail pane state ('list' shows files list, 'detail' shows doc view/form)
  const [mobilePane, setMobilePane] = useState<'list' | 'detail'>('list');
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  // Form states for Add / Edit
  const [formName, setFormName] = useState('');
  const [formType, setFormType] = useState('STANDARD');
  const [formDesc, setFormDesc] = useState('');
  const [formFileName, setFormFileName] = useState('Vendor_warrantyReport.pdf');
  const [formFileUploaded, setFormFileUploaded] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const selectedDoc = documents.find((d) => d.id === selectedDocId) || documents[0];

  const filteredDocs = useMemo(() => {
    return documents.filter((d) => {
      const q = searchQuery.toLowerCase();
      return (
        d.name.toLowerCase().includes(q) ||
        d.typeBadge.toLowerCase().includes(q) ||
        d.description.toLowerCase().includes(q)
      );
    });
  }, [documents, searchQuery]);

  const handleFileSelect = (file: File | null) => {
    if (!file) return;

    setSelectedFile(file);
    setFormFileName(file.name);
    setFormFileUploaded(true);
  };

  const handleStartAdd = () => {
    setFormName('');
    setFormType('STANDARD');
    setFormDesc('');
    setFormFileName('New_Specification.pdf');
    setFormFileUploaded(false);
    setViewMode('add');
    setMobilePane('detail');
  };

  const handleStartEdit = () => {
    if (!selectedDoc) return;
    setFormName(selectedDoc.name);
    setFormType(selectedDoc.typeBadge || 'RULEBOOK');
    setFormDesc(selectedDoc.description);
    setFormFileName(selectedDoc.fileName);
    setFormFileUploaded(true);
    setViewMode('edit');
    setMobilePane('detail');
  };

  const handleSelectDoc = (docId: string) => {
    setSelectedDocId(docId);
    setViewMode('view');
    setMobilePane('detail');
  };

  const handleSaveForm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;

    if (viewMode === 'add') {
      if (!selectedFile) return;

      setIsUploading(true);

      try {
        await sovaraApi.uploadVaultDocument(selectedFile);
        await onRefreshDocuments();
        setViewMode('view');
      } finally {
        setIsUploading(false);
      }

      return;
    } else if (viewMode === 'edit' && selectedDoc) {
      onUpdateDocument({
        ...selectedDoc,
        name: formName.trim(),
        typeBadge: formType.toUpperCase(),
        description: formDesc.trim(),
      });
      setViewMode('view');
    }
  };

  const handleCancelForm = () => {
    if (selectedDoc) {
      setViewMode('view');
    } else {
      setViewMode('default');
    }
  };

  const confirmDelete = () => {
    if (selectedDoc) {
      onDeleteDocument(selectedDoc.id);
      setIsDeleteModalOpen(false);
      const remaining = documents.filter((d) => d.id !== selectedDoc.id);
      if (remaining.length > 0) {
        setSelectedDocId(remaining[0].id);
        setViewMode('view');
      } else {
        setSelectedDocId(null);
        setViewMode('default');
        setMobilePane('list');
      }
    }
  };

  return (
    <div className="flex-1 flex flex-col md:flex-row h-full w-full bg-[#09090b] overflow-hidden select-none relative">
      {/* LEFT COLUMN: Vault Files Browser (Master List) */}
      <aside className={`w-full md:w-[320px] lg:w-[360px] h-full flex-col bg-[#0b0b0e] md:border-r md:border-[#15151a] shrink-0 ${
        mobilePane === 'list' ? 'flex' : 'hidden md:flex'
      }`}>
        {/* Header container */}
        <div className="px-4 sm:px-5 pt-4 sm:pt-6 pb-3 space-y-3.5">
          {/* Title & Counter */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <h2 className="text-lg sm:text-xl md:text-[22px] font-bold text-white tracking-tight">
                Vault Files
              </h2>
              <span className="text-[11px] sm:text-xs font-mono font-medium text-[#717182] px-2 py-0.5 rounded-md bg-[#14141c]">
                {documents.length}
              </span>
            </div>

            <button
              onClick={handleStartAdd}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#7adfd4] hover:text-[#9feee6] bg-[#121c1b] hover:bg-[#172725] border border-[#7adfd4]/25 transition-all active:scale-95 shadow-xs"
              title="Add document to vault"
            >
              <Plus size={13} className="stroke-[2.5]" />
              <span>Add</span>
            </button>
          </div>

          {/* Minimal Search Input */}
          <div className="relative">
            <Search 
              size={13} 
              className={`absolute left-3.5 top-1/2 -translate-y-1/2 transition-colors duration-150 ${
                searchQuery ? 'text-[#7adfd4]' : 'text-[#565664]'
              }`} 
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search files..."
              className="w-full bg-[#121217] rounded-xl pl-9 pr-8 py-2 text-xs text-[#e4e4e7] placeholder-[#4f4f5a] focus:outline-none focus:ring-1 focus:ring-[#7adfd4]/30 focus:bg-[#14141a] transition-all"
            />
            <AnimatePresence>
              {searchQuery && (
                <motion.button
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0.12 }}
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded-md text-[#5a5a68] hover:text-white transition-colors"
                  title="Clear search"
                  aria-label="Clear search"
                >
                  <X size={12} />
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Minimal Files List */}
        <div className="flex-1 overflow-y-auto px-2.5 sm:px-3 py-2 space-y-1 scrollbar-none">
          {filteredDocs.length === 0 ? (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.15 }}
              className="h-56 flex flex-col items-center justify-center px-4 py-8 text-center text-[#555562]"
            >
              <FileText size={22} className="stroke-[1.5] text-[#33333d] mb-2" />
              <div className="text-xs text-[#80808c] font-medium">No matching files</div>
              <div className="text-[11px] text-[#555562] mt-0.5">Try searching with another keyword</div>
            </motion.div>
          ) : (
            filteredDocs.map((doc) => {
              const isSelected = selectedDocId === doc.id;
              return (
                <button
                  key={doc.id}
                  onClick={() => handleSelectDoc(doc.id)}
                  className={`w-full text-left px-3.5 py-3 rounded-xl transition-all flex items-start gap-3 group relative active:scale-[0.99] ${
                    isSelected
                      ? 'bg-[#15151e] text-white shadow-xs border border-[#222230]'
                      : 'text-[#8e8e98] hover:bg-[#111116] hover:text-[#d0d0d8] border border-transparent'
                  }`}
                >
                  <FileText 
                    size={15} 
                    className={`shrink-0 mt-0.5 transition-colors ${
                      isSelected ? 'text-[#7adfd4]' : 'text-[#484854] group-hover:text-[#888896]'
                    }`} 
                  />

                  <div className="min-w-0 flex-1">
                    <div className={`text-[12.5px] font-medium leading-snug truncate ${
                      isSelected ? 'text-white' : 'text-[#c8c8d2] group-hover:text-white'
                    }`}>
                      {doc.name}
                    </div>

                    <div className="text-[11px] text-[#595968] mt-1.5 flex items-center gap-2">
                      <span className="font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#161620] text-[#717180]">
                        {doc.typeBadge}
                      </span>
                      <span>•</span>
                      <span>{doc.pages}p</span>
                      <span>•</span>
                      <span className="truncate">{doc.uploadedDate}</span>
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </aside>

      {/* RIGHT CANVAS: Document Detail / Form View */}
      <main className={`flex-1 h-full overflow-y-auto px-4 sm:px-8 md:px-10 lg:px-14 py-5 sm:py-8 md:py-10 flex-col bg-[#09090b] ${
        mobilePane === 'detail' ? 'flex' : 'hidden md:flex'
      }`}>
        <AnimatePresence mode="wait">
          {/* Default / Empty State */}
          {viewMode === 'default' && (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="flex-1 flex flex-col items-center justify-center text-center max-w-sm mx-auto px-4 py-12"
            >
              <div className="w-12 h-12 rounded-xl bg-[#121217] flex items-center justify-center text-[#7adfd4] mb-4">
                <Sparkles size={20} />
              </div>
              <h2 className="text-base font-semibold text-white mb-1.5 tracking-tight">
                Knowledge Context Vault
              </h2>
              <p className="text-xs text-[#6e6e7c] leading-relaxed mb-6">
                Select a file from the sidebar to inspect its parameters, or upload manuals and standards for grounded reasoning.
              </p>
              <button
                onClick={handleStartAdd}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#7adfd4] hover:bg-[#6bd0c5] text-black text-xs font-semibold transition-all active:scale-95 shadow-sm shadow-[#7adfd4]/10"
              >
                <Plus size={14} className="stroke-[2.5]" />
                <span>Add Document</span>
              </button>
            </motion.div>
          )}

          {/* View Document State */}
          {viewMode === 'view' && selectedDoc && (
            <motion.div
              key={selectedDoc.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
              className="max-w-2xl w-full mx-auto space-y-5 sm:space-y-7"
            >
              {/* Minimal Action Toolbar */}
              <div className="flex items-center justify-between pb-1">
                {/* Back to Files List on Mobile */}
                <button
                  onClick={() => setMobilePane('list')}
                  className="md:hidden flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#14141c] text-xs font-medium text-[#c4c4d0] hover:text-white transition-colors"
                >
                  <ArrowLeft size={14} />
                  <span>Files</span>
                </button>

                <div className="text-[11px] font-mono tracking-wider uppercase text-[#5a5a66] hidden md:block">
                  Vault / {selectedDoc.typeBadge}
                </div>

                <div className="flex items-center gap-1.5 ml-auto">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => onDownloadFile(selectedDoc.fileName)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#8e8e98] hover:text-white hover:bg-[#14141a] transition-all"
                    title="Download attachment"
                  >
                    <Download size={13} />
                    <span className="hidden sm:inline">Download</span>
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={handleStartEdit}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#8e8e98] hover:text-white hover:bg-[#14141a] transition-all"
                    title="Edit metadata"
                  >
                    <Edit3 size={13} />
                    <span className="hidden sm:inline">Edit</span>
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.94 }}
                    onClick={() => setIsDeleteModalOpen(true)}
                    className="p-1.5 rounded-lg text-[#666672] hover:text-[#f87171] hover:bg-[#1a1114] transition-all ml-1"
                    title="Delete file"
                  >
                    <Trash2 size={13} />
                  </motion.button>
                </div>
              </div>

              {/* Document Title & Meta Line */}
              <div className="space-y-2.5">
                <h2 className="text-lg sm:text-xl md:text-2xl font-semibold text-white tracking-tight leading-snug">
                  {selectedDoc.name}
                </h2>

                <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs text-[#5e5e6b]">
                  <span className="flex items-center gap-1 text-[#7adfd4] text-[11px] font-medium">
                    <FileCheck size={13} />
                    Active Context
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Calendar size={12} />
                    {selectedDoc.uploadedDate}
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Layers size={12} />
                    {selectedDoc.pages} pages
                  </span>
                </div>
              </div>

              {/* Attachment Strip */}
              <motion.div 
                whileHover={{ borderColor: '#2b2b38', backgroundColor: '#13131a' }}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl bg-[#111115] border border-[#1b1b24] transition-colors gap-2 sm:gap-0 my-2 shadow-xs"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <FileText size={16} className="text-[#7adfd4] shrink-0" />
                  <span className="text-xs font-medium text-white/90 truncate">
                    {selectedDoc.fileName}
                  </span>
                </div>
                <span className="text-[11px] text-[#555562] font-mono shrink-0 sm:ml-3">
                  {selectedDoc.comparisonType || 'Indexed PDF'}
                </span>
              </motion.div>

              {/* Document Context Description */}
              <div className="space-y-2.5 pt-2">
                <div className="text-[11px] font-medium uppercase tracking-wider text-[#555562]">
                  Context & Directives
                </div>
                <p className="text-xs sm:text-[13px] leading-relaxed text-[#b4b4bf] whitespace-pre-line font-normal">
                  {selectedDoc.description}
                </p>
              </div>
            </motion.div>
          )}

          {/* Add Document State */}
          {viewMode === 'add' && (
            <motion.form
              key="add-form"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
              onSubmit={handleSaveForm}
              className="max-w-xl w-full mx-auto space-y-5 sm:space-y-6 py-2"
            >
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <h2 className="text-base sm:text-lg font-semibold text-white tracking-tight">
                    Add Document
                  </h2>
                  <p className="text-xs text-[#6e6e7c]">
                    Upload context files for reference in chat queries.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setMobilePane('list')}
                  className="md:hidden flex items-center gap-1 text-xs text-[#71717e] hover:text-white p-1.5"
                >
                  <ArrowLeft size={14} />
                  <span>Files</span>
                </button>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[#888896]">
                  File Name
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g. ISO-27001 Security Standard"
                  className="w-full bg-[#111115] rounded-xl px-4 py-2.5 text-xs text-white placeholder-[#4c4c58] focus:outline-none focus:ring-1 focus:ring-[#7adfd4]/40 transition-all"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <label
                  className={`flex items-center gap-3 p-3.5 rounded-xl cursor-pointer transition-all ${
                    formFileUploaded
                      ? 'bg-[#101918] text-[#7adfd4]'
                      : 'bg-[#111115] hover:bg-[#14141a] text-[#888896]'
                  }`}
                >
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    className="hidden"
                    onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
                  />
                  <UploadCloud size={16} className="text-[#7adfd4] shrink-0" />
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-white truncate">
                      {formFileUploaded ? formFileName : 'Attach file'}
                    </div>
                    <div className="text-[10px] text-[#555562]">PDF, DOCX, TXT</div>
                  </div>
                </label>

                <div className="relative">
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                    className="w-full h-full bg-[#111115] rounded-xl px-3.5 py-2.5 text-xs text-white appearance-none focus:outline-none focus:ring-1 focus:ring-[#7adfd4]/40"
                  >
                    <option value="STANDARD">Standard</option>
                    <option value="RULEBOOK">Rulebook</option>
                    <option value="MANUAL">Manual</option>
                    <option value="SOP">SOP</option>
                    <option value="GUIDELINE">Guideline</option>
                  </select>
                  <ChevronDown size={14} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#555562] pointer-events-none" />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[#888896]">
                  Context Summary
                </label>
                <textarea
                  required
                  rows={4}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="Describe key directives, policies, or domain specifications..."
                  className="w-full bg-[#111115] rounded-xl p-3.5 text-xs text-white placeholder-[#4c4c58] focus:outline-none focus:ring-1 focus:ring-[#7adfd4]/40 leading-relaxed"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={isUploading || !selectedFile}
                  className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-[#7adfd4] hover:bg-[#6bd0c5] text-black text-xs font-semibold transition-all active:scale-95 shadow-sm shadow-[#7adfd4]/10 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? (
                    <>
                      <Loader2 size={13} className="animate-spin" />
                      <span>Uploading...</span>
                    </>
                  ) : (
                    <>
                      <Check size={13} className="stroke-[2.5]" />
                      <span>Save</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleCancelForm}
                  className="px-4 py-2.5 rounded-xl bg-[#14141a] hover:bg-[#1a1a22] text-[#888896] hover:text-white text-xs font-medium transition-all"
                >
                  Cancel
                </button>
              </div>
            </motion.form>
          )}

          {/* Edit Document State */}
          {viewMode === 'edit' && selectedDoc && (
            <motion.form
              key="edit-form"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
              onSubmit={handleSaveForm}
              className="max-w-xl w-full mx-auto space-y-5 sm:space-y-6 py-2"
            >
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <h2 className="text-base sm:text-lg font-semibold text-white tracking-tight">
                    Edit Document
                  </h2>
                  <p className="text-xs text-[#6e6e7c]">
                    Update document details and specifications.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setMobilePane('list')}
                  className="md:hidden flex items-center gap-1 text-xs text-[#71717e] hover:text-white p-1.5"
                >
                  <ArrowLeft size={14} />
                  <span>Files</span>
                </button>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[#888896]">
                  File Name
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full bg-[#111115] rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-[#7adfd4]/40 transition-all"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div className="flex items-center justify-between p-3 rounded-xl bg-[#111115]">
                  <div className="flex items-center gap-2.5 truncate">
                    <FileText size={15} className="text-[#7adfd4] shrink-0" />
                    <span className="text-xs font-medium text-white truncate">
                      {formFileName}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => onDownloadFile(formFileName)}
                    className="p-1.5 text-[#666672] hover:text-white rounded-md"
                    title="Download file"
                  >
                    <Download size={13} />
                  </button>
                </div>

                <div className="relative">
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                    className="w-full h-full bg-[#111115] rounded-xl px-3.5 py-2.5 text-xs text-white appearance-none focus:outline-none focus:ring-1 focus:ring-[#7adfd4]/40"
                  >
                    <option value="STANDARD">Standard</option>
                    <option value="RULEBOOK">Rulebook</option>
                    <option value="MANUAL">Manual</option>
                    <option value="SOP">SOP</option>
                    <option value="GUIDELINE">Guideline</option>
                  </select>
                  <ChevronDown size={14} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#555562] pointer-events-none" />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[#888896]">
                  Context Summary
                </label>
                <textarea
                  required
                  rows={4}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  className="w-full bg-[#111115] rounded-xl p-3.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-[#7adfd4]/40 leading-relaxed"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-[#7adfd4] hover:bg-[#6bd0c5] text-black text-xs font-semibold transition-all active:scale-95 shadow-sm shadow-[#7adfd4]/10"
                >
                  <Check size={13} className="stroke-[2.5]" />
                  <span>Save Changes</span>
                </button>

                <button
                  type="button"
                  onClick={handleCancelForm}
                  className="px-4 py-2.5 rounded-xl bg-[#14141a] hover:bg-[#1a1a22] text-[#888896] hover:text-white text-xs font-medium transition-all"
                >
                  Cancel
                </button>
              </div>
            </motion.form>
          )}
        </AnimatePresence>
      </main>

      {/* Delete Confirmation Modal */}
      <DeleteModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirmDelete={confirmDelete}
        onSwitchToEdit={() => {
          setIsDeleteModalOpen(false);
          handleStartEdit();
        }}
        documentTitle={selectedDoc?.name}
      />
    </div>
  );
};
