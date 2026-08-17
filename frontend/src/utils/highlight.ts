export interface CachedTextData {
  pageNumber: number;
  originalText: string;
  normalizedText: string;
  normToOrigMap: number[];
}

export interface FreshSpanInfo {
  span: HTMLSpanElement;
  startOrig: number;
  endOrig: number;
  rect: DOMRect;
  relativeTop: number;
  height: number;
}

export interface MatchResult {
  startNormIdx: number;
  endNormIdx: number;
  isExact: boolean;
  score: number;
}

// Memory cache lưu TextData thuần (Không cache DOM elements)
const textDataCache = new Map<string, CachedTextData>();

export function getCachedTextData(
  docKey: string,
  pageNumber: number
): CachedTextData | undefined {
  return textDataCache.get(`${docKey}_p${pageNumber}`);
}

export function setCachedTextData(
  docKey: string,
  pageNumber: number,
  data: CachedTextData
): void {
  textDataCache.set(`${docKey}_p${pageNumber}`, data);
}

export function clearTextDataCache(): void {
  textDataCache.clear();
}

/**
 * Sinh chuỗi trang ưu tiên dạng delta: target, -1, +1, -2, +2,...
 */
export function getPrioritySequence(
  targetPage: number,
  totalPages: number,
  radius = 5
): number[] {
  const sequence: number[] = [];
  const added = new Set<number>();

  const addPage = (p: number) => {
    if (p >= 1 && p <= totalPages && !added.has(p)) {
      added.add(p);
      sequence.push(p);
    }
  };

  addPage(targetPage);
  for (let i = 1; i <= radius; i++) {
    addPage(targetPage - i);
    addPage(targetPage + i);
  }

  return sequence;
}

/**
 * Chuẩn hóa chuỗi văn bản
 */
