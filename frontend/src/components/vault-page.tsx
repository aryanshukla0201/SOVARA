import { Download, PencilLine, Plus, Search, Upload, X } from "lucide-react";
import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { Shell } from "@/components/chrome";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { VaultDoc } from "@/lib/data";
import {
  deleteVaultDocument,
  getVaultDocuments,
  mapVaultDocument,
  reindexVaultDocument,
  searchVault,
  uploadToVault,
} from "@/lib/sovara-api";
import { downloadText } from "@/lib/download";
import { cn } from "@/lib/utils";

const KINDS = ["All", "SOP", "Standard", "Manual", "Drawing", "Template", "Mail"] as const;
const UPLOAD_KINDS = ["SOP", "Standard", "Manual", "Drawing", "Template", "Mail"] as const;

const DEFAULT_DESCRIPTION =
  "Retrieval is dense + keyword over this corpus only. Embeddings live on 10.12.0.8. A query never constructs an HTTPS host outside the plant prefix.";

type VaultDraft = {
  title: string;
  description: string;
};

type UploadDraft = {
  title: string;
  category: (typeof UPLOAD_KINDS)[number];
  description: string;
  fileName: string;
  file?: File;
};

function formatUploadedDate(value: string) {
  if (!value) return "";

  const [year, month] = value.split("-").map((part) => Number.parseInt(part, 10));

  if (!year || !month) return value;

  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(year, month - 1, 1));
}

function toFileStem(fileName: string) {
  return fileName.replace(/\.[^.]+$/, "");
}

function toVaultFileName(doc: VaultDoc | undefined) {
  if (!doc) return "";
  return doc.fileName ?? `${doc.title.replace(/[^\w.-]+/g, "_")}.pdf`;
}

