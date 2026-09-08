"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Icon } from "@/components/shared/icons";
import { SummaryContent } from "@/components/notebooks/SummaryContent";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import {
  summaryService,
  SummaryDetail,
  SummaryFormat,
  SummaryHistoryItem,
  SummaryLevel,
} from "@/services/summary.service";

interface SummaryTabProps {
  notebookId: number;
  activeDocumentCount: number;
  selectedSummaryId?: number | null;
}

function formatSummaryDate(value: string, detailed = false) {
  return new Date(value).toLocaleDateString("en-US", detailed
    ? { month: "short", day: "numeric", year: "numeric" }
    : { month: "short", day: "numeric" });
}

export function SummaryTab({
  notebookId,
  activeDocumentCount,
  selectedSummaryId,
}: SummaryTabProps) {
  const [summaries, setSummaries] = useState<SummaryHistoryItem[]>([]);
  const [selectedSummary, setSelectedSummary] = useState<SummaryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [level, setLevel] = useState<SummaryLevel>("standard");
  const [format, setFormat] = useState<SummaryFormat>("markdown");
  const [instruction, setInstruction] = useState("");
  const [viewMode, setViewMode] = useState<"rendered" | "raw">("rendered");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectionRequestRef = useRef(0);

  const loadSummary = useCallback(async (summaryId: number) => {
    const requestId = ++selectionRequestRef.current;
    setError(null);
    try {
      const detail = await summaryService.getDetail(notebookId, summaryId);
      if (requestId === selectionRequestRef.current) setSelectedSummary(detail);
    } catch (err) {
      console.error(err);
      if (requestId === selectionRequestRef.current) setError("Could not open summary.");
    }
  }, [notebookId]);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const history = await summaryService.listHistory(notebookId);
      setSummaries(history);
      const targetId = selectedSummaryId ?? history[0]?.id;
      if (targetId) await loadSummary(targetId);
      else setSelectedSummary(null);
    } catch (err) {
      console.error(err);
      setError("Could not load summary history.");
    } finally {
      setLoading(false);
    }
  }, [loadSummary, notebookId, selectedSummaryId]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handleGenerate = async () => {
    if (!activeDocumentCount || generating) return;
    setGenerating(true);
    setError(null);
    try {
      const created = await summaryService.generate({
        notebook_id: notebookId,
        level,
        format,
        instruction: instruction.trim() || undefined,
      });
      setSummaries((current) => [
        created,
        ...current.filter((item) => item.id !== created.id),
      ]);
      setSelectedSummary(created);
    } catch (err) {
      console.error(err);
      setError("The summary could not be generated. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (!selectedSummary) return;
    await navigator.clipboard.writeText(selectedSummary.summary_text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex h-full flex-1 items-center justify-center text-xs text-muted-foreground">
        <Icon name="progress_activity" className="mr-2 animate-spin" />
        Loading summaries...
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      <div className="flex flex-wrap items-center gap-2 border-b border-border/60 px-4 py-3 sm:px-6">
        <button
          type="button"
          onClick={() => setShowConfig((current) => !current)}
          className={`flex h-9 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-colors ${
            showConfig || instruction
              ? "border-primary/50 bg-primary/5 text-primary"
              : "border-border bg-background text-muted-foreground hover:bg-secondary hover:text-foreground"
          }`}
        >
          <Icon name="tune" className="text-base" />
          Configure
          <Icon name={showConfig ? "expand_less" : "expand_more"} className="text-base" />
        </button>

        <div className="ml-auto flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger
              disabled={!summaries.length}
              aria-label="Summary history"
              className="flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs text-muted-foreground outline-none hover:bg-secondary hover:text-foreground disabled:opacity-40"
            >
              <Icon name="history" size={17} />
              History
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80 rounded-xl p-1.5">
              <div className="px-2 py-1.5">
                <p className="text-xs font-semibold text-foreground">Summary history</p>
                <p className="text-[10px] text-muted-foreground">Open a previously generated summary</p>
              </div>
              <div className="max-h-72 overflow-y-auto">
                {summaries.map((item) => (
                  <DropdownMenuItem
                    key={item.id}
                    onClick={() => void loadSummary(item.id)}
                    className={`cursor-pointer rounded-lg px-2 py-2 ${selectedSummary?.id === item.id ? "bg-secondary" : ""}`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs font-medium text-foreground">{item.title}</div>
                      <div className="mt-0.5 text-[10px] capitalize text-muted-foreground">
                        {formatSummaryDate(item.created_at)} · {item.level} · {item.format.replace("_", " ")}
                      </div>
                    </div>
                    {selectedSummary?.id === item.id && <Icon name="check" size={15} className="ml-2 text-primary" />}
                  </DropdownMenuItem>
                ))}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          {selectedSummary && (
            <Button
              type="button"
              onClick={handleGenerate}
              disabled={generating || activeDocumentCount === 0}
              variant="outline"
              size="icon-sm"
              aria-label="Regenerate summary"
            >
              <RefreshCw className={generating ? "size-4 animate-spin" : "size-4"} />
            </Button>
          )}

          <Button onClick={handleGenerate} disabled={!activeDocumentCount || generating} className="h-9 text-xs">
            <Icon name={generating ? "progress_activity" : "auto_awesome"} className={generating ? "mr-1.5 animate-spin" : "mr-1.5"} />
            {generating ? "Generating..." : "Generate summary"}
          </Button>
        </div>
      </div>

      {showConfig && (
        <div className="shrink-0 space-y-4 border-b border-border/60 bg-secondary/15 px-4 py-4 sm:px-6">
          <div className="flex flex-wrap gap-6">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Length:</span>
              {(["brief", "standard", "comprehensive"] as SummaryLevel[]).map((item) => (
                <button key={item} onClick={() => setLevel(item)} className={`rounded-lg px-2.5 py-1 text-xs capitalize ${level === item ? "bg-secondary font-medium" : "text-muted-foreground"}`}>{item}</button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Format:</span>
              {(["markdown", "raw_text"] as SummaryFormat[]).map((item) => (
                <button key={item} onClick={() => setFormat(item)} className={`rounded-lg px-2.5 py-1 text-xs capitalize ${format === item ? "bg-secondary font-medium" : "text-muted-foreground"}`}>{item.replace("_", " ")}</button>
              ))}
            </div>
          </div>
          <Textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} placeholder="Additional instructions..." className="min-h-16 resize-none text-xs" />
        </div>
      )}

      {error && <div className="border-b border-destructive/20 bg-destructive/5 px-6 py-2 text-xs text-destructive">{error}</div>}

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
        {generating ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <Icon name="menu_book" className="mb-3 animate-pulse text-4xl text-primary" />
            <h3 className="text-sm font-semibold">Synthesizing Notebook Digests...</h3>
            <p className="mt-1 text-xs text-muted-foreground">Combining concepts from your active documents.</p>
          </div>
        ) : !selectedSummary ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <Icon name={activeDocumentCount ? "menu_book" : "warning"} className="mb-3 text-4xl text-muted-foreground/60" />
            <h3 className="font-heading text-base font-semibold">{activeDocumentCount ? "Generate your first summary" : "No active document found"}</h3>
            <p className="mt-1 max-w-md text-xs text-muted-foreground">{activeDocumentCount ? "Create a saved summary from the notebook's active sources." : "Enable at least one document to generate a summary."}</p>
          </div>
        ) : (
          <div className="mx-auto w-full max-w-5xl pb-12">
            <header className="mb-4 border-b border-border/60 pb-4">
              <h2 className="font-heading text-xl font-semibold text-foreground">{selectedSummary.title}</h2>
              <p className="mt-1 text-xs capitalize text-muted-foreground">
                {formatSummaryDate(selectedSummary.created_at, true)} · {selectedSummary.level} · {selectedSummary.format.replace("_", " ")}
              </p>
            </header>
            <div className="relative rounded-xl border border-border/80 bg-card p-6 shadow-2xs">
              <div className="mb-5 flex items-center justify-between gap-2">
                <div className="flex rounded-lg border border-border/60 bg-secondary/60 p-1">
                  <button onClick={() => setViewMode("rendered")} className={`rounded-md p-1 ${viewMode === "rendered" ? "bg-card shadow-2xs" : "text-muted-foreground"}`} title="Rendered view"><Icon name="visibility" className="text-sm" /></button>
                  <button onClick={() => setViewMode("raw")} className={`rounded-md p-1 ${viewMode === "raw" ? "bg-card shadow-2xs" : "text-muted-foreground"}`} title="Raw source"><Icon name="code" className="text-sm" /></button>
                </div>
                <button onClick={() => void handleCopy()} className="flex items-center gap-1 rounded-lg border border-border/60 bg-secondary/60 px-2 py-1.5 text-[11px] text-muted-foreground hover:text-foreground">
                  <Icon name={copied ? "check" : "content_copy"} className="text-sm" />
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
              <div className="text-xs leading-relaxed text-foreground">
                <SummaryContent content={selectedSummary.summary_text} format={selectedSummary.format} viewMode={viewMode} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
