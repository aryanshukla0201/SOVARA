export type NavigationTab = 'chat' | 'vault' | 'artifacts';
import type { ExecutionTelemetry } from '../api/types';

export interface VaultDocument {
  id: string;
  name: string;
  pages: number;
  uploadedDate: string;
  typeBadge: string; // e.g. "STANDARD", "RULEBOOK", "MANUAL", "SOP", "GUIDELINE"
  fileName: string;
  fileSize?: string;
  comparisonType?: string;
  description: string;
}

export interface ArtifactItem {
  id: string;
  name: string;
  pages: number;
  uploadedDate: string;
  fileType: 'PDF' | 'Docx' | 'PPT' | 'Code' | '.Md' | 'Txt';
  generatedOn: string;
  chatReference: string;
  downloadUrl?: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'sovara';
  text: string;
  timestamp: string;
  taskId?: string;

  meta?: {
    duration: string;
    sourcesCount: number;
    searchesCount: number;
  };

  attachments?: {
    name: string;
    pages: number;
    description: string;
    downloadUrl?: string;
  }[];

  citationQuote?: {
    title: string;
    snippet: string;
  };

  hasSources?: boolean;

  // Backend integration data
  stages?: {
    stage_id: string;
    run_id: string;
    stage_type: string;
    status: string;
    display_label: string;
    sequence: number;
    started_at?: string | null;
    completed_at?: string | null;
    metadata?: Record<string, unknown> | null;
  }[];

  evidence?: Record<string, unknown>[];
  verificationStatus?: string;

  executionTelemetry?: ExecutionTelemetry;

  generatedDeliverables?: string[];
}

export interface ActivityStep {
  id: string;
  title: string;
  status: 'success' | 'error' | 'neutral' | 'in-progress';
  timestamp?: string;
}

export interface CitationItem {
  id: string;
  type: 'source' | 'vault';
  sourceTitle: string;
  content: string;
}

export interface ChatSession {
  id: string;
  title: string;
  isPinned?: boolean;
  isArchived?: boolean;
  createdAt?: number;
  conversationId?: string;
}
