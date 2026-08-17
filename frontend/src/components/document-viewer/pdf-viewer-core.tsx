"use client";

import "@/lib/suppress-pdf-warnings";

import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Document, Page, pdfjs } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";
import {
  normalizeText,
} from "@/utils/highlight";

import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

const PAGE_GAP = 20;
const PAGE_OVERSCAN = 4;
const DEFAULT_PAGE_RATIO = 1.414;

export interface PdfViewerCoreProps {
  fileUrl: string;
  initialPage: number;
  targetSnippet: string | null;
  zoom: number;
  navigationRequestId: number;
  onPageCountChange?: (count: number) => void;
  onPageChange?: (page: number) => void;
  onLoadError?: (error: Error) => void;
}

interface PageMetric {
  page: number;
  top: number;
  height: number;
}

interface RenderWindow {
  start: number;
  end: number;
}

interface ProgrammaticNavigation {
  id: number;
  targetPage: number;
}

interface TextItemEntry {
  itemIndex: number;
  str: string;
  startOrig: number;
  endOrig: number;
}

interface PageTextData {
  page: number;
  normalizedText: string;
  normToOrigMap: number[];
  entries: TextItemEntry[];
}

interface TextItemHighlight {
  start: number;
  end: number;
}

interface HighlightPlan {
  page: number;
  ranges: Readonly<Record<number, TextItemHighlight>>;
  requiredPages: number[];
  requestId: number;
}

function buildPageTextData(
  page: number,
  items: readonly unknown[]
): PageTextData {
  const entries: TextItemEntry[] = [];
  let originalText = "";
  items.forEach((item, itemIndex) => {
    if (
      typeof item !== "object" ||
      item === null ||
      !("str" in item) ||
      typeof item.str !== "string"
    ) return;
    if (
      originalText.length > 0 &&
      !/\s$/.test(originalText) &&
      !/^\s/.test(item.str)
    ) {
      originalText += " ";
    }
    const startOrig = originalText.length;
    originalText += item.str;
    entries.push({
      itemIndex,
      str: item.str,
      startOrig,
      endOrig: originalText.length,
    });
  });

  let rawNormalized = "";
  const rawMap: number[] = [];
  for (let originalIndex = 0; originalIndex < originalText.length; originalIndex += 1) {
    const character = originalText[originalIndex];
    let normalizedCharacter = character.normalize("NFKC").toLowerCase();
    if (/[\r\n\t]/.test(normalizedCharacter)) normalizedCharacter = " ";
    else if (/[‐-‒–—]/.test(normalizedCharacter)) normalizedCharacter = "-";
    else if (/[“”]/.test(normalizedCharacter)) normalizedCharacter = '"';
    else if (/[‘’]/.test(normalizedCharacter)) normalizedCharacter = "'";
    for (const normalizedPart of normalizedCharacter) {
      rawNormalized += normalizedPart;
      rawMap.push(originalIndex);
    }
  }

  let normalizedText = "";
  const normToOrigMap: number[] = [];
  let inSpace = false;
  for (let index = 0; index < rawNormalized.length; index += 1) {
    const character = rawNormalized[index];
    if (character === " ") {
      if (inSpace) continue;
      inSpace = true;
    } else {
      inSpace = false;
    }
    normalizedText += character;
    normToOrigMap.push(rawMap[index]);
  }

  return { page, normalizedText, normToOrigMap, entries };
}

function createItemRanges(
  textData: PageTextData,
  startNormIdx: number,
  endNormIdx: number
): Readonly<Record<number, TextItemHighlight>> | null {
  if (startNormIdx < 0 || textData.normToOrigMap.length === 0) return null;
  const startOrig = textData.normToOrigMap[startNormIdx];
  const endOrig = textData.normToOrigMap[
    Math.min(endNormIdx, textData.normToOrigMap.length - 1)
  ];
  const ranges: Record<number, TextItemHighlight> = {};
  textData.entries.forEach((entry) => {
    if (entry.endOrig <= startOrig || entry.startOrig > endOrig) return;
    ranges[entry.itemIndex] = {
      start: Math.max(0, startOrig - entry.startOrig),
      end: Math.min(entry.str.length, endOrig - entry.startOrig + 1),
    };
  });
  return Object.keys(ranges).length > 0 ? ranges : null;
}

