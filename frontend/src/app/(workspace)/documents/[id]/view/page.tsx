"use client";

import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

import { documentService } from "@/services/document.service";
import { ProgressActivityIcon, WarningIcon } from "@/components/shared/icons";

export default function DocumentViewPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const documentId = Number(params.id);
  const page = searchParams.get("page");

  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    documentService
      .getDocumentFileUrl(documentId)
      .then((url) => {
        if (!cancelled) setFileUrl(url);
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load document.");
      });

    return () => {
      cancelled = true;
    };
  }, [documentId]);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-destructive">
        <WarningIcon size={18} />
        {error}
      </div>
    );
  }

  if (!fileUrl) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
        <ProgressActivityIcon size={18} className="animate-spin" />
        Loading document...
      </div>
    );
  }

  const src = page ? `${fileUrl}#page=${page}` : fileUrl;

  return (
    <iframe
      src={src}
      title="Document viewer"
      className="h-full w-full border-0"
    />
  );
}