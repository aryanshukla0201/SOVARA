import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import {
  Paperclip,
  ArrowUp,
  ArrowRight,
  FileText,
  Download,
  Copy,
  Check,
  RotateCw,
  ChevronDown,
  BookOpen,
  X,
} from 'lucide-react';

import { ChatMessage } from '../types';
import { AnalysisResponse } from '../api/types';
import { sovaraApi } from '../api/client';
import {
  SovaraHeroWatermark,
  SovaraRibbonLoader,
} from './SovaraLogo';

interface MainChatProps {
  chatId: string;
  chatTitle: string;
  conversationId?: string;
  initialMessages?: ChatMessage[];
  onOpenRightBar: (tab: 'activity' | 'sources' | 'approvals') => void;
  onDownloadFile: (fileName: string) => void;
  sidebarOpen?: boolean;
  onChatTitleUpdate?: (chatId: string, newTitle: string) => void;
  onSaveMessages?: (chatId: string, messages: ChatMessage[]) => void;
  onConversationIdUpdate?: (chatId: string, conversationId: string) => void;
}

const formatDuration = (milliseconds: number): string => {
  if (!Number.isFinite(milliseconds) || milliseconds <= 0) {
    return '—';
  }

  if (milliseconds < 1000) {
    return `${Math.round(milliseconds)}ms`;
  }

  return `${(milliseconds / 1000).toFixed(1)}s`;
};

const getStageDuration = (
  stages: AnalysisResponse['stages'],
): number => {
  if (!Array.isArray(stages) || stages.length === 0) {
    return 0;
  }

  const startTimes = stages
    .map((stage) => stage.started_at)
    .filter((value): value is string => Boolean(value))
    .map((value) => Date.parse(value))
    .filter((value) => Number.isFinite(value));

  const endTimes = stages
    .map((stage) => stage.completed_at)
    .filter((value): value is string => Boolean(value))
    .map((value) => Date.parse(value))
    .filter((value) => Number.isFinite(value));

  if (startTimes.length === 0 || endTimes.length === 0) {
    return 0;
  }

  const start = Math.min(...startTimes);
  const end = Math.max(...endTimes);

  return end > start ? end - start : 0;
};

const getSearchCount = (
  telemetry: AnalysisResponse['execution_telemetry'],
): number => {
  if (!telemetry) {
    return 0;
  }

  /*
   * Prefer explicit search/retrieval-like execution events.
   * If the backend does not emit those events, fall back to network calls.
   */
  const executionEvents = Array.isArray(telemetry.execution_events)
    ? telemetry.execution_events
    : [];

  const searchEvents = executionEvents.filter((event) => {
    const descriptor = `${event.type ?? ''} ${event.tool ?? ''}`.toLowerCase();

    return (
      descriptor.includes('search') ||
      descriptor.includes('retriev') ||
      descriptor.includes('vault') ||
      descriptor.includes('web')
    );
  }).length;

  if (searchEvents > 0) {
    return searchEvents;
  }

  return typeof telemetry.network_calls === 'number'
    ? telemetry.network_calls
    : 0;
};

const getDeliverableName = (path: string): string => {
  const normalized = path.replace(/\\/g, '/');
  return normalized.split('/').pop() || normalized;
};