function buildMeaningfulPhrases(value: string): string[] {
  const phrases = new Set<string>();
  value
    .split(/[.!?;:\r\n]+/)
    .map(normalizeText)
    .filter((phrase) => phrase.length >= 20)
    .forEach((phrase) => phrases.add(phrase));

  const words = normalizeText(value).split(" ").filter(Boolean);
  const windowSize = 6;
  for (let start = 0; start < words.length; start += 2) {
    const phrase = words.slice(start, start + windowSize).join(" ");
    if (phrase.length >= 20) phrases.add(phrase);
  }

  return Array.from(phrases).sort((left, right) => right.length - left.length);
}

function compactTextWithMap(value: string): {
  text: string;
  compactToSourceMap: number[];
} {
  let text = "";
  const compactToSourceMap: number[] = [];
  Array.from(value).forEach((character, sourceIndex) => {
    if (!/[\p{L}\p{N}]/u.test(character)) return;
    text += character;
    compactToSourceMap.push(sourceIndex);
  });
  return { text, compactToSourceMap };
}

function createPartialItemRanges(
  textData: PageTextData,
  phrases: string[]
): Readonly<Record<number, TextItemHighlight>> | null {
  const mergedRanges: Record<number, TextItemHighlight> = {};
  let matchedPhrases = 0;
  const compactPage = compactTextWithMap(textData.normalizedText);

  for (const phrase of phrases) {
    let matchStart = textData.normalizedText.indexOf(phrase);
    let matchEnd = matchStart + phrase.length - 1;
    if (matchStart < 0) {
      const compactPhrase = compactTextWithMap(phrase).text;
      if (compactPhrase.length < 15) continue;
      const compactIndex = compactPage.text.indexOf(compactPhrase);
      if (compactIndex < 0) continue;
      matchStart = compactPage.compactToSourceMap[compactIndex];
      matchEnd = compactPage.compactToSourceMap[
        compactIndex + compactPhrase.length - 1
      ];
    }
    const ranges = createItemRanges(
      textData,
      matchStart,
      matchEnd
    );
    if (!ranges) continue;

    Object.entries(ranges).forEach(([itemIndex, range]) => {
      const existing = mergedRanges[Number(itemIndex)];
      mergedRanges[Number(itemIndex)] = existing
        ? {
            start: Math.min(existing.start, range.start),
            end: Math.max(existing.end, range.end),
          }
        : range;
    });
    matchedPhrases += 1;
    if (matchedPhrases >= 4) break;
  }

  return matchedPhrases > 0 ? mergedRanges : null;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function sameWindow(left: RenderWindow, right: RenderWindow): boolean {
  return left.start === right.start && left.end === right.end;
}

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
    console.error("PDF render error:", error);
  }
}

type PageLoadSuccess = NonNullable<
  React.ComponentProps<typeof Page>["onLoadSuccess"]
>;
type CustomTextRenderer = NonNullable<
  React.ComponentProps<typeof Page>["customTextRenderer"]
>;