export function normalizeText(text: string): string {
  return text
    .normalize("NFKC")
    .replace(/^#{1,6}\s+/gm, " ")
    .replace(/\*\*([\s\S]*?)\*\*/g, "$1")
    .replace(/__([\s\S]*?)__/g, "$1")
    .replace(/\*([\s\S]*?)\*/g, "$1")
    .replace(/_([\s\S]*?)_/g, "$1")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/^[-*+]\s+/gm, " ")
    .replace(/\|/g, " ")
    .replace(/[\r\n\t]+/g, " ")
    .replace(/[‐-‒–—]/g, "-")
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

/**
 * Build dữ liệu Text & Index Mapping
 */
export function buildTextData(
  layerElement: HTMLElement,
  pageNumber: number
): CachedTextData | null {
  const spanElements = Array.from(
    layerElement.querySelectorAll("span")
  ) as HTMLSpanElement[];

  if (spanElements.length === 0) return null;

  let originalText = "";
  for (const span of spanElements) {
    originalText += span.textContent ?? "";
  }

  let rawNormalized = "";
  const rawNormToOrigMap: number[] = [];

  for (let origIdx = 0; origIdx < originalText.length; origIdx++) {
    const char = originalText[origIdx];
    let normChar = char.normalize("NFKC").toLowerCase();

    if (/[\r\n\t]/.test(normChar)) {
      normChar = " ";
    } else if (/[‐-‒–—]/.test(normChar)) {
      normChar = "-";
    } else if (/[“”]/.test(normChar)) {
      normChar = '"';
    } else if (/[‘’]/.test(normChar)) {
      normChar = "'";
    }

    for (let k = 0; k < normChar.length; k++) {
      rawNormalized += normChar[k];
      rawNormToOrigMap.push(origIdx);
    }
  }

  let normalizedText = "";
  const normToOrigMap: number[] = [];
  let inSpace = false;

  for (let i = 0; i < rawNormalized.length; i++) {
    const ch = rawNormalized[i];
    const origIdx = rawNormToOrigMap[i];

    if (ch === " ") {
      if (!inSpace) {
        normalizedText += " ";
        normToOrigMap.push(origIdx);
        inSpace = true;
      }
    } else {
      normalizedText += ch;
      normToOrigMap.push(origIdx);
      inSpace = false;
    }
  }

  return {
    pageNumber,
    originalText,
    normalizedText,
    normToOrigMap,
  };
}

/**
 * 1-PASS Collection: Lấy spans tươi kèm Geometry thật từ DOM hiện tại
 */
export function collectFreshSpans(layerElement: HTMLElement): FreshSpanInfo[] {
  const layerRect = layerElement.getBoundingClientRect();
  const spanElements = Array.from(
    layerElement.querySelectorAll("span")
  ) as HTMLSpanElement[];

  const spans: FreshSpanInfo[] = [];
  let currentOrigIdx = 0;

  for (const span of spanElements) {
    const text = span.textContent ?? "";
    if (!text) continue;

    const startOrig = currentOrigIdx;
    currentOrigIdx += text.length;
    const endOrig = currentOrigIdx;

    const rect = span.getBoundingClientRect();
    const relativeTop = rect.top - layerRect.top;
    const height = rect.height || 16;

    spans.push({
      span,
      startOrig,
      endOrig,
      rect,
      relativeTop,
      height,
    });
  }

  return spans;
}

/**
 * Levenshtein Similarity (0.0 -> 1.0)
 */
function getLevenshteinSimilarity(str1: string, str2: string): number {
  if (str1 === str2) return 1.0;
  if (!str1.length || !str2.length) return 0.0;

  const len1 = str1.length;
  const len2 = str2.length;
  const row: number[] = Array.from({ length: len2 + 1 }, (_, i) => i);

  for (let i = 1; i <= len1; i++) {
    let prev = i;
    for (let j = 1; j <= len2; j++) {
      const val =
        str1[i - 1] === str2[j - 1]
          ? row[j - 1]
          : Math.min(row[j - 1], prev, row[j]) + 1;
      row[j - 1] = prev;
      prev = val;
    }
    row[len2] = prev;
  }

  return 1.0 - row[len2] / Math.max(len1, len2);
}

/**
 * Tìm kiếm snippet
 */
export function findSnippet(
  normalizedText: string,
  targetSnippet: string
): MatchResult | null {
  const normSnippet = normalizeText(targetSnippet);
  if (!normSnippet) return null;

  // Exact Match
  const exactIndex = normalizedText.indexOf(normSnippet);
  if (exactIndex !== -1) {
    return {
      startNormIdx: exactIndex,
      endNormIdx: exactIndex + normSnippet.length - 1,
      isExact: true,
      score: 1.0,
    };
  }

  // Fuzzy Match
  const snippetLen = normSnippet.length;
  const textLen = normalizedText.length;
  if (textLen < Math.floor(snippetLen * 0.5)) return null;

  let bestScore = 0;
  let bestMatch: { start: number; end: number } | null = null;

  const windowSizes = [
    snippetLen,
    Math.floor(snippetLen * 0.95),
    Math.ceil(snippetLen * 1.05),
    Math.floor(snippetLen * 0.9),
    Math.ceil(snippetLen * 1.1),
  ];

  const step = Math.max(1, Math.floor(snippetLen / 10));

  for (const winSize of windowSizes) {
    if (winSize > textLen) continue;
    for (let i = 0; i <= textLen - winSize; i += step) {
      const candidate = normalizedText.slice(i, i + winSize);
      const score = getLevenshteinSimilarity(candidate, normSnippet);
      if (score > bestScore) {
        bestScore = score;
        bestMatch = { start: i, end: i + winSize - 1 };
      }
    }
  }

  if (bestMatch && bestScore >= 0.85) {
    return {
      startNormIdx: bestMatch.start,
      endNormIdx: bestMatch.end,
      isExact: false,
      score: bestScore,
    };
  }

  return {
    startNormIdx: -1,
    endNormIdx: -1,
    isExact: false,
    score: bestScore,
  };
}

/**
 * Xóa marker cũ
 */
export function clearHighlights(container: HTMLElement): void {
  const markers = container.querySelectorAll(
    "[data-rag-highlight='true'], .pdf-highlight-marker"
  );
  markers.forEach((el) => el.remove());
}

/**
 * Vẽ Marker FULL-WIDTH dựa trên Fresh Geometry
 */
export function applyLineMarker(
  layerElement: HTMLElement,
  matchedSpan: FreshSpanInfo
): HTMLElement {
  // Xóa marker cũ
  const existing = layerElement.querySelectorAll(".pdf-highlight-marker");
  existing.forEach((el) => el.remove());

  const span = matchedSpan.span;
  const spanRect = span.getBoundingClientRect();
  const layerRect = layerElement.getBoundingClientRect();

  // Tính toán chiều cao line height
  const computedStyle = window.getComputedStyle(span);
  const fontSize = parseFloat(computedStyle.fontSize) || 12;
  const lineHeight = parseFloat(computedStyle.lineHeight) || fontSize * 1.2;

  // YÊU CẦU UI 2: Chiều cao marker khoảng 1.3 lần lineHeight (phủ lớn hơn chữ một chút)
  const markerHeight = Math.max(spanRect.height, lineHeight * 1.3);
  const topOffset =
    spanRect.top - layerRect.top - (markerHeight - spanRect.height) / 2;

  const marker = document.createElement("div");
  marker.className = "pdf-highlight-marker";
  marker.dataset.ragHighlight = "true";

  Object.assign(marker.style, {
    position: "absolute",
    left: "0px",
    width: "100%",
    top: `${topOffset}px`,
    height: `${markerHeight}px`,
    backgroundColor: "rgba(181, 118, 47, 0.22)",
    borderLeft: "4px solid #B5762F",
    pointerEvents: "none",
    zIndex: "10",
    boxSizing: "border-box",
  });

  layerElement.appendChild(marker);
  return marker;
}
