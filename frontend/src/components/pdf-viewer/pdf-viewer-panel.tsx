"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Document, Page, pdfjs } from "react-pdf";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";
import { chatService } from "@/services/chat.service";
import {
  ArrowBackIcon,
  CloseIcon,
  ProgressActivityIcon,
  WarningIcon,
} from "@/components/shared/icons";
pdfjs.GlobalWorkerOptions.workerSrc =
  "https://unpkg.com/pdfjs-dist@4.8.69/build/pdf.worker.min.mjs";
// Core viewer render canvas + text layer được import dynamic để tránh SSR window mismatch
const PdfViewerCore = dynamic(
  () => import("@/components/pdf-viewer/pdf-viewer-core-client"),
  {
    ssr: false,
    loading: () => null,
  }
);

// Cache URL tài liệu để tránh fetch lặp lại khi toggle viewer
const urlCache = new Map<number, string>();

export function PdfViewerPanel() {
  const {
    isOpen,
    documentId,
    documentTitle,
    currentPage,
    targetSnippet,
    closeViewer,
    setCurrentPage,
    isThumbnailOpen,
    toggleThumbnail,
  } = usePdfViewer();

  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState(0);

  // Fetch URL tài liệu từ backend hoặc lấy từ cache
  useEffect(() => {
    if (!documentId) return;

    const cached = urlCache.get(documentId);

    if (cached) {
      setFileUrl(cached);
      setError(null);
      return;
    }

    setFileUrl(null);
    setError(null);

    chatService
      .getDocumentFileUrl(documentId)
      .then((url) => {
        urlCache.set(documentId, url);
        setFileUrl(url);
      })
      .catch(() => {
        setError("Failed to load document.");
      });
  }, [documentId]);

  if (!isOpen) return null;

  return (
    <div className="flex h-full w-full flex-col border-l border-border bg-white">
      {/* 1. HEADER DÙNG CHUNG TOÀN BỘ PANEL */}
      <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-2">
        <button
          onClick={closeViewer}
          className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowBackIcon size={18} />
          Hide viewer
        </button>

        <p className="flex-1 truncate px-3 text-center text-sm font-medium">
          {documentTitle}
        </p>

        <div className="flex items-center gap-2">
          {/* Nút Ẩn/Hiện Sidebar Thumbnail trên Header chung */}
          {numPages > 0 && (
            <button
              onClick={toggleThumbnail}
              className="rounded border border-border px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              {isThumbnailOpen ? "Hide Thumbnails" : "Show Thumbnails"}
            </button>
          )}

          <button
            onClick={closeViewer}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <CloseIcon size={18} />
          </button>
        </div>
      </div>

      {/* 2. BODY KHUNG CHỨA CẢ VIEWER VÀ SIDEBAR THUMBNAIL */}
      <div className="flex flex-1 overflow-hidden">
        {/* State Báo Lỗi */}
        {error && (
          <div className="flex h-full w-full items-center justify-center gap-2 text-sm text-destructive">
            <WarningIcon size={18} />
            {error}
          </div>
        )}

        {/* State Đang Tải */}
        {!error && !fileUrl && (
          <div className="flex h-full w-full items-center justify-center gap-2 text-sm text-muted-foreground">
            <ProgressActivityIcon size={18} className="animate-spin" />
            Loading document...
          </div>
        )}

        {/* State Đã Tải Xong Document */}
        {fileUrl && documentId && (
          <div className="flex h-full w-full overflow-hidden">
            {/* --- VIEWER CHÍNH --- */}
            {/* min-w-0 đảm bảo flex-1 co giãn full chiều rộng khi Sidebar ẩn */}
            <div className="flex-1 min-w-0 h-full overflow-hidden">
              <PdfViewerCore
                key={documentId}
                fileUrl={fileUrl}
                initialPage={currentPage}
                targetSnippet={targetSnippet}
                onPageCountChange={setNumPages}
                onPageChange={setCurrentPage}
              />
            </div>

            {/* --- SIDEBAR THUMBNAIL LIỀN KHỐI --- */}
            {/* Thu gọn chiều rộng về 0 bằng CSS transition thay vì unmount DOM */}
            <div
              className={`h-full transition-all duration-200 ease-in-out ${
                isThumbnailOpen && numPages > 0
                  ? "w-48 border-l border-border opacity-100"
                  : "w-0 opacity-0 border-none overflow-hidden pointer-events-none"
              }`}
            >
              <div className="flex h-full w-48 flex-col bg-white">
                <div className="flex shrink-0 items-center justify-between border-b border-border p-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    Pages ({numPages})
                  </span>
                  <button
                    onClick={toggleThumbnail}
                    className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                  >
                    Hide
                  </button>
                </div>

                <div className="flex-1 overflow-auto p-2">
                  <Document file={fileUrl}>
                    {Array.from({ length: numPages }, (_, i) => i + 1).map(
                      (page) => (
                        <button
                          key={page}
                          onClick={() => setCurrentPage(page)}
                          className={`mb-3 block w-full rounded border p-1 transition-colors ${
                            currentPage === page
                              ? "border-blue-500 ring-2 ring-blue-500/20"
                              : "border-border hover:border-gray-400"
                          }`}
                        >
                          <Page
                            pageNumber={page}
                            width={130}
                            renderTextLayer={false}
                            renderAnnotationLayer={false}
                          />
                          <div className="mt-1 text-center text-xs text-muted-foreground">
                            {page}
                          </div>
                        </button>
                      )
                    )}
                  </Document>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}