const VirtualPdfPage = React.memo(function VirtualPdfPage({
  pageNumber,
  width,
  highlightRanges,
  onRatioChange,
  onTextLayerReady,
  onTextLayerUnmount,
}: {
  pageNumber: number;
  width: number;
  highlightRanges?: Readonly<Record<number, TextItemHighlight>>;
  onRatioChange: (page: number, ratio: number) => void;
  onTextLayerReady: (page: number) => void;
  onTextLayerUnmount: (page: number) => void;
}) {
  const handleLoadSuccess = useCallback<PageLoadSuccess>(
    (loadedPage) => {
      onRatioChange(
        pageNumber,
        loadedPage.originalHeight / loadedPage.originalWidth
      );
    },
    [onRatioChange, pageNumber]
  );
  const handleTextLayerSuccess = useCallback(() => {
    onTextLayerReady(pageNumber);
  }, [onTextLayerReady, pageNumber]);
  const customTextRenderer = useCallback<CustomTextRenderer>(
    ({ str, itemIndex }) => {
      const range = highlightRanges?.[itemIndex];
      if (!range) return escapeHtml(str);
      return `${escapeHtml(str.slice(0, range.start))}<mark class="pdf-citation-highlight">${escapeHtml(str.slice(range.start, range.end))}</mark>${escapeHtml(str.slice(range.end))}`;
    },
    [highlightRanges]
  );

  useEffect(
    () => () => {
      onTextLayerUnmount(pageNumber);
    },
    [onTextLayerUnmount, pageNumber]
  );

  return (
    <Page
      pageNumber={pageNumber}
      width={width}
      renderTextLayer
      customTextRenderer={highlightRanges ? customTextRenderer : undefined}
      renderAnnotationLayer={false}
      loading={null}
      onLoadSuccess={handleLoadSuccess}
      onRenderTextLayerSuccess={handleTextLayerSuccess}
      onRenderTextLayerError={handlePdfRenderError}
      onRenderError={handlePdfRenderError}
    />
  );
});

