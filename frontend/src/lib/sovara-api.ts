const API_BASE = "/sovara-api";

export async function analyze(
  userQuery: string,
  conversationId?: string,
  files: File[] = [],
  requestedDeliverable?: string,
) {
  const formData = new FormData();

  formData.append("user_query", userQuery);

  if (conversationId) {
    formData.append("conversation_id", conversationId);
  }

  if (requestedDeliverable) {
    formData.append("requested_deliverable", requestedDeliverable);
  }

  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`SOVARA API error: ${response.status}`);
  }

  return response.json();
}

export async function getAnalysisStatus(requestId: string) {
  const response = await fetch(
    `${API_BASE}/analysis/${encodeURIComponent(requestId)}`,
  );

  if (!response.ok) {
    throw new Error(`SOVARA analysis status error: ${response.status}`);
  }

  return response.json();
}

export function getDownloadUrl(requestId: string, fileName: string) {
  return `${API_BASE}/download/${encodeURIComponent(requestId)}/${encodeURIComponent(fileName)}`;
}

export async function getVaultDocuments() {
  const response = await fetch(`${API_BASE}/vault/documents`);

  if (!response.ok) {
    throw new Error(`SOVARA Vault error: ${response.status}`);
  }

  return response.json();
}

export async function searchVault(query: string, topK = 5) {
  const params = new URLSearchParams({
    query,
    top_k: String(topK),
  });

  const response = await fetch(`${API_BASE}/vault/search?${params}`);

  if (!response.ok) {
    throw new Error(`SOVARA Vault search error: ${response.status}`);
  }

  return response.json();
}

export async function uploadToVault(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/vault/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`SOVARA Vault upload error: ${response.status}`);
  }

  return response.json();
}

export async function deleteVaultDocument(documentId: string) {
  const response = await fetch(`${API_BASE}/vault/documents/${documentId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`SOVARA Vault delete error: ${response.status}`);
  }

  return response.json();
}

export async function reindexVaultDocument(documentId: string) {
  const response = await fetch(
    `${API_BASE}/vault/documents/${documentId}/reindex`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    throw new Error(`SOVARA Vault reindex error: ${response.status}`);
  }

  return response.json();
}

export function mapVaultDocument(document: any) {
  return {
    id: document.document_id,
    title: document.filename,
    class: "Standard" as const,
    kind: document.file_type?.toUpperCase() ?? "Document",
    uploaded: document.created_at?.slice(0, 7) ?? "",
    updated: document.updated_at?.slice(0, 7) ?? "",
    pages: document.pages ?? 0,
    excerpt: document.filename,
  };
}
