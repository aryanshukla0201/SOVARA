import type {
  AnalysisResponse,
  AnalysisStreamEvent,
  ApprovalResponse,
  ReportResponse,
  TaskResponse,
  VaultDocumentResponse,
  VaultSearchResponse,
} from './types';

const API_BASE_URL =
  (import.meta.env.VITE_SOVARA_API_URL as string | undefined)?.replace(/\/$/, '') ||
  'http://localhost:8000';

export interface AnalyzeRequest {
  userQuery: string;
  conversationId?: string;
  taskId?: string;
  requestedDeliverable?: string;
  files?: File[];
}

export interface StreamCallbacks {
  onWorkflow?: (event: AnalysisStreamEvent) => void;
  onCompleted?: (event: AnalysisStreamEvent) => void;
  onError?: (event: AnalysisStreamEvent) => void;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new Error(
      body || `SOVARA API request failed (${response.status} ${response.statusText})`,
    );
  }

  return response.json() as Promise<T>;
}

function buildFormData(request: AnalyzeRequest): FormData {
  const form = new FormData();

  form.append('user_query', request.userQuery);

  if (request.conversationId) {
    form.append('conversation_id', request.conversationId);
  }

  if (request.taskId) {
    form.append('task_id', request.taskId);
  }

  if (request.requestedDeliverable) {
    form.append('requested_deliverable', request.requestedDeliverable);
  }

  for (const file of request.files ?? []) {
    form.append('files', file);
  }

  return form;
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  return parseResponse<T>(response);
}

export const sovaraApi = {
  baseUrl: API_BASE_URL,

  async analyze(analyzeRequest: AnalyzeRequest): Promise<AnalysisResponse> {
    return request<AnalysisResponse>('/analyze', {
      method: 'POST',
      body: buildFormData(analyzeRequest),
    });
  },

  async streamAnalyze(
    analyzeRequest: AnalyzeRequest,
    callbacks: StreamCallbacks = {},
    signal?: AbortSignal,
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/analyze/stream`, {
      method: 'POST',
      body: buildFormData(analyzeRequest),
      headers: {
        Accept: 'text/event-stream',
      },
      signal,
    });

    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(
        body ||
          `SOVARA stream failed (${response.status} ${response.statusText})`,
      );
    }

    if (!response.body) {
      throw new Error('SOVARA stream returned no response body.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const dispatch = (block: string) => {
      const lines = block.split(/\r?\n/);
      let eventType = 'message';
      const dataLines: string[] = [];

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trimStart());
        }
      }

      if (!dataLines.length) {
        return;
      }

      const rawData = dataLines.join('\n');

      let payload: AnalysisStreamEvent;

      try {
        payload = JSON.parse(rawData) as AnalysisStreamEvent;
      } catch {
        payload = {
          type: eventType,
          data: rawData,
        };
      }

      const normalized = {
        ...payload,
        type:
          typeof payload.type === 'string' && payload.type.length > 0
            ? payload.type
            : eventType,
      };

      if (normalized.type === 'workflow') {
        callbacks.onWorkflow?.(normalized);
      } else if (normalized.type === 'completed') {
        callbacks.onCompleted?.(normalized);
      } else if (normalized.type === 'error') {
        callbacks.onError?.(normalized);
      }
    };

    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? '';

      for (const block of blocks) {
        dispatch(block);
      }
    }

    buffer += decoder.decode();

    if (buffer.trim()) {
      dispatch(buffer);
    }
  },

  async getAnalysis(requestId: string): Promise<AnalysisResponse> {
    return request<AnalysisResponse>(
      `/analysis/${encodeURIComponent(requestId)}`,
    );
  },

  async getTask(taskId: string): Promise<TaskResponse> {
    return request<TaskResponse>(
      `/tasks/${encodeURIComponent(taskId)}`,
    );
  },

  async listVaultDocuments(): Promise<VaultDocumentResponse[]> {
    const response = await request<
      VaultDocumentResponse[] | { documents?: VaultDocumentResponse[] }
    >('/vault/documents');

    return Array.isArray(response) ? response : response.documents ?? [];
  },

  async uploadVaultDocument(file: File): Promise<VaultDocumentResponse> {
    const form = new FormData();
    form.append('file', file);

    const response = await fetch(`${API_BASE_URL}/vault/upload`, {
      method: 'POST',
      body: form,
      headers: {
        Accept: 'application/json',
      },
    });

    return parseResponse<VaultDocumentResponse>(response);
  },

  async deleteVaultDocument(documentId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/vault/documents/${encodeURIComponent(documentId)}`,
      {
        method: 'DELETE',
        headers: {
          Accept: 'application/json',
        },
      },
    );

    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(
        body ||
          `Failed to delete vault document (${response.status} ${response.statusText})`,
      );
    }
  },

  async reindexVaultDocument(documentId: string): Promise<VaultDocumentResponse> {
    return request<VaultDocumentResponse>(
      `/vault/documents/${encodeURIComponent(documentId)}/reindex`,
      {
        method: 'POST',
      },
    );
  },

  async searchVault(
    query: string,
    topK = 10,
  ): Promise<VaultSearchResponse> {
    return request<VaultSearchResponse>(
      `/vault/search?query=${encodeURIComponent(query)}&top_k=${encodeURIComponent(topK)}`,
    );
  },

  async getApproval(approvalId: string): Promise<ApprovalResponse> {
    return request<ApprovalResponse>(
      `/approvals/${encodeURIComponent(approvalId)}`,
    );
  },

  async getTaskApprovals(taskId: string): Promise<ApprovalResponse[]> {
    const response = await request<
      ApprovalResponse[] | { approvals?: ApprovalResponse[] }
    >(`/tasks/${encodeURIComponent(taskId)}/approvals`);

    return Array.isArray(response) ? response : response.approvals ?? [];
  },

  async approve(approvalId: string): Promise<ApprovalResponse> {
    return request<ApprovalResponse>(
      `/approvals/${encodeURIComponent(approvalId)}/approve`,
      {
        method: 'POST',
      },
    );
  },

  async reject(approvalId: string): Promise<ApprovalResponse> {
    return request<ApprovalResponse>(
      `/approvals/${encodeURIComponent(approvalId)}/reject`,
      {
        method: 'POST',
      },
    );
  },

  async cancelApproval(approvalId: string): Promise<ApprovalResponse> {
    return request<ApprovalResponse>(
      `/approvals/${encodeURIComponent(approvalId)}/cancel`,
      {
        method: 'POST',
      },
    );
  },

  async getReport(reportId: string): Promise<ReportResponse> {
    return request<ReportResponse>(
      `/reports/${encodeURIComponent(reportId)}`,
    );
  },

  async getTaskReports(taskId: string): Promise<ReportResponse[]> {
    const response = await request<
      ReportResponse[] | { reports?: ReportResponse[] }
    >(`/tasks/${encodeURIComponent(taskId)}/reports`);

    return Array.isArray(response) ? response : response.reports ?? [];
  },

  async createTaskReport(
    taskId: string,
    payload: Record<string, unknown> = {},
  ): Promise<ReportResponse> {
    return request<ReportResponse>(
      `/tasks/${encodeURIComponent(taskId)}/reports`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      },
    );
  },

  getDownloadUrl(requestId: string, fileName: string): string {
    return `${API_BASE_URL}/download/${encodeURIComponent(requestId)}/${encodeURIComponent(fileName)}`;
  },
};

