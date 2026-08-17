"use client";

import "@/lib/suppress-pdf-warnings";

import React, { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { Document, Page, pdfjs } from "react-pdf";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";
import { chatService } from "@/services/chat.service";
import {
  Icon,
  ProgressActivityIcon,
  WarningIcon,
} from "@/components/shared/icons";

pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

const PdfViewerCore = dynamic(
  () =>
    import("@/components/document-viewer/pdf-viewer-core").then(
      (module) => module.PdfViewerCore
    ),
  { ssr: false, loading: () => null }
);

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.15;

function isExpectedRenderCancellation(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false;
  const candidate = error as { name?: string; message?: string };
  return (
    candidate.name === "AbortException" ||
    /textlayer task cancelled|rendering cancelled|cancelled/i.test(
      candidate.message ?? ""
    )
  );
}

function handlePdfRenderError(error: Error): void {
  if (!isExpectedRenderCancellation(error)) {
    console.error("PDF thumbnail render error:", error);
  }
}

const PdfThumbnail = React.memo(function PdfThumbnail({
  pageNumber,
}: {
  pageNumber: number;
}) {
  return (
    <Page
      pageNumber={pageNumber}
      width={560}
      scale={0.25}
      devicePixelRatio={1}
      renderTextLayer={false}
      renderAnnotationLayer={false}
      loading={null}
      className="max-w-full overflow-hidden [&_canvas]:!h-auto [&_canvas]:!max-w-full"
      onRenderError={handlePdfRenderError}
    />
  );
});

const LazyThumbnailSlot = React.memo(function LazyThumbnailSlot({
  page,
  active,
  onSelect,
  registerButton,
}: {
  page: number;
  active: boolean;
  onSelect: (page: number) => void;
  registerButton: (page: number, element: HTMLButtonElement | null) => void;
}) {
  const slotRef = useRef<HTMLButtonElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const setButtonRef = useCallback(
    (element: HTMLButtonElement | null) => {
      slotRef.current = element;
      registerButton(page, element);
    },
    [page, registerButton]
  );

  useEffect(() => {
    const element = slotRef.current;
    const root = element?.closest("[data-thumbnail-scroll]");
    if (!element || !(root instanceof HTMLElement)) return;
    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry.isIntersecting),
      { root, rootMargin: "320px 0px" }
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <button
      ref={setButtonRef}
      type="button"
      onClick={() => onSelect(page)}
      aria-label={`Go to page ${page}`}
      className={`mb-3 block w-full overflow-hidden rounded-md border p-1.5 transition-colors ${
        active
          ? "border-primary/60 bg-primary/5 ring-2 ring-primary/10"
          : "border-border/70 bg-card hover:border-primary/35"
      }`}
    >
      <div className="mx-auto flex aspect-[1/1.414] w-[140px] max-w-full items-center justify-center overflow-hidden rounded-sm bg-secondary/30">
        {isVisible ? (
          <PdfThumbnail pageNumber={page} />
        ) : (
          <span className="text-xs font-medium tabular-nums text-muted-foreground/70">
            {page}
          </span>
        )}
      </div>
      <span className="mt-1.5 block text-center text-[10px] tabular-nums text-muted-foreground">
        {page}
      </span>
    </button>
  );
});

function ToolbarButton({
  label,
  disabled,
  active,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={`flex h-8 w-8 items-center justify-center rounded-md transition-colors disabled:pointer-events-none disabled:opacity-35 ${
        active
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-secondary hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}

export function PdfViewerPanel({
  mode = "split",
  onClose,
}: {
  mode?: "split" | "full";
  onClose?: () => void;
}) {
  const {
    documentId,
    documentTitle,
    currentPage,
    targetSnippet,
    closeViewer,
    setCurrentPage,
    isThumbnailOpen,
    toggleThumbnail,
  } = usePdfViewer();
  const handleClose = onClose ?? closeViewer;

  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [navigationRequestId, setNavigationRequestId] = useState(0);
  const [pageInput, setPageInput] = useState(String(currentPage));
  const isEditingPageRef = useRef(false);
  const thumbnailRefs = useRef<Map<number, HTMLButtonElement>>(new Map());
  const thumbnailScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!documentId) return;
    let active = true;
    setFileUrl(null);
    setError(null);
    setNumPages(0);
    setZoom(1);

    chatService
      .getDocumentFileUrl(documentId)
      .then((url) => {
        if (active) setFileUrl(url);
      })
      .catch(() => {
        if (active) setError("Failed to load document.");
      });

    return () => {
      active = false;
    };
  }, [documentId, loadAttempt]);

  useEffect(() => {
    if (!isThumbnailOpen) return;
    const container = thumbnailScrollRef.current;
    const thumbnail = thumbnailRefs.current.get(currentPage);
    if (!container || !thumbnail) return;

    const containerBounds = container.getBoundingClientRect();
    const thumbnailBounds = thumbnail.getBoundingClientRect();
    if (thumbnailBounds.top < containerBounds.top) {
      container.scrollTop -= containerBounds.top - thumbnailBounds.top;
    } else if (thumbnailBounds.bottom > containerBounds.bottom) {
      container.scrollTop += thumbnailBounds.bottom - containerBounds.bottom;
    }
  }, [currentPage, isThumbnailOpen]);

  useEffect(() => {
    if (!isEditingPageRef.current) setPageInput(String(currentPage));
  }, [currentPage]);

  const handlePdfLoadError = useCallback(() => {
    setError("The PDF could not be rendered.");
  }, []);
  const navigateToPage = useCallback(
    (page: number) => {
      setCurrentPage(page);
      setNavigationRequestId((requestId) => requestId + 1);
    },
    [setCurrentPage]
  );
  const registerThumbnailButton = useCallback(
    (page: number, element: HTMLButtonElement | null) => {
      if (element) thumbnailRefs.current.set(page, element);
      else thumbnailRefs.current.delete(page);
    },
    []
  );

  const commitPageInput = () => {
    const parsedPage = Number(pageInput);
    const nextPage = Math.min(
      Math.max(1, Number.isInteger(parsedPage) ? parsedPage : currentPage),
      Math.max(1, numPages)
    );
    setPageInput(String(nextPage));
    if (numPages > 0) navigateToPage(nextPage);
  };

  return (
    <div className={`flex h-full w-full flex-col bg-background ${mode === "split" ? "border-l border-border/70" : ""}`}>
      <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border/60 bg-card/70 px-3">
        <ToolbarButton label={mode === "full" ? "Back to Library" : "Hide PDF Viewer"} onClick={handleClose}>
          <Icon name={mode === "full" ? "arrow_back" : "visibility_off"} className="text-[18px]" />
        </ToolbarButton>

        <span className="mr-1 h-5 w-px bg-border/80" aria-hidden />

        <p
          className="min-w-0 flex-1 truncate font-heading text-xs font-semibold text-foreground"
          title={documentTitle ?? undefined}
        >
          {documentTitle}
        </p>

        <div className="flex shrink-0 items-center gap-0.5">
          <ToolbarButton
            label="Zoom out"
            disabled={zoom <= MIN_ZOOM}
            onClick={() => setZoom((value) => Math.max(MIN_ZOOM, value - ZOOM_STEP))}
          >
            <Icon name="zoom_out" className="text-[18px]" />
          </ToolbarButton>
          <ToolbarButton label="Reset zoom" onClick={() => setZoom(1)}>
            <Icon name="restart_alt" className="text-[18px]" />
          </ToolbarButton>
          <ToolbarButton
            label="Zoom in"
            disabled={zoom >= MAX_ZOOM}
            onClick={() => setZoom((value) => Math.min(MAX_ZOOM, value + ZOOM_STEP))}
          >
            <Icon name="zoom_in" className="text-[18px]" />
          </ToolbarButton>

          <div className="mx-1 flex h-8 items-center gap-1 rounded-md bg-secondary/70 px-1.5 text-[10px] tabular-nums text-muted-foreground">
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={numPages > 0 ? pageInput : ""}
              disabled={numPages === 0}
              aria-label="Page number"
              onFocus={() => {
                isEditingPageRef.current = true;
              }}
              onChange={(event) => {
                if (/^\d*$/.test(event.target.value)) setPageInput(event.target.value);
              }}
              onBlur={() => {
                isEditingPageRef.current = false;
                commitPageInput();
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") event.currentTarget.blur();
              }}
              className="h-6 w-8 rounded border border-border/80 bg-card px-1 text-center text-[10px] text-foreground outline-none focus:border-primary/60 focus:ring-2 focus:ring-primary/10 disabled:opacity-50"
            />
            <span aria-hidden>/</span>
            <span className="min-w-4 text-center">{numPages || "--"}</span>
          </div>

          <span className="mx-1 h-5 w-px bg-border/80" aria-hidden />

          <ToolbarButton
            label={isThumbnailOpen ? "Hide thumbnails" : "Show thumbnails"}
            active={isThumbnailOpen}
            disabled={numPages === 0}
            onClick={toggleThumbnail}
          >
            <Icon name="view_sidebar" className="text-[18px]" />
          </ToolbarButton>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        {error && (
          <div className="flex h-full w-full flex-col items-center justify-center gap-3 px-6 text-center text-sm text-destructive">
            <div className="flex items-center gap-2">
              <WarningIcon size={18} />
              {error}
            </div>
            <button
              type="button"
              onClick={() => setLoadAttempt((attempt) => attempt + 1)}
              className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-secondary"
            >
              Retry
            </button>
          </div>
        )}

        {!error && !fileUrl && (
          <div className="flex h-full w-full items-center justify-center gap-2 text-xs text-muted-foreground">
            <ProgressActivityIcon size={18} className="animate-spin" />
            Loading document...
          </div>
        )}

        {!error && fileUrl && documentId && (
          <div className="flex h-full min-w-0 flex-1 overflow-hidden">
            <aside
              aria-hidden={!isThumbnailOpen}
              className={`order-2 shrink-0 overflow-hidden border-l border-border/60 bg-card/45 transition-[width,opacity] duration-200 ${
                isThumbnailOpen && numPages > 0
                  ? "w-44 opacity-100"
                  : "pointer-events-none w-0 opacity-0"
              }`}
            >
              <div
                ref={thumbnailScrollRef}
                data-thumbnail-scroll
                className="h-full w-44 overflow-y-auto px-2 py-3"
              >
                {isThumbnailOpen && (
                  <Document file={fileUrl} loading={null}>
                    {Array.from({ length: numPages }, (_, index) => index + 1).map(
                      (page) => (
                        <LazyThumbnailSlot
                          key={page}
                          page={page}
                          active={currentPage === page}
                          onSelect={navigateToPage}
                          registerButton={registerThumbnailButton}
                        />
                      )
                    )}
                  </Document>
                )}
              </div>
            </aside>

            <main className="order-1 h-full min-w-0 flex-1 overflow-hidden">
              <PdfViewerCore
                key={documentId}
                fileUrl={fileUrl}
                initialPage={currentPage}
                targetSnippet={targetSnippet}
                zoom={zoom}
                navigationRequestId={navigationRequestId}
                onPageCountChange={setNumPages}
                onPageChange={setCurrentPage}
                onLoadError={handlePdfLoadError}
              />
            </main>
          </div>
        )}
      </div>
    </div>
  );
}
