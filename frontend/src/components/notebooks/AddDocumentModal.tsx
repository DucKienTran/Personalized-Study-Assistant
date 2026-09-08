"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import { documentService, DocumentListItem } from "@/services/document.service";
import { notebookService } from "@/services/notebook.service";

interface AddDocumentModalProps {
  isOpen: boolean;
  notebookId?: number;
  existingDocIdsInNotebook?: number[];
  showExisting?: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function AddDocumentModal({
  isOpen,
  notebookId,
  existingDocIdsInNotebook = [],
  showExisting = true,
  onClose,
  onSuccess,
}: AddDocumentModalProps) {
  const [addDocTab, setAddDocTab] = useState<"upload" | "existing">("upload");
  const [uploadSource, setUploadSource] = useState<"file" | "paste">("file");
  const [textContent, setTextContent] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State cho tab chọn tài liệu sẵn có
  const [existingDocs, setExistingDocs] = useState<DocumentListItem[]>([]);
  const [loadingExistingDocs, setLoadingExistingDocs] = useState(false);
  const [loadingMoreExistingDocs, setLoadingMoreExistingDocs] = useState(false);
  const [hasMoreExistingDocs, setHasMoreExistingDocs] = useState(true);
  const [existingSearch, setExistingSearch] = useState("");
  const [debouncedExistingSearch, setDebouncedExistingSearch] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const existingRequestIdRef = useRef(0);
  const existingLoadMoreRef = useRef<HTMLDivElement>(null);
  const EXISTING_PAGE_SIZE = 20;

  // Tải danh sách tài liệu trong thư viện khi modal mở
  useEffect(() => {
    if (isOpen) {
      setUploadError(null);
      setSelectedDocIds([]);
      setAddDocTab("upload");
      setUploadSource("file");
      setTextContent("");
      setExistingSearch("");
      setDebouncedExistingSearch("");
    }
  }, [isOpen, showExisting]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedExistingSearch(existingSearch.trim());
    }, 300);

