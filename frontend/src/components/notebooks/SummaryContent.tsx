import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { SummaryFormat } from "@/services/summary.service";

interface SummaryContentProps {
  content: string;
  format: SummaryFormat;
  viewMode: "rendered" | "raw";
}

export function SummaryContent({ content, format, viewMode }: SummaryContentProps) {
  if (format === "markdown" && viewMode === "rendered") {
    return <MarkdownRenderer content={content} linkCitations={false} />;
  }

  return (
    <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-[8px] border border-border/40 bg-secondary/30 p-3 font-mono text-xs">
      {content}
    </pre>
  );
}
