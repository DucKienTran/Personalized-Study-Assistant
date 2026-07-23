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