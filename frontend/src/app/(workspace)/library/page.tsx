"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { DeleteDocumentDialog } from "@/components/documents/DeleteDocumentDialog";
import { Icon } from "@/components/shared/icons";
import { ToastContainer, useToast } from "@/components/shared/Toast";
import { DocumentListItem, documentService } from "@/services/document.service";

const PAGE_SIZE = 100;
const DOCUMENTS_PER_PAGE = 15;
const FILE_TYPE_FILTERS = ["all", "pdf", "docx", "markdown", "txt"] as const;

type FileTypeFilter = (typeof FILE_TYPE_FILTERS)[number];
type SortOption = "newest" | "oldest" | "name-asc" | "name-desc";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function normalizedFileType(fileType?: string): string {
  return fileType?.toLowerCase().replace(/^\./, "") || "file";
}

function filterFileType(fileType?: string): Exclude<FileTypeFilter, "all"> | "other" {
  const type = normalizedFileType(fileType);
  if (type === "pdf") return "pdf";
  if (type === "doc" || type === "docx") return "docx";
  if (type === "md" || type === "markdown") return "markdown";
  if (type === "txt" || type === "text") return "txt";
  return "other";
}

function documentIcon(fileType?: string): string {
  const type = normalizedFileType(fileType);
  if (type === "pdf") return "picture_as_pdf";
  if (type === "md" || type === "markdown") return "markdown";
  if (type === "txt" || type === "text") return "article";
  return "description";
}

function documentIconColor(fileType?: string): string {
  const type = filterFileType(fileType);
  if (type === "pdf") return "bg-red-50 text-red-600/80";
  if (type === "docx") return "bg-blue-50 text-blue-600/80";
  if (type === "markdown") return "bg-amber-50 text-amber-700/80";
  if (type === "txt") return "bg-emerald-50 text-emerald-700/75";
  return "bg-secondary text-muted-foreground";
}