export function PdfViewerCore({
  fileUrl,
  initialPage,
  targetSnippet,
  zoom,
  navigationRequestId,
  onPageCountChange,
  onPageChange,
  onLoadError,
}: PdfViewerCoreProps) {
  const { highlightRequestId } = usePdfViewer();
  const [numPages, setNumPages] = useState(0);
  const [containerWidth, setContainerWidth] = useState(480);
  const [defaultPageRatio, setDefaultPageRatio] = useState(DEFAULT_PAGE_RATIO);
  const [pageRatios, setPageRatios] = useState<Record<number, number>>({});
  const [renderWindow, setRenderWindow] = useState<RenderWindow>({
    start: Math.max(1, initialPage - PAGE_OVERSCAN),
    end: initialPage + PAGE_OVERSCAN,
  });
  const [forcedPages, setForcedPages] = useState<Set<number>>(new Set());
  const [highlightPlan, setHighlightPlan] = useState<HighlightPlan | null>(null);

  const pdfScrollRef = useRef<HTMLDivElement>(null);
  const pdfDocumentRef = useRef<PDFDocumentProxy | null>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const currentPageRef = useRef(initialPage);
  const initialPageRef = useRef(initialPage);
  const handledNavigationRequestRef = useRef(0);
  const scrollFrameRef = useRef<number | null>(null);
  const navigationFrameRef = useRef<number | null>(null);
  const navigationSequenceRef = useRef(0);
  const activeNavigationRef = useRef<ProgrammaticNavigation | null>(null);
  const pageRatiosRef = useRef<Record<number, number>>({});
  const previousPageMetricsRef = useRef<PageMetric[]>([]);
  const searchSessionRef = useRef(0);
  const citationTargetPageRef = useRef(initialPage);
  const pageTextCacheRef = useRef<Map<number, PageTextData>>(new Map());
  const renderedTextPagesRef = useRef<Set<number>>(new Set());
  const highlightPlanRef = useRef<HighlightPlan | null>(null);
  const pendingHighlightPlanRef = useRef<HighlightPlan | null>(null);
  const scrolledHighlightRequestRef = useRef<number | null>(null);
  initialPageRef.current = initialPage;

  const pageWidth = Math.max(
    240,
    Math.min(760, Math.max(0, containerWidth - 48)) * zoom
  );

  const pageMetrics = useMemo(() => {
    let top = 0;
    return Array.from({ length: numPages }, (_, index): PageMetric => {
      const page = index + 1;
      const height = pageWidth * (pageRatios[page] ?? defaultPageRatio);
      const metric = { page, top, height };
      top += height + PAGE_GAP;
      return metric;
    });
  }, [defaultPageRatio, numPages, pageRatios, pageWidth]);

  const updateViewport = useCallback(() => {
    const container = pdfScrollRef.current;
    if (
      !container ||
      pageMetrics.length === 0 ||
      activeNavigationRef.current !== null
    ) return;

    const viewportTop = container.scrollTop;
    const viewportBottom = viewportTop + container.clientHeight;
    let low = 0;
    let high = pageMetrics.length - 1;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      const metric = pageMetrics[middle];
      if (metric.top + metric.height < viewportTop) low = middle + 1;
      else high = middle;
    }
    const firstVisible = low;

    let lastVisible = firstVisible;
    let majorityPage = pageMetrics[firstVisible].page;
    let largestOverlap = 0;
    while (
      lastVisible < pageMetrics.length &&
      pageMetrics[lastVisible].top <= viewportBottom
    ) {
      const metric = pageMetrics[lastVisible];
      const overlap = Math.max(
        0,
        Math.min(metric.top + metric.height, viewportBottom) -
          Math.max(metric.top, viewportTop)
      );
      if (overlap > largestOverlap) {
        largestOverlap = overlap;
        majorityPage = metric.page;
      }
      lastVisible += 1;
    }

    const nextWindow = {
      start: Math.max(1, pageMetrics[firstVisible].page - PAGE_OVERSCAN),
      end: Math.min(
        numPages,
        pageMetrics[Math.max(firstVisible, lastVisible - 1)].page + PAGE_OVERSCAN
      ),
    };
    setRenderWindow((current) =>
      sameWindow(current, nextWindow) ? current : nextWindow
    );

    if (majorityPage !== currentPageRef.current) {
      currentPageRef.current = majorityPage;
      onPageChange?.(majorityPage);
    }
  }, [numPages, onPageChange, pageMetrics]);

  const scheduleViewportUpdate = useCallback(() => {
    if (scrollFrameRef.current !== null) return;
    scrollFrameRef.current = window.requestAnimationFrame(() => {
      scrollFrameRef.current = null;
      updateViewport();
    });
  }, [updateViewport]);

  const settleProgrammaticNavigation = useCallback(() => {
    const navigation = activeNavigationRef.current;
    const container = pdfScrollRef.current;
    const target = navigation
      ? pageRefs.current.get(navigation.targetPage)
      : null;
    if (!navigation || !container || !target) return;

    const containerTop = container.getBoundingClientRect().top;
    const targetTop = target.getBoundingClientRect().top;
    const paddingTop = Number.parseFloat(window.getComputedStyle(container).paddingTop) || 0;
    const distance = targetTop - containerTop - paddingTop;

    if (Math.abs(distance) > 1) {
      container.scrollTo({ top: container.scrollTop + distance, behavior: "auto" });
      navigationFrameRef.current = window.requestAnimationFrame(() => {
        navigationFrameRef.current = null;
        if (activeNavigationRef.current?.id === navigation.id) {
          settleProgrammaticNavigation();
        }
      });
      return;
    }

    // A measured page ratio means the real page has replaced its placeholder.
    if (pageRatiosRef.current[navigation.targetPage] !== undefined) {
      activeNavigationRef.current = null;
      updateViewport();
    }
  }, [updateViewport]);

  const scheduleNavigationSettlement = useCallback(() => {
    if (navigationFrameRef.current !== null) return;
    navigationFrameRef.current = window.requestAnimationFrame(() => {
      navigationFrameRef.current = null;
      settleProgrammaticNavigation();
    });
  }, [settleProgrammaticNavigation]);

  const scrollToPage = useCallback(
    (page: number) => {
      if (!numPages) return;
      const validPage = Math.min(Math.max(1, page), numPages);
      const request = {
        id: ++navigationSequenceRef.current,
        targetPage: validPage,
      };
      activeNavigationRef.current = request;
      currentPageRef.current = validPage;
      onPageChange?.(validPage);
      setRenderWindow({
        start: Math.max(1, validPage - PAGE_OVERSCAN),
        end: Math.min(numPages, validPage + PAGE_OVERSCAN),
      });
      scheduleNavigationSettlement();
    },
    [numPages, onPageChange, scheduleNavigationSettlement]
  );

  const cancelProgrammaticNavigation = useCallback(() => {
    if (activeNavigationRef.current === null) return;
    activeNavigationRef.current = null;
    navigationSequenceRef.current += 1;
    if (navigationFrameRef.current !== null) {
      window.cancelAnimationFrame(navigationFrameRef.current);
      navigationFrameRef.current = null;
    }
    scheduleViewportUpdate();
  }, [scheduleViewportUpdate]);

  useEffect(() => {
    const container = pdfScrollRef.current;
    if (!container) return;
    let resizeFrame: number | null = null;
    const observer = new ResizeObserver(([entry]) => {
      if (resizeFrame !== null) window.cancelAnimationFrame(resizeFrame);
      resizeFrame = window.requestAnimationFrame(() => {
        resizeFrame = null;
        setContainerWidth(entry.contentRect.width);
      });
    });
    observer.observe(container);
    return () => {
      observer.disconnect();
      if (resizeFrame !== null) window.cancelAnimationFrame(resizeFrame);
    };
  }, []);

  useEffect(() => {
    return () => {
      if (scrollFrameRef.current !== null) {
        window.cancelAnimationFrame(scrollFrameRef.current);
      }
      if (navigationFrameRef.current !== null) {
        window.cancelAnimationFrame(navigationFrameRef.current);
      }
    };
  }, []);

  useEffect(() => {
    setNumPages(0);
    setDefaultPageRatio(DEFAULT_PAGE_RATIO);
    setPageRatios({});
    pageRatiosRef.current = {};
    setForcedPages(new Set());
    setHighlightPlan(null);
    highlightPlanRef.current = null;
    pendingHighlightPlanRef.current = null;
    pdfDocumentRef.current = null;
    pageRefs.current.clear();
    pageTextCacheRef.current.clear();
    renderedTextPagesRef.current.clear();
    currentPageRef.current = initialPage;
    activeNavigationRef.current = null;
    previousPageMetricsRef.current = [];
    searchSessionRef.current += 1;
  }, [fileUrl]);

  useEffect(() => {
    if (
      !numPages ||
      targetSnippet ||
      initialPage === currentPageRef.current
    ) return;
    currentPageRef.current = Math.min(Math.max(1, initialPage), numPages);
    scrollToPage(currentPageRef.current);
  }, [initialPage, numPages, scrollToPage, targetSnippet]);

  useEffect(() => {
    if (
      !numPages ||
      navigationRequestId === 0 ||
      handledNavigationRequestRef.current === navigationRequestId
    ) return;
    handledNavigationRequestRef.current = navigationRequestId;
    currentPageRef.current = Math.min(Math.max(1, initialPage), numPages);
    scrollToPage(currentPageRef.current);
  }, [initialPage, navigationRequestId, numPages, scrollToPage]);

  useLayoutEffect(() => {
    const container = pdfScrollRef.current;
    const previousMetrics = previousPageMetricsRef.current;
    previousPageMetricsRef.current = pageMetrics;
    if (!container || previousMetrics.length === 0 || pageMetrics.length === 0) return;

    if (activeNavigationRef.current !== null) {
      scheduleNavigationSettlement();
      return;
    }

    const previousTop = container.scrollTop;
    const previousMetric =
      previousMetrics.find(
        (metric) => previousTop >= metric.top && previousTop < metric.top + metric.height + PAGE_GAP
      ) ?? previousMetrics[previousMetrics.length - 1];
    const nextMetric = pageMetrics[previousMetric.page - 1];
    if (!nextMetric) return;
    const progress = Math.min(
      1,
      Math.max(0, (previousTop - previousMetric.top) / Math.max(1, previousMetric.height))
    );
    container.scrollTop = nextMetric.top + nextMetric.height * progress;
  }, [pageMetrics, scheduleNavigationSettlement]);

  const handleTextLayerReady = useCallback(
    (pageNumber: number) => {
      renderedTextPagesRef.current.add(pageNumber);
      const pendingPlan = pendingHighlightPlanRef.current;
      if (pendingPlan?.page === pageNumber) {
        pendingHighlightPlanRef.current = null;
        highlightPlanRef.current = pendingPlan;
        setHighlightPlan(pendingPlan);
        return;
      }
      const plan = highlightPlanRef.current;
      if (
        !plan ||
        scrolledHighlightRequestRef.current === plan.requestId ||
        !plan.requiredPages.every((page) => renderedTextPagesRef.current.has(page))
      ) {
        return;
      }

      const highlightedElement = pageRefs.current
        .get(plan.page)
        ?.querySelector(".pdf-citation-highlight");
      if (!(highlightedElement instanceof HTMLElement)) return;

      scrolledHighlightRequestRef.current = plan.requestId;
      currentPageRef.current = plan.page;
      onPageChange?.(plan.page);
      highlightedElement.scrollIntoView({ behavior: "smooth", block: "center" });
    },
    [onPageChange]
  );

  const handleTextLayerUnmount = useCallback((pageNumber: number) => {
    renderedTextPagesRef.current.delete(pageNumber);
  }, []);

  const handlePageRatioChange = useCallback((page: number, ratio: number) => {
    pageRatiosRef.current[page] = ratio;
    setPageRatios((current) =>
      Math.abs((current[page] ?? 0) - ratio) < 0.001
        ? current
        : { ...current, [page]: ratio }
    );
    if (activeNavigationRef.current?.targetPage === page) {
      scheduleNavigationSettlement();
    }
  }, [scheduleNavigationSettlement]);

  const handleDocumentLoadSuccess = useCallback(
    async (pdf: Parameters<
      NonNullable<React.ComponentProps<typeof Document>["onLoadSuccess"]>
    >[0]) => {
      pdfDocumentRef.current = pdf;
      const validInitial = Math.min(
        Math.max(1, initialPageRef.current),
        pdf.numPages
      );
      try {
        const initialPdfPage = await pdf.getPage(validInitial);
        const viewport = initialPdfPage.getViewport({ scale: 1 });
        setDefaultPageRatio(viewport.height / viewport.width);
      } catch {
        setDefaultPageRatio(DEFAULT_PAGE_RATIO);
      }
      setNumPages(pdf.numPages);
      onPageCountChange?.(pdf.numPages);
      currentPageRef.current = validInitial;
      setRenderWindow({
        start: Math.max(1, validInitial - PAGE_OVERSCAN),
        end: Math.min(pdf.numPages, validInitial + PAGE_OVERSCAN),
      });
    },
    [onPageCountChange]
  );

  useEffect(() => {
    const pdf = pdfDocumentRef.current;
    if (!numPages || !pdf) return;
    const session = ++searchSessionRef.current;
    highlightPlanRef.current = null;
    pendingHighlightPlanRef.current = null;
    setHighlightPlan(null);
    scrolledHighlightRequestRef.current = null;
    const validInitial = Math.min(
      Math.max(1, initialPageRef.current),
      numPages
    );
    if (!targetSnippet) {
      setForcedPages(new Set());
      return;
    }

    const pages = [validInitial, validInitial - 1, validInitial - 2].filter(
      (page) => page >= 1
    );
    citationTargetPageRef.current = validInitial;

    const loadPageText = async (pageNumber: number) => {
      const cached = pageTextCacheRef.current.get(pageNumber);
      if (cached) return cached;
      const pdfPage = await pdf.getPage(pageNumber);
      const textContent = await pdfPage.getTextContent();
      const textData = buildPageTextData(pageNumber, textContent.items);
      pageTextCacheRef.current.set(pageNumber, textData);
      return textData;
    };

    const activateHighlight = (
      pageNumber: number,
      ranges: Readonly<Record<number, TextItemHighlight>>
    ) => {
      if (session !== searchSessionRef.current) return;
      const pagesToRender = [pageNumber - 1, pageNumber, pageNumber + 1].filter(
        (page) => page >= 1 && page <= numPages
      );
      const plan: HighlightPlan = {
        page: pageNumber,
        ranges,
        requiredPages: [pageNumber],
        requestId: highlightRequestId,
      };
      setForcedPages(new Set(pagesToRender));
      setRenderWindow({
        start: Math.max(1, pageNumber - PAGE_OVERSCAN),
        end: Math.min(numPages, pageNumber + PAGE_OVERSCAN),
      });
      if (
        pageRefs.current
          .get(pageNumber)
          ?.querySelector(".react-pdf__Page") &&
        !renderedTextPagesRef.current.has(pageNumber)
      ) {
        pendingHighlightPlanRef.current = plan;
      } else {
        highlightPlanRef.current = plan;
        setHighlightPlan(plan);
      }
    };

    void (async () => {
      try {
        const normalizedSnippet = normalizeText(targetSnippet);
        if (!normalizedSnippet) {
          scrollToPage(citationTargetPageRef.current);
          return;
        }
        const meaningfulPhrases = [
          normalizedSnippet,
          ...buildMeaningfulPhrases(targetSnippet),
        ];
        for (const pageNumber of pages) {
          if (session !== searchSessionRef.current) return;
          const textData = await loadPageText(pageNumber);
          const exactIndex = textData.normalizedText.indexOf(normalizedSnippet);
          const ranges =
            exactIndex >= 0
              ? createItemRanges(
                  textData,
                  exactIndex,
                  exactIndex + normalizedSnippet.length - 1
                )
              : createPartialItemRanges(textData, meaningfulPhrases);
          if (ranges) {
            activateHighlight(pageNumber, ranges);
            return;
          }
        }

        if (session === searchSessionRef.current) {
          setForcedPages(new Set());
          scrollToPage(citationTargetPageRef.current);
        }
      } catch {
        if (session === searchSessionRef.current) {
          setForcedPages(new Set());
          scrollToPage(citationTargetPageRef.current);
        }
      }
    })();
  }, [highlightRequestId, numPages, scrollToPage, targetSnippet]);

  const renderedPages = useMemo(() => {
    const pages = new Set<number>();
    for (let page = renderWindow.start; page <= renderWindow.end; page += 1) {
      if (page >= 1 && page <= numPages) pages.add(page);
    }
    forcedPages.forEach((page) => pages.add(page));
    return pages;
  }, [forcedPages, numPages, renderWindow]);

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <div
        ref={pdfScrollRef}
        onScroll={activeNavigationRef.current ? scheduleNavigationSettlement : scheduleViewportUpdate}
        onWheel={cancelProgrammaticNavigation}
        onTouchStart={cancelProgrammaticNavigation}
        onPointerDown={cancelProgrammaticNavigation}
        className="flex-1 overflow-auto bg-secondary/25 px-6 py-5"
      >
        <Document
          file={fileUrl}
          loading={null}
          onLoadSuccess={handleDocumentLoadSuccess}
          onLoadError={onLoadError}
          onSourceError={onLoadError}
          className="mx-auto flex w-max min-w-full flex-col items-center"
        >
          {pageMetrics.map(({ page, height }) => {
            const shouldRender = renderedPages.has(page);
            return (
              <div
                key={page}
                ref={(element) => {
                  if (element) pageRefs.current.set(page, element);
                  else pageRefs.current.delete(page);
                }}
                data-page-number={page}
                className="relative shrink-0 overflow-hidden rounded-sm border border-border/70 bg-card shadow-[0_8px_24px_rgba(36,31,22,0.08)]"
                style={{
                  width: pageWidth,
                  height,
                  marginBottom: page === numPages ? 0 : PAGE_GAP,
                }}
              >
                {shouldRender ? (
                  <VirtualPdfPage
                    pageNumber={page}
                    width={pageWidth}
                    highlightRanges={
                      highlightPlan?.page === page
                        ? highlightPlan.ranges
                        : undefined
                    }
                    onRatioChange={handlePageRatioChange}
                    onTextLayerReady={handleTextLayerReady}
                    onTextLayerUnmount={handleTextLayerUnmount}
                  />
                ) : (
                  <div className="h-full w-full bg-card">
                    <div className="mx-auto mt-[12%] h-2 w-2/3 rounded bg-secondary/60" />
                    <div className="mx-auto mt-3 h-2 w-3/4 rounded bg-secondary/40" />
                    <div className="mx-auto mt-3 h-2 w-1/2 rounded bg-secondary/40" />
                  </div>
                )}
                <span className="pointer-events-none absolute bottom-2 right-3 rounded bg-background/85 px-1.5 py-0.5 text-[10px] text-muted-foreground shadow-xs">
                  {page}
                </span>
              </div>
            );
          })}
        </Document>
      </div>
    </div>
  );
}
