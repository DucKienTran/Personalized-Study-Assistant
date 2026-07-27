/**
 * Format page range for citation display.
 *
 * Examples:
 * - 12, 12 -> "Page 12"
 * - 12, 15 -> "Page 12 - 15"
 */
export function formatPageRange(
  pageStart?: number | null,
  pageEnd?: number | null
): string {
  if (pageStart == null) return "";

  if (pageEnd == null || pageStart === pageEnd) {
    return `Page ${pageStart}`;
  }

  return `Page ${pageStart} - ${pageEnd}`;
}

export function remapCitations(
  renderedText: string,
  citationMap: Record<string, number>
): string {
  return renderedText.replace(/\[(\d+)\]/g, (match, num) => {
    const newNum = citationMap[num];
    return newNum !== undefined ? `[${newNum}]` : "";
  });
}