export const MainChat: React.FC<MainChatProps> = ({
  chatId,
  chatTitle,
  conversationId,
  initialMessages = [],
  onOpenRightBar,
  onDownloadFile,
  sidebarOpen = true,
  onChatTitleUpdate,
  onSaveMessages,
  onConversationIdUpdate,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>(
    () => initialMessages,
  );

  const [inputPrompt, setInputPrompt] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);

  const [workflowStages, setWorkflowStages] = useState<
    Record<string, unknown>[]
  >([]);

  const [displayedText, setDisplayedText] = useState<
    Record<string, string>
  >({});

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const thinkingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const streamingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const submissionLockRef = useRef(false);

  /*
   * React state updates are asynchronous.
   * The ref guarantees that onCompleted receives every workflow event
   * emitted before the backend completion event.
   */
  const workflowStagesRef = useRef<Record<string, unknown>[]>([]);

  useEffect(() => {
    return () => {
      if (thinkingTimeoutRef.current) {
        clearTimeout(thinkingTimeoutRef.current);
      }

      if (streamingIntervalRef.current) {
        clearInterval(streamingIntervalRef.current);
      }
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking, displayedText]);

  const handleFileSelection = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const files = Array.from(event.target.files ?? []);

    if (files.length > 0) {
      setSelectedFiles((previous) => [...previous, ...files]);
    }

    /*
     * Reset the input so selecting the same file again still triggers
     * the change event.
     */
    event.target.value = '';
  };

  const removeSelectedFile = (index: number) => {
    setSelectedFiles((previous) =>
      previous.filter((_, fileIndex) => fileIndex !== index),
    );
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputPrompt).trim();

    if (!query || isThinking || submissionLockRef.current) {
      return;
    }

    submissionLockRef.current = true;

    if (thinkingTimeoutRef.current) {
      clearTimeout(thinkingTimeoutRef.current);
    }

    if (streamingIntervalRef.current) {
      clearInterval(streamingIntervalRef.current);
    }

    const filesForRequest = [...selectedFiles];

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      }),
      attachments:
        filesForRequest.length > 0
          ? filesForRequest.map((file) => ({
              name: file.name,
              pages: 0,
              description: 'Attached to analysis',
            }))
          : undefined,
    };

    const newMessages = [...messages, userMsg];

    setMessages(newMessages);
    onSaveMessages?.(chatId, newMessages);

    setInputPrompt('');
    setSelectedFiles([]);

    setIsThinking(true);

    workflowStagesRef.current = [];
    setWorkflowStages([]);

    const aiMsgId = `msg-${Date.now() + 1}`;

    setStreamingMsgId(aiMsgId);

    setDisplayedText((previous) => ({
      ...previous,
      [aiMsgId]: '',
    }));
    
    let streamFinished = false;

    try {
      await sovaraApi.streamAnalyze(
        {
          userQuery: query,
          conversationId: conversationId,
          files: filesForRequest,
          requestedDeliverable: undefined,
        },
        {
          onWorkflow: (event) => {

            const workflowEvent =
              event as unknown as Record<string, unknown>;

            workflowStagesRef.current = [
              ...workflowStagesRef.current,
              workflowEvent,
            ];

            setWorkflowStages(workflowStagesRef.current);
          },

          onCompleted: (event) => {
            /*
             * The SSE callback is typed generically, while the completed
             * payload follows the full AnalysisResponse contract.
             *
             * Cast once at the API boundary instead of repeatedly
             * accessing unknown properties.
             */

            streamFinished = true;
            const completedEvent =
              event as unknown as AnalysisResponse;

            const backendConversationId =
              typeof completedEvent.conversation_id === 'string'
                ? completedEvent.conversation_id
                : undefined;

            if (backendConversationId && backendConversationId !== conversationId) {
              onConversationIdUpdate?.(chatId, backendConversationId);
            }

            const finalAnswer =
              typeof completedEvent.final_answer === 'string'
                ? completedEvent.final_answer
                : 'SOVARA completed the analysis, but no final answer was returned.';

            const evidence = Array.isArray(
              completedEvent.evidence,
            )
              ? completedEvent.evidence
              : [];

            const telemetry =
              completedEvent.execution_telemetry;

            const verificationStatus =
              typeof completedEvent.verification_status === 'string'
                ? completedEvent.verification_status
                : undefined;

            const stages = Array.isArray(
              completedEvent.stages,
            )
              ? completedEvent.stages
              : [];

            /*
             * Prefer actual workflow duration.
             * Fall back to total LLM duration if stage timestamps
             * are unavailable.
             */
            const stageDuration = getStageDuration(stages);

            const llmDuration =
              typeof telemetry?.llm_total_duration_ms ===
              'number'
                ? telemetry.llm_total_duration_ms
                : 0;

            const duration =
              stageDuration > 0
                ? formatDuration(stageDuration)
                : formatDuration(llmDuration);

            const searchesCount =
              getSearchCount(telemetry);

            const generatedDeliverables =
              Array.isArray(
                completedEvent.generated_deliverables,
              )
                ? completedEvent.generated_deliverables.filter(
                    (item): item is string =>
                      typeof item === 'string',
                  )
                : [];

            const attachments =
              generatedDeliverables.map((path) => {
                const name = getDeliverableName(path);

                return {
                  name,
                  pages: 0,
                  description: 'Generated deliverable',
                  downloadUrl:
                    sovaraApi.getDownloadUrl(
                      completedEvent.request_id,
                      name,
                    ),
                };
              });

            const aiResponse: ChatMessage = {
              id: aiMsgId,
              sender: 'sovara',
              text: finalAnswer,

              timestamp: new Date().toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              }),

              taskId:
                typeof completedEvent.task_id === 'string'
                  ? completedEvent.task_id
                  : undefined,

              meta: {
                duration,
                sourcesCount: evidence.length,
                searchesCount,
              },

              hasSources: evidence.length > 0,

              evidence,

              verificationStatus,

              stages,

              executionTelemetry: telemetry,

              generatedDeliverables,

              attachments,
            };

            const updatedMessages = [
              ...newMessages,
              aiResponse,
            ];

            submissionLockRef.current = false;
            setIsThinking(false);
            setMessages(updatedMessages);

            onSaveMessages?.(
              chatId,
              updatedMessages,
            );

            setStreamingMsgId(null);

            setDisplayedText((previous) => ({
              ...previous,
              [aiMsgId]: finalAnswer,
            }));

            workflowStagesRef.current = [];
            setWorkflowStages([]);
          },

          onError: (event) => {
            streamFinished = true;
            console.error(
              'SOVARA stream error:',
              event,
            );
            
            submissionLockRef.current = false;
            setIsThinking(false);
            setStreamingMsgId(null);

            workflowStagesRef.current = [];
            setWorkflowStages([]);

            setDisplayedText((previous) => ({
              ...previous,
              [aiMsgId]:
                'SOVARA encountered an error while processing this request.',
            }));
          },
        },
      );
      if (!streamFinished) {
        throw new Error('SOVARA stream ended without a completion or error event.');
      }
    } catch (error) {
      console.error(
        'SOVARA analysis failed:',
        error,
      );
      submissionLockRef.current = false;
      setIsThinking(false);
      setStreamingMsgId(null);

      workflowStagesRef.current = [];
      setWorkflowStages([]);

      setDisplayedText((previous) => ({
        ...previous,
        [aiMsgId]:
          'SOVARA could not complete this request. Please try again.',
      }));
    }

    if (
      chatTitle === 'New Chat' &&
      onChatTitleUpdate
    ) {
      const generatedTitle =
        query.length > 28
          ? `${query.slice(0, 28).trim()}...`
          : query;

      onChatTitleUpdate(
        chatId,
        generatedTitle,
      );
    }
  };

  const handleCopy = (
    id: string,
    text: string,
  ) => {
    navigator.clipboard.writeText(text);

    setCopiedId(id);

    setTimeout(
      () => setCopiedId(null),
      2000,
    );
  };

  const handleDownloadAttachment = (
    attachment: {
      name: string;
      downloadUrl?: string;
    },
  ) => {
    if (attachment.downloadUrl) {
      window.open(
        attachment.downloadUrl,
        '_blank',
        'noopener,noreferrer',
      );
      return;
    }

    onDownloadFile(attachment.name);
  };

  const isHeroState = messages.length === 0;

  return (
    <div className="flex-1 flex flex-col h-full min-w-0 bg-[#0a0a0d] relative overflow-hidden select-text">

      {/* Hidden backend-compatible file picker */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx"
        className="hidden"
        onChange={handleFileSelection}
      />

      {/* Messages Scroll Area */}
      <div
        className={`flex-1 overflow-y-auto px-3.5 sm:px-6 md:px-8 lg:px-16 ${
          isHeroState
            ? 'h-full flex flex-col'
            : 'pt-4 sm:pt-6 pb-28 sm:pb-36'
        }`}
      >
        {isHeroState ? (
          /* Initial Hero State */
          <div className="flex-1 flex flex-col justify-between items-center w-full min-h-full">
            <div className="flex-1" />

            <div className="w-full max-w-3xl flex flex-col items-center px-4">
              <motion.div
                initial={{ opacity: 1 }}
                exit={{
                  opacity: 0,
                  y: -24,
                }}
                transition={{
                  duration: 0.25,
                }}
              >
                <SovaraHeroWatermark className="" />
              </motion.div>

              {/* Hero Prompt */}
              <motion.div
                layoutId="mainSearchCapsule"
                transition={{
                  type: 'spring',
                  damping: 28,
                  stiffness: 240,
                  mass: 0.85,
                }}
                className="w-full max-w-2xl bg-[#121217] border border-[#24242e] rounded-2xl p-2.5 sm:p-3 shadow-2xl transition-colors duration-200 teal-border-glow hover:border-[#333342] focus-within:border-[#7adfd4]/50 focus-within:shadow-[0_8px_32px_rgba(122,223,212,0.12)]"
              >
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() =>
                      fileInputRef.current?.click()
                    }
                    className="p-2 text-[#71717a] hover:text-[#d4d4d8] hover:bg-[#1a1a22] rounded-lg transition-colors active:scale-95"
                    title="Attach PDF or DOCX"
                  >
                    <Paperclip size={18} />
                  </button>

                  <input
                    type="text"
                    value={inputPrompt}
                    onChange={(event) =>
                      setInputPrompt(
                        event.target.value,
                      )
                    }
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        handleSendMessage();
                      }
                    }}
                    placeholder="Ask SOVARA to analyze, compare, research, or create..."
                    className="flex-1 bg-transparent text-sm md:text-[15px] text-[#f4f4f5] placeholder-[#6b6b76] focus:outline-none"
                    autoFocus
                  />

                  <button
                    onClick={() =>
                      handleSendMessage()
                    }
                    disabled={
                      !inputPrompt.trim() ||
                      isThinking
                    }
                    className={`p-2 rounded-xl transition-all duration-150 active:scale-95 ${
                      inputPrompt.trim() &&
                      !isThinking
                        ? 'bg-[#7adfd4] hover:bg-[#6bd0c5] text-black shadow-md shadow-[#7adfd4]/20 scale-100'
                        : 'bg-[#1e1e26] text-[#71717a] cursor-not-allowed'
                    }`}
                    title="Send query"
                  >
                    <ArrowUp
                      size={18}
                      className="stroke-[2.5]"
                    />
                  </button>
                </div>

                {/* Selected Files */}
                {selectedFiles.length > 0 && (
                  <div className="flex flex-wrap gap-2 px-1 pt-2">
                    {selectedFiles.map(
                      (file, index) => (
                        <div
                          key={`${file.name}-${index}`}
                          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#1a1a22] border border-[#292934] text-[11px] text-[#c4c4cc]"
                        >
                          <FileText
                            size={12}
                            className="text-[#7adfd4]"
                          />

                          <span className="max-w-[180px] truncate">
                            {file.name}
                          </span>

                          <button
                            type="button"
                            onClick={() =>
                              removeSelectedFile(
                                index,
                              )
                            }
                            className="text-[#71717a] hover:text-white"
                            title="Remove file"
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ),
                    )}
                  </div>
                )}
              </motion.div>
            </div>

            {/* Footer */}
            <motion.div
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex-1 flex items-end justify-center pb-6"
            >
              <div className="text-[12px] text-[#555562] flex items-center justify-center gap-1.5 select-none tracking-wide">
                <span>
                  Private workspace
                </span>

                <span className="text-[#3a3a46]">
                  •
                </span>

                <span>
                  Local execution
                </span>
              </div>
            </motion.div>
          </div>
        ) : (
          /* Active Chat Conversation */
          <div className="max-w-3xl mx-auto space-y-8 pt-4">
            {messages.map(
              (msg, messageIndex) => {
                const isStreamingThis =
                  streamingMsgId === msg.id;

                const activeText =
                  displayedText[msg.id] !==
                  undefined
                    ? displayedText[msg.id]
                    : msg.text;

                const previousUserMessage =
                  messages
                    .slice(0, messageIndex)
                    .reverse()
                    .find(
                      (message) =>
                        message.sender ===
                        'user',
                    );

                return (
                  <motion.div
                    key={msg.id}
                    initial={{
                      opacity: 0,
                      y: 14,
                    }}
                    animate={{
                      opacity: 1,
                      y: 0,
                    }}
                    transition={{
                      duration: 0.28,
                      ease: [
                        0.16,
                        1,
                        0.3,
                        1,
                      ],
                    }}
                    className="space-y-4"
                  >
                    {msg.sender === 'user' ? (
                      /* User Message */
                      <div className="flex justify-end">
                        <motion.div
                          initial={{
                            scale: 0.98,
                          }}
                          animate={{
                            scale: 1,
                          }}
                          className="max-w-[85%] bg-[#1a1a21] border border-[#282833] rounded-2xl px-5 py-3 text-sm text-[#e4e4e7] leading-relaxed break-words break-all shadow-sm"
                        >
                          <div>
                            {msg.text}
                          </div>

                          {msg.attachments &&
                            msg.attachments.length >
                              0 && (
                              <div className="mt-3 space-y-1.5">
                                {msg.attachments.map(
                                  (
                                    attachment,
                                    index,
                                  ) => (
                                    <div
                                      key={index}
                                      className="flex items-center gap-2 text-[11px] text-[#8f8f99]"
                                    >
                                      <FileText
                                        size={12}
                                        className="text-[#7adfd4]"
                                      />

                                      <span className="truncate">
                                        {
                                          attachment.name
                                        }
                                      </span>
                                    </div>
                                  ),
                                )}
                              </div>
                            )}
                        </motion.div>
                      </div>
                    ) : (
                      /* SOVARA AI Response */
                      <div className="space-y-5 text-[#e4e4e7]">

                        {/* Research Summary */}
                        {msg.meta && (
                          <motion.button
                            initial={{
                              opacity: 0,
                              scale: 0.96,
                            }}
                            animate={{
                              opacity: 1,
                              scale: 1,
                            }}
                            whileHover={{
                              scale: 1.015,
                              borderColor:
                                '#7adfd4',
                            }}
                            whileTap={{
                              scale: 0.98,
                            }}
                            onClick={() =>
                              onOpenRightBar(
                                'activity',
                              )
                            }
                            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#141419] border border-[#24242f] text-xs text-[#a1a1aa] hover:text-white transition-all group shadow-xs"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-[#7adfd4] animate-pulse" />

                            <span>
                              {msg.meta.duration}
                              {' • '}
                              {
                                msg.meta
                                  .sourcesCount
                              }
                              {' sources • '}
                              {
                                msg.meta
                                  .searchesCount
                              }
                              {' searches'}
                            </span>

                            <ArrowRight
                              size={13}
                              className="text-[#7adfd4] group-hover:translate-x-0.5 transition-transform"
                            />
                          </motion.button>
                        )}

                        {/* Response Text */}
                        <div className="text-[14px] md:text-[15px] leading-relaxed space-y-3 text-[#d4d4dc]">
                          {activeText
                            .split('\n\n')
                            .map(
                              (para, index) => {
                                if (
                                  para.startsWith(
                                    '•',
                                  )
                                ) {
                                  return (
                                    <ul
                                      key={index}
                                      className="space-y-2 my-2"
                                    >
                                      {para
                                        .split(
                                          '\n',
                                        )
                                        .map(
                                          (
                                            line,
                                            lineIndex,
                                          ) => {
                                            const cleanLine =
                                              line.replace(
                                                /^•\s*/,
                                                '',
                                              );

                                            return (
                                              <motion.li
                                                key={
                                                  lineIndex
                                                }
                                                initial={{
                                                  opacity: 0,
                                                  x: -6,
                                                }}
                                                animate={{
                                                  opacity: 1,
                                                  x: 0,
                                                }}
                                                transition={{
                                                  duration:
                                                    0.2,
                                                }}
                                                className="flex items-start gap-2.5 text-[#d4d4dc]"
                                              >
                                                <span className="text-[#7adfd4] mt-1.5 text-xs">
                                                  •
                                                </span>

                                                <span>
                                                  {
                                                    cleanLine
                                                  }
                                                </span>
                                              </motion.li>
                                            );
                                          },
                                        )}
                                    </ul>
                                  );
                                }

                                return (
                                  <motion.p
                                    key={index}
                                    initial={{
                                      opacity: 0,
                                      y: 3,
                                    }}
                                    animate={{
                                      opacity: 1,
                                      y: 0,
                                    }}
                                    transition={{
                                      duration: 0.2,
                                    }}
                                  >
                                    {para}
                                  </motion.p>
                                );
                              },
                            )}

                          {/* Streaming Cursor */}
                          {isStreamingThis && (
                            <span className="inline-block w-2 h-4 bg-[#7adfd4] ml-1 rounded-[1px] animate-pulse align-middle shadow-[0_0_8px_rgba(122,223,212,0.8)]" />
                          )}
                        </div>

                        {/* Structured Output */}
                        {!isStreamingThis && (
                          <motion.div
                            initial={{
                              opacity: 0,
                              y: 10,
                            }}
                            animate={{
                              opacity: 1,
                              y: 0,
                            }}
                            transition={{
                              duration: 0.35,
                              ease: [
                                0.16,
                                1,
                                0.3,
                                1,
                              ],
                            }}
                            className="space-y-4"
                          >
                            {/* Generated Deliverables */}
                            {msg.attachments &&
                              msg.attachments
                                .length >
                                0 && (
                                <div className="space-y-2">
                                  {msg.attachments.map(
                                    (
                                      attachment,
                                      index,
                                    ) => (
                                      <motion.div
                                        key={index}
                                        whileHover={{
                                          y: -1.5,
                                          borderColor:
                                            '#343444',
                                        }}
                                        transition={{
                                          duration:
                                            0.15,
                                        }}
                                        className="flex flex-col sm:flex-row sm:items-center justify-between p-3 sm:p-3.5 rounded-xl bg-[#121217] border border-[#22222b] transition-colors gap-2.5 sm:gap-0 shadow-xs"
                                      >
                                        <div className="flex items-center gap-3 min-w-0">
                                          <div className="p-2 rounded-lg bg-[#181820] text-[#7adfd4] shrink-0">
                                            <FileText
                                              size={
                                                18
                                              }
                                            />
                                          </div>

                                          <div className="min-w-0">
                                            <div className="text-xs sm:text-sm font-medium text-white truncate">
                                              {
                                                attachment.name
                                              }
                                            </div>

                                            <div className="text-[11px] text-[#71717a]">
                                              {attachment.pages >
                                              0
                                                ? `${attachment.pages} pages • `
                                                : ''}
                                              {
                                                attachment.description
                                              }
                                            </div>
                                          </div>
                                        </div>

                                        <motion.button
                                          whileHover={{
                                            scale: 1.02,
                                          }}
                                          whileTap={{
                                            scale: 0.97,
                                          }}
                                          onClick={() =>
                                            handleDownloadAttachment(
                                              attachment,
                                            )
                                          }
                                          className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1a1a22] hover:bg-[#242430] text-xs font-medium text-[#e4e4e7] border border-[#2c2c38] transition-all shrink-0 self-end sm:self-auto"
                                        >
                                          <Download
                                            size={
                                              13
                                            }
                                          />

                                          <span>
                                            Download
                                          </span>
                                        </motion.button>
                                      </motion.div>
                                    ),
                                  )}
                                </div>
                              )}

                            {/* Citation Quote */}
                            {msg.citationQuote && (
                              <motion.div
                                whileHover={{
                                  borderColor:
                                    '#2e2e3c',
                                }}
                                className="p-4 rounded-xl bg-[#111116] border border-[#1f1f28] space-y-2 transition-colors"
                              >
                                <div className="text-xs font-semibold text-white tracking-wide">
                                  {
                                    msg
                                      .citationQuote
                                      .title
                                  }
                                </div>

                                <p className="text-xs leading-relaxed text-[#9494a0]">
                                  {
                                    msg
                                      .citationQuote
                                      .snippet
                                  }
                                </p>
                              </motion.div>
                            )}

                            {/* Sources */}
                            {msg.hasSources && (
                              <div>
                                <motion.button
                                  whileHover={{
                                    scale: 1.025,
                                    borderColor:
                                      '#7adfd4',
                                  }}
                                  whileTap={{
                                    scale: 0.98,
                                  }}
                                  onClick={() =>
                                    onOpenRightBar(
                                      'sources',
                                    )
                                  }
                                  className="px-3.5 py-1.5 rounded-lg bg-[#15151c] hover:bg-[#1d1d26] border border-[#272733] text-xs font-medium text-[#d4d4d8] transition-all flex items-center gap-1.5"
                                >
                                  <BookOpen
                                    size={12}
                                    className="text-[#7adfd4]"
                                  />

                                  <span>
                                    Sources
                                  </span>
                                </motion.button>
                              </div>
                            )}

                            {/* Bottom Actions */}
                            <div className="flex items-center gap-2 pt-2 text-[#71717a]">
                              <motion.button
                                whileHover={{
                                  scale: 1.1,
                                  color: '#ffffff',
                                }}
                                whileTap={{
                                  scale: 0.92,
                                }}
                                onClick={() =>
                                  handleCopy(
                                    msg.id,
                                    activeText,
                                  )
                                }
                                className="p-1.5 rounded-lg hover:bg-[#181820] transition-colors"
                                title={
                                  copiedId ===
                                  msg.id
                                    ? 'Copied!'
                                    : 'Copy to clipboard'
                                }
                              >
                                {copiedId ===
                                msg.id ? (
                                  <Check className="text-[#34d399]" size={14} />
                                ) : (
                                  <Copy size={14} />
                                )}
                              </motion.button>

                              <motion.button
                                whileHover={{
                                  scale: 1.1,
                                  color: '#ffffff',
                                }}
                                whileTap={{
                                  scale: 0.92,
                                }}
                                onClick={() =>
                                  handleSendMessage(
                                    previousUserMessage?.text ||
                                      msg.text,
                                  )
                                }
                                className="p-1.5 rounded-lg hover:bg-[#181820] transition-colors"
                                title="Regenerate response"
                              >
                                <RotateCw
                                  size={14}
                                />
                              </motion.button>

                              <motion.button
                                whileHover={{
                                  scale: 1.1,
                                  color: '#ffffff',
                                }}
                                whileTap={{
                                  scale: 0.92,
                                }}
                                className="p-1.5 rounded-lg hover:bg-[#181820] transition-colors"
                                title="More options"
                              >
                                <ChevronDown
                                  size={14}
                                />
                              </motion.button>
                            </div>
                          </motion.div>
                        )}
                      </div>
                    )}
                  </motion.div>
                );
              },
            )}

            {/* Thinking Indicator */}
            {isThinking && (
              <motion.div
                initial={{
                  opacity: 0,
                  y: 8,
                }}
                animate={{
                  opacity: 1,
                  y: 0,
                }}
                className="flex items-center gap-3 text-xs text-[#7adfd4] pt-2"
              >
                <SovaraRibbonLoader
                  size={26}
                />

                <span className="animate-pulse tracking-wide font-medium">
                  {workflowStages.length >
                  0
                    ? 'SOVARA is processing your request...'
                    : 'SOVARA is analyzing and verifying context...'}
                </span>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Floating Bottom Input Bar */}
      {!isHeroState && (
        <motion.div
          initial={{
            opacity: 0,
          }}
          animate={{
            opacity: 1,
          }}
          transition={{
            duration: 0.3,
          }}
          className="absolute bottom-0 left-0 right-0 p-3 sm:p-4 md:p-6 bg-gradient-to-t from-[#0a0a0d] via-[#0a0a0d]/95 to-transparent pointer-events-none"
        >
          <div className="max-w-3xl mx-auto pointer-events-auto">
            <motion.div
              layoutId="mainSearchCapsule"
              transition={{
                type: 'spring',
                damping: 28,
                stiffness: 240,
                mass: 0.85,
              }}
              className="bg-[#121217] border border-[#24242e] rounded-2xl p-1.5 sm:p-2.5 shadow-2xl transition-all teal-border-glow"
            >
              <div className="flex items-center gap-2 sm:gap-3">
                <button
                  type="button"
                  onClick={() =>
                    fileInputRef.current?.click()
                  }
                  className="p-1.5 sm:p-2 text-[#71717a] hover:text-[#d4d4d8] hover:bg-[#1a1a22] rounded-lg transition-colors shrink-0"
                  title="Attach PDF or DOCX"
                >
                  <Paperclip size={18} />
                </button>

                <input
                  type="text"
                  value={inputPrompt}
                  onChange={(event) =>
                    setInputPrompt(
                      event.target.value,
                    )
                  }
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      handleSendMessage();
                    }
                  }}
                  placeholder="Ask anything, / for commands, @ for context..."
                  className="flex-1 bg-transparent text-xs sm:text-sm text-[#f4f4f5] placeholder-[#6b6b76] focus:outline-none min-w-0"
                />

                <button
                  onClick={() =>
                    handleSendMessage()
                  }
                  disabled={
                    !inputPrompt.trim() ||
                    isThinking
                  }
                  className={`p-1.5 sm:p-2 rounded-xl transition-all shrink-0 ${
                    inputPrompt.trim() &&
                    !isThinking
                      ? 'bg-[#7adfd4] hover:bg-[#6bd0c5] text-black shadow-md shadow-[#7adfd4]/20 scale-100'
                      : 'bg-[#1e1e26] text-[#71717a] cursor-not-allowed'
                  }`}
                  title="Send message"
                >
                  <ArrowUp
                    size={18}
                    className="stroke-[2.5]"
                  />
                </button>
              </div>

              {/* Selected Files */}
              {selectedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 px-1 pt-2">
                  {selectedFiles.map(
                    (file, index) => (
                      <div
                        key={`${file.name}-${index}`}
                        className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#1a1a22] border border-[#292934] text-[11px] text-[#c4c4cc]"
                      >
                        <FileText
                          size={12}
                          className="text-[#7adfd4]"
                        />

                        <span className="max-w-[180px] truncate">
                          {file.name}
                        </span>

                        <button
                          type="button"
                          onClick={() =>
                            removeSelectedFile(
                              index,
                            )
                          }
                          className="text-[#71717a] hover:text-white"
                          title="Remove file"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ),
                  )}
                </div>
              )}
            </motion.div>

            {/* Footer */}
            <div className="text-[10px] sm:text-[11px] text-[#555560] mt-1.5 sm:mt-2 text-center flex items-center justify-center gap-1 select-none">
              <span>
                Private workspace • Local execution
              </span>

              <span className="text-[#7adfd4]/80">
                ›
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

