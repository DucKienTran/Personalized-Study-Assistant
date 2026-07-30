"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";
import {
  getPrioritySequence,
  buildTextData,
  collectFreshSpans,
  findSnippet,
  applyLineMarker,
  getCachedTextData,
  setCachedTextData,
  CachedTextData,
} from "@/utils/highlight";

import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc =
  "https://unpkg.com/pdfjs-dist@4.8.69/build/pdf.worker.min.mjs";

export interface PdfViewerCoreProps {
  fileUrl: string;
  initialPage: number;
  targetSnippet: string | null;
  onPageCountChange?: (count: number) => void;
  onPageChange?: (page: number) => void;
}

// Trợ lý chờ DOM TextLayer render xong các thẻ span
async function ensureSpansReady(
  layerElement: HTMLElement,
  maxWaitMs = 800
): Promise<boolean> {
  const startTime = Date.now();
  while (Date.now() - startTime < maxWaitMs) {
    if (layerElement.querySelectorAll("span").length > 0) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 30));
  }
  return layerElement.querySelectorAll("span").length > 0;
}

export function PdfViewerCore({
  fileUrl,
  initialPage,
  targetSnippet,
  onPageCountChange,
  onPageChange,
}: PdfViewerCoreProps) {
  const { highlightRequestId } = usePdfViewer();

  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [zoom, setZoom] = useState(1);
  const [pagesToRender, setPagesToRender] = useState<number[]>([]);

  // Ref container dành riêng cho việc scroll nội bộ panel PDF
  const pdfScrollRef = useRef<HTMLDivElement>(null);

  // Token & Guard Refs
  const searchSessionIdRef = useRef<number>(0);
  const searchFoundRef = useRef<boolean>(false);
  const prioritySequenceRef = useRef<number[]>([]);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Synchronize currentPage với initialPage
  useEffect(() => {
    setCurrentPage(initialPage);
  }, [initialPage]);

  // Reset toàn bộ state & session khi đổi PDF file
  useEffect(() => {
    setNumPages(0);
    setPagesToRender([]);
    pageRefs.current.clear();
    searchFoundRef.current = false;
    searchSessionIdRef.current += 1; // Invalidate lập tức mọi async search/render callback dở dang của PDF cũ
  }, [fileUrl]);
  // Hàm xử lý search & highlight độc lập
  const processPageSearch = useCallback(
    async (pageNumber: number, sessionId: number) => {
      // 1. Race condition check: Bỏ qua nếu sessionId đã cũ
      if (sessionId !== searchSessionIdRef.current) return;

      // 2. Chặn duplicate highlight nếu đã tìm thấy
      if (searchFoundRef.current || !targetSnippet) return;

      const pageContainer = pageRefs.current.get(pageNumber);
      if (!pageContainer) return;

      const layerElement = pageContainer.querySelector(
        ".react-pdf__Page__textContent"
      ) as HTMLElement | null;

      if (!layerElement) return;

      // Chờ DOM render xong các thẻ <span> trước khi đọc text
      const isReady = await ensureSpansReady(layerElement);
      if (!isReady || sessionId !== searchSessionIdRef.current) return;

      const docKey = fileUrl;

      // 3. Đọc hoặc Build CachedTextData
      let textData: CachedTextData | undefined = getCachedTextData(
        docKey,
        pageNumber
      );

      if (!textData) {
        const built = buildTextData(layerElement, pageNumber);
        if (built) {
          textData = built;
          setCachedTextData(docKey, pageNumber, built);
        }
      }

      if (!textData) return;

      // 4. Tìm kiếm snippet
      const match = findSnippet(textData.normalizedText, targetSnippet);
      const sequence = prioritySequenceRef.current;
      const currentIndex = sequence.indexOf(pageNumber);

      // --- TRƯỜNG HỢP TÌM THẤY ---
      if (match && match.startNormIdx >= 0) {
        const freshSpans = collectFreshSpans(layerElement);

        const startOrig = textData.normToOrigMap[match.startNormIdx];
        const endOrig = textData.normToOrigMap[match.endNormIdx];

        const matchedSpan = freshSpans.find(
          (item) => item.endOrig > startOrig && item.startOrig <= endOrig
        );

        if (matchedSpan) {
          searchFoundRef.current = true;

          const marker = applyLineMarker(layerElement, matchedSpan);

          setCurrentPage(pageNumber);
          onPageChange?.(pageNumber);

          // SCROLL NỘI BỘ: Chỉ cuộn container pdfScrollRef, KHÔNG scroll window/chat
          requestAnimationFrame(() => {
            const container = pdfScrollRef.current;
            if (container && marker) {
              const containerRect = container.getBoundingClientRect();
              const markerRect = marker.getBoundingClientRect();

              const offset =
                markerRect.top -
                containerRect.top +
                container.scrollTop -
                container.clientHeight / 2;

              container.scrollTo({
                top: offset,
                behavior: "smooth",
              });
            }
          });

          // Filter background pages chính xác
          const remainingPages = sequence.filter(
            (p) => p >= 1 && p <= numPages && p !== pageNumber
          );
          setPagesToRender((prev) =>
            Array.from(new Set([...prev, ...remainingPages])).filter(
              (p) => p >= 1 && p <= numPages
            )
          );
          return;
        }
      }

      // --- TRƯỜNG HỢP CHƯA TÌM THẤY ---
      if (currentIndex !== -1 && currentIndex < sequence.length - 1) {
        const nextPage = sequence[currentIndex + 1];
        if (nextPage >= 1 && nextPage <= numPages) {
          setPagesToRender((prev) =>
            Array.from(new Set([...prev, nextPage])).filter(
              (p) => p >= 1 && p <= numPages
            )
          );
        }
      } else {
        searchFoundRef.current = true;
        setCurrentPage(initialPage);
      }
    },
    [fileUrl, targetSnippet, initialPage, numPages, onPageChange]
  );

  // Lifecycle quản lý Search Session
  useEffect(() => {
    if (!numPages || numPages < 1) return;

    const validInitial = Math.min(Math.max(1, initialPage), numPages);

    searchSessionIdRef.current += 1;
    const currentSession = searchSessionIdRef.current;
    searchFoundRef.current = false;

    if (!targetSnippet) {
      setPagesToRender([validInitial]);
      return;
    }

    const rawSequence = getPrioritySequence(validInitial, numPages, 5);
    const sequence = rawSequence.filter((p) => p >= 1 && p <= numPages);

    if (sequence.length === 0) {
      setPagesToRender([validInitial]);
      return;
    }

    prioritySequenceRef.current = sequence;
    const firstPage = sequence[0];

    setPagesToRender((prev) =>
      Array.from(new Set([...prev, firstPage])).filter(
        (p) => p >= 1 && p <= numPages
      )
    );

    const timer = setTimeout(() => {
      if (searchSessionIdRef.current === currentSession) {
        processPageSearch(firstPage, currentSession);
      }
    }, 50);

    return () => clearTimeout(timer);
  }, [initialPage, targetSnippet, highlightRequestId, numPages, processPageSearch]);

  const jumpToPage = useCallback(
    (page: number) => {
      if (!numPages || page < 1 || page > numPages) return;
      setCurrentPage(page);
      onPageChange?.(page);
      if (!pagesToRender.includes(page)) {
        setPagesToRender((prev) =>
          Array.from(new Set([...prev, page])).filter(
            (p) => p >= 1 && p <= numPages
          )
        );
      }
    },
    [numPages, onPageChange, pagesToRender]
  );

  const validPagesToRender = pagesToRender.filter(
    (p) => typeof p === "number" && p >= 1 && p <= numPages
  );

  return (
    <div className="flex h-full flex-col">
      {/* Control Bar */}
      <div className="flex shrink-0 items-center justify-center gap-2 border-b bg-white p-2">
        <button
          disabled={currentPage <= 1}
          onClick={() => jumpToPage(currentPage - 1)}
          className="rounded border px-2 py-1 text-xs disabled:opacity-40 hover:bg-muted"
        >
          Prev
        </button>

        <input
          type="number"
          value={currentPage}
          onChange={(e) => setCurrentPage(Number(e.target.value))}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              jumpToPage(Number(e.currentTarget.value));
            }
          }}
          className="w-12 border text-center text-xs"
        />

        <span className="text-xs">/ {numPages}</span>

        <button
          disabled={currentPage >= numPages}
          onClick={() => jumpToPage(currentPage + 1)}
          className="rounded border px-2 py-1 text-xs disabled:opacity-40 hover:bg-muted"
        >
          Next
        </button>

        <div className="ml-4 flex items-center gap-1">
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}
            className="rounded border px-2 py-1 text-xs hover:bg-muted"
          >
            -
          </button>
          <span className="text-xs">{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom((z) => Math.min(2.5, z + 0.1))}
            className="rounded border px-2 py-1 text-xs hover:bg-muted"
          >
            +
          </button>
        </div>
      </div>

      {/* Main Page Container với ref cuộn nội bộ */}
      <div
        ref={pdfScrollRef}
        className="flex-1 overflow-auto bg-gray-100 p-4"
      >
        <Document
          file={fileUrl}
          onLoadSuccess={({ numPages: count }) => {
            setNumPages(count);
            onPageCountChange?.(count);
          }}
        >
          {numPages > 0 &&
            validPagesToRender.map((pageNo) => {
              const isActive = pageNo === currentPage;
              return (
                <div
                  key={`page-container-${pageNo}`}
                  ref={(el) => {
                    if (el) pageRefs.current.set(pageNo, el);
                    else pageRefs.current.delete(pageNo);
                  }}
                  className={`mx-auto w-fit shadow-md transition-opacity duration-150 ${
                    isActive
                      ? "relative mb-6 block opacity-100"
                      : "absolute top-0 left-1/2 -translate-x-1/2 opacity-0 pointer-events-none invisible"
                  }`}
                >
                  <Page
                    key={`page-${pageNo}-${zoom}`}
                    pageNumber={pageNo}
                    scale={zoom}
                    renderTextLayer
                    renderAnnotationLayer={false}
                    onGetTextSuccess={() =>
                      processPageSearch(pageNo, searchSessionIdRef.current)
                    }
                    onRenderError={(error) => {
                      if (error.name !== "AbortException") {
                        console.error(error);
                      }
                    }}
                  />
                </div>
              );
            })}
        </Document>
      </div>
    </div>
  );
}