    return () => window.clearTimeout(timeoutId);
  }, [existingSearch]);

  const loadExistingDocuments = useCallback(
    async (reset: boolean) => {
      if (!showExisting || !isOpen) return;

      const requestId = ++existingRequestIdRef.current;
      const skip = reset ? 0 : existingDocs.length;

      try {
        if (reset) {
          setLoadingExistingDocs(true);
        } else {
          setLoadingMoreExistingDocs(true);
        }

        const docs = await documentService.listDocuments({
          skip,
          limit: EXISTING_PAGE_SIZE,
          search: debouncedExistingSearch || undefined,
        });

        if (requestId !== existingRequestIdRef.current) return;

        setExistingDocs((current) => (reset ? docs : [...current, ...docs]));
        setHasMoreExistingDocs(docs.length === EXISTING_PAGE_SIZE);
      } catch (err) {
        if (requestId !== existingRequestIdRef.current) return;
        console.error("Failed to fetch existing documents:", err);
        setUploadError("Failed to load existing documents.");
      } finally {
        if (requestId === existingRequestIdRef.current) {
          setLoadingExistingDocs(false);
          setLoadingMoreExistingDocs(false);
        }
      }
    },
    [debouncedExistingSearch, existingDocs.length, isOpen, showExisting]
  );

  useEffect(() => {
    if (!isOpen || !showExisting) return;
    setExistingDocs([]);
    setHasMoreExistingDocs(true);
    void loadExistingDocuments(true);
    // loadExistingDocuments intentionally omitted: this effect resets pagination only when the query/modal changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedExistingSearch, isOpen, showExisting]);

  useEffect(() => {
    const target = existingLoadMoreRef.current;
    if (!target || !hasMoreExistingDocs || loadingExistingDocs || loadingMoreExistingDocs) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void loadExistingDocuments(false);
      },
      { rootMargin: "120px" }
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [hasMoreExistingDocs, loadingExistingDocs, loadingMoreExistingDocs, loadExistingDocuments]);

  if (!isOpen) return null;

  // Lọc các tài liệu chưa có trong Notebook này
  const existingInNotebookSet = new Set(existingDocIdsInNotebook);
  const availableDocs = existingDocs.filter((d) => !existingInNotebookSet.has(d.id));

  // ===== XỬ LÝ UPLOAD FILE MỚI =====
  const handleUploadFile = async (file: File) => {
    if (!/\.(pdf|docx|txt|md)$/i.test(file.name)) {
      setUploadError("Only PDF, DOCX, TXT, and MD files are supported.");
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);

      // 1. Upload tài liệu lên server
      const uploadedDoc = await documentService.uploadDocument(file);

      // Library uploads only create the document; Notebook uploads also attach it.
      if (notebookId !== undefined) {
        await notebookService.addDocuments(notebookId, {
          document_ids: [uploadedDoc.id],
        });
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      console.error("Upload error:", err);
      setUploadError(err?.message || "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleUploadFile(e.dataTransfer.files[0]);
    }
  };

  const handlePasteText = async () => {
    const title = textContent
      .split(/\r?\n/)
      .find((line) => line.trim())
      ?.trim()
      .slice(0, 100);
    if (!title || !textContent.trim()) return;
    try {
      setIsUploading(true);
      setUploadError(null);

      const document = await documentService.createTextDocument(
        title,
        textContent
      );
      if (notebookId !== undefined) {
        await notebookService.addDocuments(notebookId, {
          document_ids: [document.id],
        });
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      console.error("Paste text error:", err);
      setUploadError(
        err?.response?.data?.detail || "Unable to add pasted text. Please try again."
      );
    } finally {
      setIsUploading(false);
    }
  };

  // ===== XỬ LÝ CHỌN TÀI LIỆU CÓ SẴN =====
  const handleAddSelectedDocs = async () => {
    if (selectedDocIds.length === 0 || notebookId === undefined) return;
    try {
      setIsUploading(true);
      await notebookService.addDocuments(notebookId, {
        document_ids: selectedDocIds,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      console.error("Error adding documents:", err);
      setUploadError("Failed to add selected documents.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      {/* Tăng độ rộng Modal lên max-w-2xl */}
      <div className="flex h-[510px] max-h-[calc(100vh-2rem)] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-xl">
        {/* Header Modal */}
        <div className="p-5 border-b border-border/60 flex items-center justify-between">
          <h3 className="font-heading text-lg font-bold">
            {notebookId === undefined ? "Upload Document" : "Add Document to Notebook"}
          </h3>
          <button
            onClick={onClose}
            disabled={isUploading}
            className="text-muted-foreground hover:text-foreground p-1 rounded-lg transition-colors cursor-pointer"
          >
            <Icon name="close" className="text-xl" />
          </button>
        </div>

        {/* Tabs trong Modal */}
        {showExisting && (
        <div className="flex border-b border-border/60 bg-secondary/30 p-1.5">
          <button
            onClick={() => setAddDocTab("upload")}
            className={`flex-1 rounded-lg py-2 text-xs font-normal transition-all cursor-pointer ${
            addDocTab === "upload"
                ? "bg-card text-[#4F4A43] shadow-2xs"
                : "text-[#8D867C] hover:text-[#5F5A52]"
            }`}
          >
            Upload New File
          </button>
          <button
            onClick={() => setAddDocTab("existing")}
            className={`flex-1 rounded-lg py-2 text-xs font-normal transition-all cursor-pointer ${
            addDocTab === "existing"
                ? "bg-card text-[#4F4A43] shadow-2xs"
                : "text-[#8D867C] hover:text-[#5F5A52]"
            }`}
          >
            Choose Existing ({availableDocs.length})
          </button>
        </div>
        )}

        {/* Content Body */}
        <div className="min-h-0 flex-1 overflow-y-auto p-6">
          {uploadError && (
            <div className="mb-4 p-3 bg-destructive/10 text-destructive text-xs rounded-xl border border-destructive/20">
              {uploadError}
            </div>
          )}

          {/* TAB 1: UPLOAD FILE MỚI */}
          {addDocTab === "upload" && (
            <div className="h-full min-h-[300px]">
              <input
                type="file"
                ref={fileInputRef}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleUploadFile(e.target.files[0]);
                  }
                }}
                className="hidden"
                accept=".pdf,.docx,.txt,.md"
              />

              {uploadSource === "file" ? (
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    if (!isUploading) setIsDragOver(true);
                  }}
                  onDragLeave={() => setIsDragOver(false)}
                  onDrop={(e) => {
                    if (!isUploading) handleDrop(e);
                    else e.preventDefault();
                  }}
                  className={`flex h-full min-h-[300px] flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
                    isDragOver
                      ? "scale-[0.99] border-primary bg-primary/5"
                      : "border-border/80 bg-secondary/20"
                  }`}
                >
                  {isUploading ? (
                    <div className="flex flex-col items-center gap-2">
                      <Icon name="progress_activity" className="animate-spin text-3xl text-primary" />
                      <p className="text-xs font-normal text-foreground">
                        {notebookId === undefined ? "Uploading document..." : "Uploading & adding document..."}
                      </p>
                    </div>
                  ) : (
                    <>
                      <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                        <Icon name="cloud_upload" className="text-3xl" />
                      </div>
                      <p className="text-sm font-normal text-foreground">
                        Drag & drop a document here
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Supports PDF, DOCX, TXT, MD
                      </p>
                      <div className="mt-6 flex flex-wrap justify-center gap-3">
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-normal text-primary-foreground transition-colors hover:bg-[var(--primary-hover)]"
                        >
                          <Icon name="upload_file" className="text-base" />
                          Upload file
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setUploadSource("paste");
                            setUploadError(null);
                          }}
                          className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-xs font-normal text-foreground transition-colors hover:border-primary/50 hover:bg-primary/5"
                        >
                          <Icon name="content_paste" className="text-base text-primary" />
                          Paste text
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div className="flex h-full min-h-[300px] flex-col rounded-2xl border border-border/80 bg-secondary/20 p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <button
                      type="button"
                      disabled={isUploading}
                      onClick={() => {
                        setUploadSource("file");
                        setUploadError(null);
                      }}
                      title="Back to upload"
                      aria-label="Back to upload"
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:opacity-50"
                    >
                      <Icon name="arrow_back" className="text-base" />
                    </button>
                    <h4 className="text-sm font-normal text-foreground">Paste text</h4>
                  </div>

                  <textarea
                    id="notebook-paste-content"
                    value={textContent}
                    disabled={isUploading}
                    onChange={(event) => setTextContent(event.target.value)}
                    placeholder="Paste or type text here..."
                    className="min-h-40 flex-1 resize-none rounded-xl border border-border bg-card px-3 py-2.5 text-sm font-normal leading-6 text-foreground outline-none transition focus:border-primary/60 focus:ring-2 focus:ring-primary/10 disabled:opacity-60"
                  />

                  <div className="mt-4 flex justify-end">
                    <Button
                      type="button"
                      onClick={handlePasteText}
                      disabled={isUploading || !textContent.trim()}
                      className="rounded-xl text-xs font-normal"
                    >
                      {isUploading && (
                        <Icon name="progress_activity" className="mr-1.5 animate-spin text-sm" />
                      )}
                      {isUploading ? "Adding..." : "Add"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: CHỌN TÀI LIỆU ĐÃ CÓ */}
          {showExisting && addDocTab === "existing" && (
            <div className="flex h-full min-h-0 flex-col gap-4">
              <div className="relative shrink-0">
                <Icon
                  name="search"
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lg text-muted-foreground"
                />
                <input
                  type="search"
                  value={existingSearch}
                  onChange={(event) => setExistingSearch(event.target.value)}
                  placeholder="Search documents..."
                  aria-label="Search existing documents by filename"
                  className="h-10 w-full rounded-lg border border-border bg-card pl-10 pr-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/15"
                />
              </div>

              {loadingExistingDocs ? (
                <div className="flex flex-1 items-center justify-center gap-2 py-10 text-center text-xs text-muted-foreground">
                  <Icon name="progress_activity" className="animate-spin text-lg" />
                  Loading documents...
                </div>
              ) : availableDocs.length === 0 && !hasMoreExistingDocs ? (
                <div className="flex flex-1 items-center justify-center py-10 text-center text-xs text-muted-foreground">
                  {debouncedExistingSearch ? "No documents found." : "No other documents available in your library."}
                </div>
              ) : (
                <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
                  {availableDocs.map((doc) => {
                    const isSelected = selectedDocIds.includes(doc.id);
                    return (
                      <div
                        key={doc.id}
                        onClick={() => {
                          setSelectedDocIds((prev) =>
                            isSelected
                              ? prev.filter((id) => id !== doc.id)
                              : [...prev, doc.id]
                          );
                        }}
                        className={`p-3 border rounded-xl flex items-center justify-between cursor-pointer transition-all ${
                          isSelected
                            ? "border-primary bg-primary/5"
                            : "border-border/80 hover:bg-secondary/40"
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <Icon name="description" className="text-lg text-muted-foreground shrink-0" />
                          <span className="text-xs font-normal truncate">{doc.title}</span>
                        </div>
                        <div
                          className={`w-4 h-4 rounded-md border flex items-center justify-center ${
                            isSelected
                              ? "bg-primary border-primary text-primary-foreground"
                              : "border-border"
                          }`}
                        >
                          {isSelected && <Icon name="check" className="text-xs" />}
                        </div>
                      </div>
                    );
                  })}
                  {hasMoreExistingDocs && <div ref={existingLoadMoreRef} className="h-px" aria-hidden="true" />}
                  {loadingMoreExistingDocs && (
                    <div className="flex items-center justify-center gap-2 py-3 text-xs text-muted-foreground">
                      <Icon name="progress_activity" className="animate-spin text-base" />
                      Loading more...
                    </div>
                  )}
                </div>
              )}

              <div className="flex shrink-0 justify-end border-t border-border/60 pt-4">
                <Button
                  onClick={handleAddSelectedDocs}
                  disabled={selectedDocIds.length === 0 || isUploading}
                  className="cursor-pointer rounded-xl bg-primary text-xs font-normal text-primary-foreground hover:bg-[var(--primary-hover)]"
                >
                  {isUploading && (
                    <Icon name="progress_activity" className="animate-spin text-sm mr-1.5" />
                  )}
                  Add Selected ({selectedDocIds.length})
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
