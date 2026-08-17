"use client";

import React, { useEffect, useState } from "react";

import { PdfViewerPanel } from "@/components/document-viewer/pdf-viewer-panel";
import { TextDocumentViewer } from "@/components/document-viewer/text-document-viewer";
import { ProgressActivityIcon, WarningIcon } from "@/components/shared/icons";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";
import { documentService } from "@/services/document.service";

export type DocumentViewerMode = "split" | "full";

interface DocumentViewerPanelProps {
  mode?: DocumentViewerMode;
  onClose?: () => void;
}

export function DocumentViewerPanel({ mode = "split", onClose }: DocumentViewerPanelProps) {
  const { documentId } = usePdfViewer();
  const [fileType, setFileType] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!documentId) return;
    let active = true;
    setFileType(null);
    setError(false);
    documentService
      .getDocument(documentId)
      .then((document) => {
        if (active) setFileType(document.file_type?.toLowerCase().replace(/^\./, "") ?? "");
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [documentId]);

  if (!documentId) return null;
  if (fileType === "pdf") return <PdfViewerPanel mode={mode} onClose={onClose} />;
  if (["doc", "docx", "txt", "text", "md", "markdown"].includes(fileType ?? "")) {
    return <TextDocumentViewer documentId={documentId} mode={mode} onClose={onClose} />;
  }

  return (
    <div className={`flex h-full items-center justify-center bg-background px-6 text-center text-xs text-muted-foreground ${mode === "split" ? "border-l border-border/70" : ""}`}>
      {error ? (
        <span className="flex items-center gap-2 text-destructive">
          <WarningIcon size={18} /> Unable to identify the document type.
        </span>
      ) : fileType === null ? (
        <span className="flex items-center gap-2">
          <ProgressActivityIcon size={18} className="animate-spin" /> Loading document...
        </span>
      ) : (
        "This document type cannot be previewed."
      )}
    </div>
  );
}