export function VaultPage() {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<(typeof KINDS)[number]>("All");
  const [docs, setDocs] = useState<VaultDoc[]>([]);
  const [open, setOpen] = useState("");
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [vaultError, setVaultError] = useState<string | null>(null);
  const [searchMatches, setSearchMatches] = useState<string[] | null>(null);

  const [editing, setEditing] = useState(false);
  const [addingKnowledge, setAddingKnowledge] = useState(false);

  const [drafts, setDrafts] = useState<Record<string, VaultDraft>>({});
  const [draftTitle, setDraftTitle] = useState("");
  const [draftDescription, setDraftDescription] = useState(DEFAULT_DESCRIPTION);

  const [uploadDraft, setUploadDraft] = useState<UploadDraft>({
    title: "",
    category: "SOP",
    description: "",
    fileName: "",
  });

  useEffect(() => {
    let cancelled = false;

    async function loadVault() {
      setLoading(true);
      setVaultError(null);

      try {
        const result = await getVaultDocuments();

        const rawDocuments = Array.isArray(result)
          ? result
          : result.documents ?? [];

        const documents = rawDocuments.map(mapVaultDocument);

        if (!cancelled) {
          setDocs(documents);

          setOpen((current) => {
            if (current && documents.some((doc: VaultDoc) => doc.id === current)) {
              return current;
            }

            return documents[0]?.id ?? "";
          });
        }
      } catch (error) {
        if (!cancelled) {
          setVaultError(
            error instanceof Error ? error.message : "Failed to load vault.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadVault();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const query = q.trim();

    if (!query) {
      setSearchMatches(null);
      return;
    }

    let cancelled = false;

    async function runSearch() {
      setSearching(true);
      setVaultError(null);

      try {
        const result = await searchVault(query, 5);

        const results: Array<{ source_file_id?: string }> =
          Array.isArray(result) ? result : result.results ?? [];

        if (!cancelled) {
          setSearchMatches(
            Array.from(
              new Set(
                results
                  .map((item) => item.source_file_id)
                  .filter((id): id is string => Boolean(id)),
              ),
            ),
          );
        }
      } catch (error) {
        if (!cancelled) {
          setVaultError(
            error instanceof Error ? error.message : "Vault search failed.",
          );
        }
      } finally {
        if (!cancelled) {
          setSearching(false);
        }
      }
    }

    const timer = window.setTimeout(() => {
      void runSearch();
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [q]);

  const rows = useMemo(() => {
    return docs.filter((doc) => {
      const matchQ =
        searchMatches === null || searchMatches.includes(doc.id);

      const matchK =
        kind === "All" ||
        doc.kind.toLowerCase() === kind.toLowerCase();

      return matchQ && matchK;
    });
  }, [docs, kind, searchMatches]);

  const active =
    docs.find((doc) => doc.id === open) ??
    rows[0] ??
    docs[0];

  const saved = active ? drafts[active.id] : undefined;

  const displayTitle =
    saved?.title ??
    active?.title ??
    "";

  const displayDescription =
    saved?.description ??
    DEFAULT_DESCRIPTION;

  const displayFileName = toVaultFileName(active);

  useEffect(() => {
    if (!active || addingKnowledge) return;

    const next = drafts[active.id];

    setDraftTitle(next?.title ?? active.title);
    setDraftDescription(next?.description ?? DEFAULT_DESCRIPTION);
    setEditing(false);
  }, [active?.id, drafts, addingKnowledge]);

  const handleDownload = () => {
    if (!active) return;

    downloadText(
      displayFileName,
      `${displayTitle}\n\n${active.pages} pages · uploaded on ${formatUploadedDate(active.uploaded)}\n\n${displayDescription}\n`,
      "text/plain",
    );
  };

  const handleStartEdit = () => {
    if (!active) return;

    setDraftTitle(saved?.title ?? active.title);
    setDraftDescription(saved?.description ?? DEFAULT_DESCRIPTION);
    setEditing(true);
  };

  const handleCancelEdit = () => {
    if (!active) return;

    setDraftTitle(saved?.title ?? active.title);
    setDraftDescription(saved?.description ?? DEFAULT_DESCRIPTION);
    setEditing(false);
  };

  const handleSaveEdit = () => {
    if (!active) return;

    setDrafts((current) => ({
      ...current,
      [active.id]: {
        title: draftTitle.trim() || active.title,
        description: draftDescription.trim() || DEFAULT_DESCRIPTION,
      },
    }));

    setEditing(false);
  };

  const handleStartAddKnowledge = () => {
    setAddingKnowledge(true);
    setEditing(false);

    setUploadDraft({
      title: "",
      category: "SOP",
      description: "",
      fileName: "",
    });
  };

  const handleUploadFileChange = (
    event: ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setUploadDraft((current) => ({
      ...current,
      file,
      fileName: file.name,
      title: current.title.trim() || toFileStem(file.name),
    }));
  };

  const handleSaveKnowledge = async () => {
    const file = uploadDraft.file;

    if (!file) return;

    setVaultError(null);

    try {
      await uploadToVault(file);

      const result = await getVaultDocuments();

      const rawDocuments = Array.isArray(result)
        ? result
        : result.documents ?? [];

      const documents = rawDocuments.map(mapVaultDocument);

      setDocs(documents);

      const uploadedDocument =
        documents.find(
          (doc: VaultDoc) =>
            doc.title === file.name ||
            doc.fileName === file.name,
        ) ?? documents[0];

      if (uploadedDocument) {
        setOpen(uploadedDocument.id);
      }

      setUploadDraft({
        title: "",
        category: "SOP",
        description: "",
        fileName: "",
      });

      setEditing(false);
      setAddingKnowledge(false);
    } catch (error) {
      setVaultError(
        error instanceof Error
          ? error.message
          : "Failed to upload document.",
      );
    }
  };

  const handleCancelAddKnowledge = () => {
    setAddingKnowledge(false);

    setUploadDraft({
      title: "",
      category: "SOP",
      description: "",
      fileName: "",
    });
  };

  const handleDelete = async () => {
    if (!active) return;

    setVaultError(null);

    try {
      await deleteVaultDocument(active.id);

      const nextDocs = docs.filter(
        (doc) => doc.id !== active.id,
      );

      setDocs(nextDocs);
      setOpen(nextDocs[0]?.id ?? "");
      setEditing(false);
    } catch (error) {
      setVaultError(
        error instanceof Error
          ? error.message
          : "Failed to delete document.",
      );
    }
  };

  const handleReindex = async () => {
    if (!active) return;

    setVaultError(null);

    try {
      await reindexVaultDocument(active.id);

      const result = await getVaultDocuments();

      const rawDocuments = Array.isArray(result)
        ? result
        : result.documents ?? [];

      const documents = rawDocuments.map(mapVaultDocument);

      setDocs(documents);
    } catch (error) {
      setVaultError(
        error instanceof Error
          ? error.message
          : "Failed to reindex document.",
      );
    }
  };

  return (
    <Shell mode="app">
      <div className="mx-auto flex min-h-0 w-full max-w-6xl flex-1 flex-col md:flex-row">
        <section className="flex min-h-0 w-full flex-col border-border md:w-96 md:border-r lg:w-[28rem]">
          <div className="space-y-3 p-4">
            <div className="flex items-start justify-between gap-3">
              <p className="font-mono text-xs uppercase tracking-widest text-ok">
                Knowledge vault
              </p>

              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={handleStartAddKnowledge}
              >
                <Plus className="size-4" />
                Add knowledge
              </Button>
            </div>

            <h1 className="font-display text-2xl font-medium tracking-tight">
              Manuals, SOPs, mail.
            </h1>

            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-faint" />

              <Input
                value={q}
                onChange={(event) => setQ(event.target.value)}
                placeholder="Search the local index"
                className="pl-10"
                aria-label="Search vault"
              />
            </div>

            <div className="flex gap-1 overflow-x-auto pb-1">
              {KINDS.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setKind(item)}
                  className={cn(
                    "h-9 shrink-0 rounded-md px-3 text-sm",
                    kind === item
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground",
                  )}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <ul className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
            {loading ? (
              <li className="px-3 py-8 text-sm text-muted-foreground">
                Loading vault...
              </li>
            ) : (
              <>
                {rows.map((doc) => (
                  <li key={doc.id}>
                    <button
                      type="button"
                      onClick={() => {
                        setAddingKnowledge(false);
                        setOpen(doc.id);
                      }}
                      className={cn(
                        "w-full rounded-lg px-3 py-3 text-left",
                        active?.id === doc.id && !addingKnowledge
                          ? "bg-secondary"
                          : "hover:bg-secondary/50",
                      )}
                    >
                      <span className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium">
                          {doc.title}
                        </span>

                        <Badge
                          variant={
                            doc.class === "Restricted"
                              ? "warn"
                              : "default"
                          }
                        >
                          {doc.class}
                        </Badge>
                      </span>

                      <span className="mt-1 block font-mono text-xs text-faint">
                        {doc.pages} pages · uploaded on{" "}
                        {formatUploadedDate(doc.uploaded)}
                      </span>
                    </button>
                  </li>
                ))}

                {rows.length === 0 ? (
                  <li className="px-3 py-8 text-sm text-muted-foreground">
                    No documents in this slice.
                  </li>
                ) : null}
              </>
            )}
          </ul>
        </section>

        <article className="hidden min-h-0 flex-1 overflow-y-auto p-6 md:block">
          {vaultError ? (
            <div className="mb-4 rounded-lg border border-border bg-elevated p-3 text-sm text-crit">
              {vaultError}
            </div>
          ) : null}

          {addingKnowledge ? (
            <div className="mx-auto max-w-xl">
              <div className="space-y-4 rounded-2xl border border-border bg-elevated/70 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
                      Upload
                    </p>

                    <h2 className="mt-2 font-display text-2xl font-medium tracking-tight">
                      Add knowledge
                    </h2>
                  </div>

                  <Badge variant="ok">Internal</Badge>
                </div>

                <label className="block space-y-2">
                  <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
                    File
                  </span>

                  <Input
                    type="file"
                    onChange={handleUploadFileChange}
                    aria-label="Upload file"
                  />

                  <span className="block text-xs text-muted-foreground">
                    {uploadDraft.fileName
                      ? `Selected: ${uploadDraft.fileName}`
                      : "Choose a file from your system."}
                  </span>
                </label>

                <label className="block space-y-2">
                  <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
                    Title
                  </span>

                  <Input
                    value={uploadDraft.title}
                    onChange={(event) =>
                      setUploadDraft((current) => ({
                        ...current,
                        title: event.target.value,
                      }))
                    }
                    placeholder="Document title"
                    aria-label="Upload title"
                  />
                </label>

                <label className="block space-y-2">
                  <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
                    Category
                  </span>

                  <select
                    value={uploadDraft.category}
                    onChange={(event) =>
                      setUploadDraft((current) => ({
                        ...current,
                        category:
                          event.target.value as UploadDraft["category"],
                      }))
                    }
                    className="flex h-11 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    aria-label="Upload category"
                  >
                    {UPLOAD_KINDS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-2">
                  <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
                    Description
                  </span>

                  <Textarea
                    value={uploadDraft.description}
                    onChange={(event) =>
                      setUploadDraft((current) => ({
                        ...current,
                        description: event.target.value,
                      }))
                    }
                    className="min-h-32"
                    placeholder="Short description"
                    aria-label="Upload description"
                  />
                </label>

                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    onClick={handleSaveKnowledge}
                    disabled={!uploadDraft.file}
                    className="min-w-24"
                  >
                    <Upload className="size-4" />
                    Save
                  </Button>

                  <Button
                    variant="ghost"
                    type="button"
                    onClick={handleCancelAddKnowledge}
                  >
                    <X className="size-4" />
                    Cancel
                  </Button>
                </div>
              </div>
            </div>
          ) : active ? (
            <div className="mx-auto max-w-xl">
              <div className="flex items-start justify-between gap-3">
                <Badge
                  variant={
                    active.class === "Restricted"
                      ? "warn"
                      : "ok"
                  }
                >
                  {active.class}
                </Badge>

                {editing ? (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      type="button"
                      onClick={handleCancelEdit}
                    >
                      <X className="size-4" />
                      Cancel
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      type="button"
                      onClick={handleSaveEdit}
                    >
                      Save
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0"
                    type="button"
                    onClick={handleStartEdit}
                  >
                    <PencilLine className="size-4" />
                    Edit
                  </Button>
                )}
              </div>

              <div className="mt-3 space-y-2">
                {editing ? (
                  <Input
                    value={draftTitle}
                    onChange={(event) =>
                      setDraftTitle(event.target.value)
                    }
                    className="h-11 font-display text-2xl font-medium tracking-tight"
                    aria-label="Edit title"
                  />
                ) : (
                  <h2 className="font-display text-2xl font-medium tracking-tight">
                    {displayTitle}
                  </h2>
                )}

                <p className="font-mono text-xs uppercase tracking-widest text-faint">
                  {active.pages} pages · uploaded on{" "}
                  {formatUploadedDate(active.uploaded)}
                </p>
              </div>

              <div className="mt-6 rounded-xl border border-border bg-background/70 px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {displayFileName}
                    </p>

                    <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
                      Local vault file
                    </p>
                  </div>

                  <Button
                    variant="muted"
                    size="sm"
                    className="shrink-0"
                    type="button"
                    onClick={handleDownload}
                  >
                    <Download className="size-4" />
                    Download
                  </Button>
                </div>
              </div>

              <div className="mt-6 space-y-2">
                <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
                  File description
                </p>

                {editing ? (
                  <Textarea
                    value={draftDescription}
                    onChange={(event) =>
                      setDraftDescription(event.target.value)
                    }
                    className="min-h-32"
                    aria-label="Edit file description"
                  />
                ) : (
                  <p className="rounded-lg border border-border bg-elevated p-4 text-sm leading-relaxed text-foreground/90">
                    {displayDescription}
                  </p>
                )}
              </div>

              <div className="mt-4 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  type="button"
                  onClick={handleReindex}
                >
                  Reindex
                </Button>

                {editing ? (
                  <Button
                    size="sm"
                    type="button"
                    onClick={handleDelete}
                    className="border border-border bg-destructive/10 text-crit hover:bg-destructive/15"
                  >
                    Delete file
                  </Button>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-xl py-12 text-sm text-muted-foreground">
              No document selected.
            </div>
          )}
        </article>
      </div>
    </Shell>
  );
}