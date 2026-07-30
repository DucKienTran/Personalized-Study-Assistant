"use client";

import React from "react";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";

function SplitPanelToggleIcon({ isActive }: { isActive: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
    >
      <rect
        x="1"
        y="2"
        width="14"
        height="12"
        rx="1.5"
        stroke="currentColor"
        strokeWidth="1.3"
      />

      <line
        x1="10.5"
        y1="2"
        x2="10.5"
        y2="14"
        stroke="currentColor"
        strokeWidth="1.3"
      />

      <rect
        x="10.5"
        y="2"
        width="4.5"
        height="12"
        fill="currentColor"
        opacity={isActive ? 0.85 : 0}
      />
    </svg>
  );
}


export function PdfViewerToggle() {
  const {
    isOpen,
    documentId,
    toggleViewer,
  } = usePdfViewer();

  const hasDocument = documentId !== null;


  return (
    <button
      type="button"
      onClick={toggleViewer}
      disabled={!hasDocument}
      title={
        hasDocument
          ? "Toggle PDF viewer"
          : "No document open yet"
      }
      className="
        flex items-center justify-center
        rounded p-1.5
        text-muted-foreground
        transition-colors
        hover:bg-muted
        hover:text-foreground
        disabled:cursor-not-allowed
        disabled:opacity-30
      "
    >
      <SplitPanelToggleIcon
        isActive={isOpen}
      />
    </button>
  );
}