function formatUploadDate(createdAt?: string): string | null {
  if (!createdAt) return null;
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return null;
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${day}/${month}/${date.getFullYear()}`;
}

function LibrarySkeleton() {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 px-4 py-8 sm:px-6">
      <div className="h-9 w-52 animate-pulse rounded-md bg-muted" />
      <div className="h-10 w-full animate-pulse rounded-lg bg-muted" />
      <div className="overflow-hidden rounded-xl border border-border bg-card">
        {[1, 2, 3, 4].map((item) => (
          <div key={item} className="h-20 animate-pulse border-b border-border last:border-b-0" />
        ))}
      </div>
    </div>
  );
}

export default function LibraryPage() {
  const router = useRouter();
  const documentsSectionRef = useRef<HTMLDivElement>(null);
  const { toasts, showToast, dismissToast } = useToast();
  const [documents, setDocuments] = useState<DocumentListItem[] | null>(null);
  const [search, setSearch] = useState("");
  const [fileTypeFilter, setFileTypeFilter] = useState<FileTypeFilter>("all");
  const [sort, setSort] = useState<SortOption>("newest");
  const [currentPage, setCurrentPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<DocumentListItem | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  const loadDocuments = useCallback(async () => {
    setError(null);

    try {
      const allDocuments: DocumentListItem[] = [];
      let page: DocumentListItem[];

      do {
        page = await documentService.listDocuments({ skip: allDocuments.length, limit: PAGE_SIZE });
        allDocuments.push(...page);
      } while (page.length === PAGE_SIZE);

      setDocuments(allDocuments);
    } catch {
      setError("Unable to load documents.");
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    window.addEventListener("document-uploaded", loadDocuments);
    return () => window.removeEventListener("document-uploaded", loadDocuments);
  }, [loadDocuments]);

  const filteredDocuments = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    const filtered = (documents ?? []).filter((document) => {
      const matchesSearch = document.title.toLowerCase().includes(normalizedSearch);
      const matchesType = fileTypeFilter === "all" || filterFileType(document.file_type) === fileTypeFilter;
      return matchesSearch && matchesType;
    });

    return [...filtered].sort((left, right) => {
      if (sort === "name-asc") return left.title.localeCompare(right.title);
      if (sort === "name-desc") return right.title.localeCompare(left.title);

      const leftDate = left.created_at ? new Date(left.created_at).getTime() : 0;
      const rightDate = right.created_at ? new Date(right.created_at).getTime() : 0;
      return sort === "oldest" ? leftDate - rightDate : rightDate - leftDate;
    });
  }, [documents, fileTypeFilter, search, sort]);

  const totalPages = Math.max(1, Math.ceil(filteredDocuments.length / DOCUMENTS_PER_PAGE));
  const paginatedDocuments = useMemo(() => {
    const start = (currentPage - 1) * DOCUMENTS_PER_PAGE;
    return filteredDocuments.slice(start, start + DOCUMENTS_PER_PAGE);
  }, [currentPage, filteredDocuments]);

  useEffect(() => {
    setCurrentPage(1);
  }, [fileTypeFilter, search, sort]);

  useEffect(() => {
    setCurrentPage((page) => Math.min(page, totalPages));
  }, [totalPages]);

  const viewDocument = (documentId: number) => {
    router.push(`/library/${documentId}`);
  };

  const goToPage = (page: number) => {
    const nextPage = Math.min(totalPages, Math.max(1, page));
    if (nextPage === currentPage) return;
    setCurrentPage(nextPage);
    window.requestAnimationFrame(() => {
      documentsSectionRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  };

  const downloadDocument = async (document: DocumentListItem) => {
    if (downloadingId !== null) return;
    setDownloadingId(document.id);
    try {
      const url = await documentService.getDocumentDownloadUrl(document.id);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = document.title;
      window.document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    } catch {
      showToast("Unable to download this document. Please try again.", "danger");
    } finally {
      setDownloadingId(null);
    }
  };

  const confirmDelete = async () => {
    if (!documentToDelete) return;

    setDeleting(true);
    setDeleteError(null);
    try {
      await documentService.deleteDocument(documentToDelete.id);
      setDocuments((current) => current?.filter((item) => item.id !== documentToDelete.id) ?? null);
      setDocumentToDelete(null);
    } catch {
      setDeleteError("Unable to delete this document. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  if (!documents && !error) return <LibrarySkeleton />;

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground">Library</h1>
        <button
          type="button"
          onClick={() => window.dispatchEvent(new Event("open-upload-modal"))}
          className="inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-lg bg-primary px-3.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <Icon name="add" className="text-base" />
          Upload
        </button>
      </div>

      <div className="relative mt-6">
        <Icon
          name="search"
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lg text-muted-foreground"
        />
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search documents..."
          aria-label="Search documents by filename"
          className="h-10 w-full rounded-lg border border-border bg-card pl-10 pr-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/15"
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1" aria-label="Filter documents by file type">
          {FILE_TYPE_FILTERS.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setFileTypeFilter(type)}
              aria-pressed={fileTypeFilter === type}
              className={`h-8 cursor-pointer rounded-md px-3 text-xs font-medium transition-colors ${
                fileTypeFilter === type
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            >
              {type === "all" ? "All" : type === "markdown" ? "Markdown" : type.toUpperCase()}
            </button>
          ))}
        </div>

        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          Sort
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as SortOption)}
            className="h-8 cursor-pointer rounded-md border border-border bg-card px-2 text-xs text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
          >
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="name-asc">Name A-Z</option>
            <option value="name-desc">Name Z-A</option>
          </select>
        </label>
      </div>

      <div ref={documentsSectionRef} className="mt-7 flex scroll-mt-4 items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">All documents</h2>
        {documents && documents.length > 0 && (
          <span className="text-xs text-muted-foreground">{filteredDocuments.length} documents</span>
        )}
      </div>

      {error ? (
        <div className="mt-4 rounded-xl border border-border bg-card px-6 py-10 text-center">
          <p className="text-sm text-destructive">{error}</p>
          <button type="button" onClick={() => void loadDocuments()} className="mt-3 text-sm font-medium text-primary hover:underline">
            Try again
          </button>
        </div>
      ) : documents?.length === 0 ? (
        <div className="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center">
          <Icon name="description" className="text-[56px] text-muted-foreground/35" />
          <p className="mt-4 text-sm font-medium text-foreground">No documents yet</p>
          <p className="mt-1.5 text-xs text-muted-foreground">
            Upload a document to start building your library.
          </p>
        </div>
      ) : filteredDocuments.length === 0 ? (
        <div className="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center">
          <Icon name="find_in_page" className="text-[56px] text-muted-foreground/35" />
          <p className="mt-4 text-sm font-medium text-foreground">No documents found</p>
          <p className="mt-1.5 text-xs text-muted-foreground">
            Try adjusting your search or filters.
          </p>
        </div>
      ) : (
        <>
        <div className="mt-4 space-y-2.5">
          {paginatedDocuments.map((document) => {
            const uploadDate = formatUploadDate(document.created_at);
            return (
            <div
              key={document.id}
              role="link"
              tabIndex={0}
              onClick={() => viewDocument(document.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  viewDocument(document.id);
                }
              }}
              className="group flex min-h-24 cursor-pointer items-center gap-3 rounded-xl border border-border bg-card px-4 py-4 transition-colors hover:border-primary/25 hover:bg-secondary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 sm:gap-4 sm:px-5"
            >
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${documentIconColor(document.file_type)}`}>
                <Icon name={documentIcon(document.file_type)} className="text-xl" />
              </div>

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground group-hover:text-primary">
                  {document.title}
                </p>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {formatFileSize(document.file_size)}
                  {uploadDate && ` · ${uploadDate}`}
                </p>
              </div>

              <button
                type="button"
                disabled={downloadingId !== null}
                onClick={(event) => {
                  event.stopPropagation();
                  void downloadDocument(document);
                }}
                aria-label={`Download ${document.title}`}
                title="Download"
                className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-md text-muted-foreground/65 transition-colors hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-45"
              >
                <Icon
                  name={downloadingId === document.id ? "progress_activity" : "download"}
                  className={`text-lg ${downloadingId === document.id ? "animate-spin" : ""}`}
                />
              </button>

              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  setDeleteError(null);
                  setDocumentToDelete(document);
                }}
                aria-label={`Delete ${document.title}`}
                title="Delete document"
                className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-md text-muted-foreground/65 transition-colors hover:bg-destructive/10 hover:text-destructive"
              >
                <Icon name="delete" className="text-lg" />
              </button>
            </div>
            );
          })}
        </div>

        {totalPages > 1 && (
          <nav className="mt-7 flex flex-wrap items-center justify-center gap-1" aria-label="Library pagination">
            <button
              type="button"
              disabled={currentPage === 1}
              onClick={() => goToPage(currentPage - 1)}
              className="h-8 cursor-pointer rounded-md px-3 text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>
            {Array.from({ length: totalPages }, (_, index) => index + 1).map((page) => (
              <button
                key={page}
                type="button"
                onClick={() => goToPage(page)}
                aria-current={currentPage === page ? "page" : undefined}
                className={`h-8 min-w-8 cursor-pointer rounded-md px-2 text-xs font-medium transition-colors ${
                  currentPage === page
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                }`}
              >
                {page}
              </button>
            ))}
            <button
              type="button"
              disabled={currentPage === totalPages}
              onClick={() => goToPage(currentPage + 1)}
              className="h-8 cursor-pointer rounded-md px-3 text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </nav>
        )}
        </>
      )}

      <DeleteDocumentDialog
        document={documentToDelete}
        deleting={deleting}
        error={deleteError}
        onClose={() => {
          setDocumentToDelete(null);
          setDeleteError(null);
        }}
        onConfirm={() => void confirmDelete()}
      />
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
