import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  X, 
  Check, 
  Clock, 
  BookOpen, 
  AlertCircle,
  ExternalLink,
  Layers,
  Sparkles,
  FileText
} from 'lucide-react';
import { ChatMessage } from '../types';
import { sovaraApi } from '../api/client';
import type { ApprovalResponse } from '../api/types';

interface RightBarProps {
  isOpen: boolean;
  onClose: () => void;
  defaultTab?: 'activity' | 'sources' | 'approvals';
  isMobile?: boolean;
  latestMessage?: ChatMessage;
}

export const RightBar: React.FC<RightBarProps> = ({
  isOpen,
  onClose,
  defaultTab = 'activity',
  latestMessage,
}) => {
  const [activeTab, setActiveTab] = useState<'activity' | 'sources' | 'approvals'>(defaultTab);
  const [approvals, setApprovals] = useState<ApprovalResponse[]>([]);
  const [approvalsLoading, setApprovalsLoading] = useState(false);

  const [approvalActionId, setApprovalActionId] = useState<string | null>(null);

  const refreshApprovals = async () => {
    if (!latestMessage?.taskId) return;

    try {
      const data = await sovaraApi.getTaskApprovals(latestMessage.taskId);
      setApprovals(Array.isArray(data) ? data : []);
    } catch {
      // Keep the current UI state if refresh fails.
    }
  };

  const handleApprove = async (approvalId: string) => {
    setApprovalActionId(approvalId);

    try {
      await sovaraApi.approve(approvalId);
      await refreshApprovals();
    } catch {
      // Keep the existing approval visible if the action fails.
    } finally {
      setApprovalActionId(null);
    }
  };

  const handleReject = async (approvalId: string) => {
    setApprovalActionId(approvalId);

    try {
      await sovaraApi.reject(approvalId);
      await refreshApprovals();
    } catch {
      // Keep the existing approval visible if the action fails.
    } finally {
      setApprovalActionId(null);
    }
  };

  // Sync tab state when opening specifically for sources or activity
  useEffect(() => {
    if (defaultTab) {
      setActiveTab(defaultTab);
    }
  }, [defaultTab, isOpen]);

  useEffect(() => {
    if (activeTab !== 'approvals' || !latestMessage) return;

    const taskId = latestMessage.taskId;
    if (!taskId) return;

    let cancelled = false;

    const loadApprovals = async () => {
      setApprovalsLoading(true);

      try {
        const data = await sovaraApi.getTaskApprovals(taskId);

        if (!cancelled) {
          setApprovals(Array.isArray(data) ? data : []);
        }
      } catch {
        if (!cancelled) {
          setApprovals([]);
        }
      } finally {
        if (!cancelled) {
          setApprovalsLoading(false);
        }
      }
    };

    void loadApprovals();

    return () => {
      cancelled = true;
    };
  }, [activeTab, latestMessage]);

  // Handle ESC key to dismiss drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end overflow-hidden select-none">
          {/* Dimmed backdrop to close on outside click */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-[2px]"
            aria-label="Close drawer backdrop"
          />

          {/* Sliding Panel strictly anchored to the right edge within viewport boundaries */}
          <motion.aside
            initial={{ x: '100%', opacity: 0.8 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0.8 }}
            transition={{
              type: 'spring',
              damping: 28,
              stiffness: 280,
              mass: 0.85,
            }}
            className="relative z-10 h-full w-full max-w-[360px] sm:max-w-[400px] bg-[#0d0d12] border-l border-[#1f1f28] shadow-[-16px_0_48px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden text-[#e4e4e7]"
          >
            {/* Top Header & Tab Switcher */}
            <div className="px-4 py-3 border-b border-[#1b1b24] flex items-center justify-between shrink-0 bg-[#0e0e14]">
              {/* Segmented Capsule Tabs */}
              <div className="flex items-center bg-[#171720] p-1 rounded-full border border-[#252530]">
                <button
                  onClick={() => setActiveTab('activity')}
                  className={`px-3.5 py-1 text-xs font-medium rounded-full transition-all ${
                    activeTab === 'activity'
                      ? 'bg-[#262633] text-white shadow-xs'
                      : 'text-[#8b8b98] hover:text-white'
                  }`}
                >
                  Activity
                </button>

                <button
                  onClick={() => setActiveTab('sources')}
                  className={`px-3.5 py-1 text-xs font-medium rounded-full transition-all ${
                    activeTab === 'sources'
                      ? 'bg-[#262633] text-white shadow-xs'
                      : 'text-[#8b8b98] hover:text-white'
                  }`}
                >
                  Sources
                </button>

                <button
                  onClick={() => setActiveTab('approvals')}
                  className={`px-3.5 py-1 text-xs font-medium rounded-full transition-all ${
                    activeTab === 'approvals'
                      ? 'bg-[#262633] text-white shadow-xs'
                      : 'text-[#8b8b98] hover:text-white'
                  }`}
                >
                  Approvals
                </button>
              </div>

              {/* Close Button */}
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-[#858593] hover:text-white hover:bg-[#1a1a24] transition-colors active:scale-95"
                title="Close drawer (Esc)"
                aria-label="Close drawer"
              >
                <X size={17} />
              </button>
            </div>

            {/* Scrollable Body Content */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 text-xs font-normal scrollbar-none">
              {activeTab === 'activity' ? (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-[#636372] mb-3">
                      Execution Timeline
                    </h3>

                    {/* Timeline Steps */}
                    <div className="space-y-2.5">
                      {(latestMessage?.stages ?? []).length > 0 ? (
                        latestMessage!.stages!
                          .filter(
                            (stage, index, stages) =>
                              index === 0 ||
                              stage.stage_type !== stages[index - 1].stage_type,
                          )
                          .map((stage) => {
                          const isSuccess = stage.status === 'completed';
                          const isError =
                            stage.status === 'failed' || stage.status === 'cancelled';
                          const isRunning =
                            stage.status === 'running' || stage.status === 'pending';

                          return (
                            <div
                              key={stage.stage_id}
                              className="flex items-start gap-2.5 p-2 rounded-lg hover:bg-[#13131a] transition-colors text-[#d4d4d8]"
                            >
                              {isSuccess && (
                                <Check
                                  size={14}
                                  className="text-[#34d399] mt-0.5 shrink-0 stroke-[2.5]"
                                />
                              )}

                              {isError && (
                                <X
                                  size={14}
                                  className="text-[#f87171] mt-0.5 shrink-0 stroke-[2.5]"
                                />
                              )}

                              {isRunning && (
                                <Clock
                                  size={13}
                                  className="text-[#7adfd4] mt-0.5 shrink-0"
                                />
                              )}

                              <span
                                className={`text-[12px] leading-tight ${
                                  isError
                                    ? 'text-[#fca5a5]'
                                    : isSuccess
                                    ? 'text-[#e4e4e7]'
                                    : 'text-[#a1a1ad]'
                                }`}
                              >
                                {stage.display_label}
                              </span>
                            </div>
                          );
                        })
                      ) : (
                        <div className="p-3 rounded-xl bg-[#121218] border border-[#1d1d28] text-[#71717a] text-[12px]">
                          No execution activity yet.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Execution Context */}
                  <div className="pt-3 border-t border-[#1c1c26]">
                    <div className="text-[11px] font-medium uppercase tracking-wider text-[#636372] mb-2 flex items-center gap-1.5">
                      <Sparkles size={12} className="text-[#7adfd4]" />
                      <span>Execution Context</span>
                    </div>

                    <div className="p-3 rounded-xl bg-[#121218] border border-[#1d1d28] text-[#a5a5b2] text-[12px] leading-relaxed space-y-2">
                      {latestMessage ? (
                        <>
                          <div>
                            <span className="text-[#71717a]">Processing: </span>
                            <span className="text-[#d4d4d8]">
                              {latestMessage.executionTelemetry?.processing_location ??
                                'Local'}
                            </span>
                          </div>

                          <div>
                            <span className="text-[#71717a]">Models: </span>
                            <span className="text-[#d4d4d8]">
                              {latestMessage.executionTelemetry?.models_used?.join(', ') ||
                                'Not reported'}
                            </span>
                          </div>

                          <div>
                            <span className="text-[#71717a]">LLM calls: </span>
                            <span className="text-[#d4d4d8]">
                              {latestMessage.executionTelemetry?.llm_calls ?? 0}
                            </span>
                          </div>
                        </>
                      ) : (
                        <span>No execution context available yet.</span>
                      )}
                    </div>
                  </div>
                </div>
              ) : activeTab === 'sources' ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-[#636372]">
                      Grounded Sources ({latestMessage?.evidence?.length ?? 0})
                    </h3>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        latestMessage?.verificationStatus === 'passed'
                          ? 'text-[#7adfd4] bg-[#122220] border border-[#7adfd4]/20'
                          : latestMessage?.verificationStatus === 'failed'
                            ? 'text-[#f87171] bg-[#2a1414] border border-[#f87171]/20'
                            : 'text-[#a1a1aa] bg-[#18181f] border border-[#3f3f46]/40'
                      }`}
                    >
                      {latestMessage?.verificationStatus === 'passed'
                        ? 'Verified'
                        : latestMessage?.verificationStatus === 'failed'
                          ? 'Verification Failed'
                          : 'Not Verified'}
                    </span>
                  </div>

                  <div className="space-y-3">
                    {(latestMessage?.evidence ?? []).length > 0 ? (
                      latestMessage!.evidence!.map((item, index) => {
                        const sourceTitle =
                          String(
                            item.source_filename ??
                              item.source_title ??
                              item.title ??
                              item.source ??
                              `Evidence ${index + 1}`,
                          );

                        const evidenceType = String(
                          item.evidence_type ?? item.type ?? 'source',
                        );

                        const content =
                          String(
                            item.snippet ??
                              item.content ??
                              item.text ??
                              item.quote ??
                              '',
                          ).trim() || 'Evidence retrieved by SOVARA.';

                        const isVault =
                          evidenceType.toLowerCase().includes('vault') ||
                          Boolean(item.source_file_id);

                        return (
                          <div
                            key={String(item.evidence_id ?? item.id ?? `evidence-${index}`)}
                            className="p-3.5 rounded-xl bg-[#121217] border border-[#1e1e28] hover:border-[#2a2a36] transition-all space-y-2 group"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2 text-[#9a9aa6] min-w-0">
                                {isVault ? (
                                  <BookOpen
                                    size={13}
                                    className="text-[#7adfd4] shrink-0"
                                  />
                                ) : (
                                  <div className="w-2 h-2 rounded-full bg-[#7adfd4] shrink-0" />
                                )}

                                <span className="text-[11.5px] font-medium tracking-wide text-white/90 truncate">
                                  {sourceTitle}
                                </span>
                              </div>

                              <span className="text-[10px] font-mono uppercase text-[#5a5a66] shrink-0">
                                {isVault ? 'Vault' : 'Source'}
                              </span>
                            </div>

                            <p className="text-[11px] leading-relaxed text-[#858592] line-clamp-4">
                              {content}
                            </p>

                            {(item.page_number != null ||
                              item.chunk_id != null ||
                              item.evidence_id != null) && (
                              <div className="flex items-center gap-2 text-[9px] font-mono text-[#555560]">
                                {item.page_number != null && (
                                  <span>Page {String(item.page_number)}</span>
                                )}

                                {item.chunk_id != null && (
                                  <span>Chunk {String(item.chunk_id)}</span>
                                )}

                                {item.evidence_id != null && (
                                  <span className="truncate">
                                    {String(item.evidence_id)}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })
                    ) : (
                      <div className="p-3 rounded-xl bg-[#121218] border border-[#1d1d28] text-[#71717a] text-[12px]">
                        No grounded evidence for this response.
                      </div>
                    )}
                  </div>

                  {/* Knowledge Vault Integration Tip */}
                  <div className="p-3 rounded-xl bg-[#11161d] border border-[#1d2a38] text-[11.5px] text-[#93c5fd] leading-relaxed flex items-start gap-2.5">
                    <Layers size={15} className="text-[#60a5fa] shrink-0 mt-0.5" />
                    <span>
                      Documents indexed in your <strong>Knowledge Vault</strong> are automatically extracted and cited in chat responses.
                    </span>
                  </div>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto p-4">
                  {approvalsLoading ? (
                    <div className="flex items-center justify-center py-12 text-xs text-[#717180]">
                      Loading approvals...
                    </div>
                  ) : approvals.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <Check size={22} className="text-[#565664] mb-3" />

                      <p className="text-sm text-[#a1a1ad]">
                        No approvals required
                      </p>

                      <p className="text-xs text-[#62626f] mt-1">
                        This task has no pending approval requests.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {approvals.map((approval) => (
                        <div
                          key={approval.approval_id}
                          className="rounded-xl border border-[#252530] bg-[#121218] p-4"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm font-medium text-white">
                              {approval.tool_name}
                            </span>

                            <span className="rounded-full bg-[#2a2418] px-2 py-1 text-[10px] font-medium uppercase text-[#d6b46a]">
                              {approval.status}
                            </span>
                          </div>

                          <p className="mt-3 text-xs leading-relaxed text-[#a1a1ad]">
                            {approval.reason}
                          </p>

                          <div className="mt-3 space-y-1.5 text-[11px] text-[#717180]">
                            <div>
                              <span className="text-[#8b8b98]">Risk:</span>{' '}
                              {approval.risk_level}
                            </div>

                            <div>
                              <span className="text-[#8b8b98]">Action:</span>{' '}
                              {approval.requested_action}
                            </div>

                            <div>
                              <span className="text-[#8b8b98]">Arguments:</span>{' '}
                              {approval.requested_arguments_summary}
                            </div>
                          </div>

                          {approval.status === 'pending' && (
                            <div className="flex items-center gap-2 pt-2">
                              <button
                                type="button"
                                disabled={approvalActionId === approval.approval_id}
                                onClick={() => void handleApprove(approval.approval_id)}
                                className="flex-1 rounded-lg border border-[#7adfd4]/20 bg-[#122220] px-3 py-2 text-[11px] font-medium text-[#7adfd4] transition-colors hover:bg-[#16302d] disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {approvalActionId === approval.approval_id
                                  ? 'Processing...'
                                  : 'Approve'}
                              </button>

                              <button
                                type="button"
                                disabled={approvalActionId === approval.approval_id}
                                onClick={() => void handleReject(approval.approval_id)}
                                className="flex-1 rounded-lg border border-[#f87171]/20 bg-[#2a1414] px-3 py-2 text-[11px] font-medium text-[#f87171] transition-colors hover:bg-[#351818] disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {approvalActionId === approval.approval_id
                                  ? 'Processing...'
                                  : 'Reject'}
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.aside>
        </div>
      )}
    </AnimatePresence>
  );
};
