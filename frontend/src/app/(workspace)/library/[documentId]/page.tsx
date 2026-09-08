"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import axios from "axios";
import { DocumentViewerPanel } from "@/components/document-viewer/document-viewer-panel";
import { AccessNotFound } from "@/components/shared/AccessNotFound";
import { ProgressActivityIcon, WarningIcon } from "@/components/shared/icons";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";
import { documentService } from "@/services/document.service";

export default function LibraryDocumentPage() {
  const params = useParams<{ documentId: string }>();
  const router = useRouter();
  const routeDocumentId = Number(params.documentId);
  const { documentId, openDocument, closeViewer } = usePdfViewer();
  const [error, setError] = useState<string | null>(null);
  const [accessNotFound, setAccessNotFound] = useState(false);

  useEffect(() => {
    if (!Number.isInteger(routeDocumentId) || routeDocumentId <= 0) {
      setAccessNotFound(true);
      return;
    }

    let active = true;
    setError(null);
    setAccessNotFound(false);
    documentService
      .getDocument(routeDocumentId)
      .then((document) => {
        if (!active) return;
        if (!document) {
          setAccessNotFound(true);
          return;
        }
        openDocument({ id: document.id, title: document.title });
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (axios.isAxiosError(error) && (error.response?.status === 403 || error.response?.status === 404)) {
          setAccessNotFound(true);
        } else {
          setError("Unable to load this document.");
        }
      });

    return () => {
      active = false;
    };
  }, [openDocument, routeDocumentId]);

  const backToLibrary = () => {
    closeViewer();
    router.push("/library");
  };

  if (accessNotFound) {
    return <AccessNotFound />;
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-sm text-destructive">
        <span className="flex items-center gap-2">
          <WarningIcon size={18} /> {error}
        </span>
        <button type="button" onClick={backToLibrary} className="text-sm font-medium text-primary hover:underline">
          Back to Library
        </button>
      </div>
    );
  }

  if (documentId !== routeDocumentId) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
        <ProgressActivityIcon size={18} className="animate-spin" /> Loading document...
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 w-full overflow-hidden">
      <DocumentViewerPanel mode="full" onClose={backToLibrary} />
    </div>
  );
}
