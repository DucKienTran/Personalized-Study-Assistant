"use client";

import { useState } from "react";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  summaryService,
  SummaryLevel,
  SummaryFormat,
} from "@/services/summary.service";

interface SummaryTabProps {
  notebookId: number;
  activeDocumentCount: number;
  summaryText: string;
  setSummaryText: (text: string) => void;
  isGenerating: boolean;
  setIsGenerating: (generating: boolean) => void;
  level: SummaryLevel;
  setLevel: (level: SummaryLevel) => void;
  format: SummaryFormat;
  setFormat: (format: SummaryFormat) => void;
  instruction: string;
  setInstruction: (instruction: string) => void;
}

export function SummaryTab({
  notebookId,
  activeDocumentCount,
  summaryText,
  setSummaryText,
  isGenerating,
  setIsGenerating,
  level,
  setLevel,
  format,
  setFormat,
  instruction,
  setInstruction,
}: SummaryTabProps) {
  const [showConfig, setShowConfig] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  // Chế độ xem: 'rendered' vs 'raw'
  const [viewMode, setViewMode] = useState<"rendered" | "raw">("rendered");
  const [copied, setCopied] = useState(false);

  // Save Modal States
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [saveTitle, setSaveTitle] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const handleGenerate = async () => {
    if (activeDocumentCount === 0) return;
    try {
      setIsGenerating(true);
      setError(null);
      const resultText = await summaryService.generate({
        notebook_id: notebookId,
        level,
        format,
        instruction: instruction.trim() || undefined,
      });
      setSummaryText(resultText);
    } catch (err: any) {
      console.error("Failed to generate notebook summary:", err);
      setError(
        err?.response?.data?.message ||
          err?.message ||
          "Không thể tạo tóm tắt. Vui lòng thử lại sau."
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveSummary = async () => {
    if (!summaryText) return;
    const defaultTitle = `Summary - ${new Date().toLocaleDateString("vi-VN")}`;
    const finalTitle = saveTitle.trim() || defaultTitle;

    try {
      setIsSaving(true);
      setError(null);
      await summaryService.save({
        notebook_id: notebookId,
        title: finalTitle,
        summary_text: summaryText,
        level,
        format,
        instruction: instruction.trim() || undefined,
      });

      setIsSaveModalOpen(false);
      setSaveTitle("");
      setToastMsg("Đã lưu bản tóm tắt vào lịch sử!");
      setTimeout(() => setToastMsg(null), 3000);
    } catch (err: any) {
      console.error("Failed to save summary:", err);
      setError("Không thể lưu bản tóm tắt. Vui lòng thử lại.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyText = () => {
    if (!summaryText) return;
    navigator.clipboard.writeText(summaryText);
    setCopied(true);
    setToastMsg("Đã sao chép nội dung tóm tắt!");
    setTimeout(() => {
      setCopied(false);
      setToastMsg(null);
    }, 2500);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="absolute top-4 right-6 z-50 bg-primary text-primary-foreground text-xs px-3 py-1.5 rounded-[8px] shadow-md flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
          <Icon name="check_circle" className="text-base" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* TOP TOOLBAR */}
      <div className="border-b border-border/60 bg-card/40 px-6 py-2 flex items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className={`text-xs font-medium flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] border transition-all cursor-pointer ${
              showConfig || instruction
                ? "border-primary/50 text-primary bg-primary/5"
                : "border-border/80 text-muted-foreground hover:text-foreground bg-card"
            }`}
          >
            <Icon name="tune" className="text-base" />
            <span>Config & Instructions</span>
            {instruction && <span className="w-1.5 h-1.5 rounded-full bg-primary" />}
            <Icon
              name={showConfig ? "expand_less" : "expand_more"}
              className="text-base text-muted-foreground"
            />
          </button>
        </div>

        {/* TOP RIGHT: Regenerate / Save */}
        {summaryText && (
          <div className="flex items-center gap-2">
            <Button
              onClick={handleGenerate}
              variant="outline"
              size="sm"
              className="rounded-[8px] text-xs font-medium border-border/80 hover:bg-secondary flex items-center gap-1.5 cursor-pointer"
            >
              <Icon name="refresh" className="text-sm" />
              <span>Regenerate</span>
            </Button>
            <Button
              onClick={() => setIsSaveModalOpen(true)}
              size="sm"
              className="rounded-[8px] text-xs font-medium bg-primary text-primary-foreground hover:bg-[var(--primary-hover)] flex items-center gap-1.5 shadow-2xs cursor-pointer"
            >
              <Icon name="bookmark" className="text-base" />
              <span>Save Summary</span>
            </Button>
          </div>
        )}
      </div>

      {/* EXPANDABLE CONFIG PANEL: Căn lề trái & giới hạn độ rộng đúng bằng khung summary */}
      {showConfig && (
        <div className="border-b border-border/60 bg-secondary/15 p-4 px-6 shrink-0 animate-in slide-in-from-top-1 duration-200">
          <div className="w-full space-y-4">
            <div className="flex flex-wrap items-center gap-6">
              {/* Length Selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-muted-foreground">Length:</span>
                <div className="flex items-center gap-1 bg-card p-1 rounded-[8px] border border-border/60">
                  {(["brief", "standard", "comprehensive"] as SummaryLevel[]).map((lvl) => (
                    <button
                      key={lvl}
                      onClick={() => setLevel(lvl)}
                      className={`px-2.5 py-1 text-xs rounded-[8px] capitalize transition-all cursor-pointer ${
                        level === lvl
                          ? "bg-secondary text-foreground font-medium shadow-2xs"
                          : "text-muted-foreground hover:text-foreground font-normal"
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>

              {/* Format Selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-muted-foreground">Format:</span>
                <div className="flex items-center gap-1 bg-card p-1 rounded-[8px] border border-border/60">
                  <button
                    onClick={() => setFormat("markdown")}
                    className={`px-2.5 py-1 text-xs rounded-[8px] transition-all cursor-pointer ${
                      format === "markdown"
                        ? "bg-secondary text-foreground font-medium shadow-2xs"
                        : "text-muted-foreground hover:text-foreground font-normal"
                    }`}
                  >
                    Markdown
                  </button>
                  <button
                    onClick={() => setFormat("raw_text")}
                    className={`px-2.5 py-1 text-xs rounded-[8px] transition-all cursor-pointer ${
                      format === "raw_text"
                        ? "bg-secondary text-foreground font-medium shadow-2xs"
                        : "text-muted-foreground hover:text-foreground font-normal"
                    }`}
                  >
                    Raw Text
                  </button>
                </div>
              </div>
            </div>

            {/* Additional Instructions: Thu hẹp độ rộng ngang bằng khung white box bên dưới */}
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground block">
                Additional Instructions
              </label>
              <Textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="e.g. Focus on key definitions, equations, and critical concepts..."
                className="text-xs bg-card border-border/70 min-h-[55px] resize-none rounded-[8px] focus-visible:ring-primary/30 w-full"
              />
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mx-6 mt-4 p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-[8px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon name="error_outline" className="text-base shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-destructive/80 hover:text-destructive cursor-pointer"
          >
            <Icon name="close" className="text-base" />
          </button>
        </div>
      )}

      {/* MAIN CONTENT AREA: Đẩy lên sát trên, căn trái sát sidebar, bo góc rounded-[8px] */}
      <div className="flex-1 overflow-y-auto px-6 py-4 w-full flex flex-col">
        {/* CASE 1: TRẠNG THÁI CHƯA CHỌN DOCUMENT NÀO */}
        {activeDocumentCount === 0 ? (
          <div className="mt-6">
            <div className="border-2 border-dashed border-border/80 bg-card/60 rounded-[8px] p-8 py-12 flex flex-col items-center justify-center text-center shadow-2xs">
              <div className="w-12 h-12 rounded-[8px] bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-3">
                <Icon name="warning" className="text-2xl" />
              </div>

              <h4 className="font-heading text-base font-semibold text-foreground">
                No active document found
              </h4>

              <p className="text-xs text-muted-foreground max-w-md mt-2 mb-6 leading-relaxed">
                Please enable at least one document in the left sidebar to generate a notebook summary.
              </p>

              <Button
                disabled
                size="default"
                className="rounded-[8px] px-5 py-2 bg-muted text-muted-foreground flex items-center gap-2 cursor-not-allowed text-xs font-medium opacity-60"
              >
                <Icon name="auto_awesome" className="text-base" />
                <span>Summarize Notebook</span>
              </Button>
            </div>
          </div>
        ) : isGenerating ? (
          /* CASE 2: ĐANG TẠO TÓM TẮT (LOADING PENDING STATE) */
          <div className="my-auto py-16 flex flex-col items-center justify-center text-center space-y-4">
            <div className="w-12 h-12 rounded-[8px] bg-primary/10 text-primary flex items-center justify-center animate-pulse">
              <Icon name="menu_book" className="text-2xl animate-bounce" />
            </div>
            <div>
              <h4 className="font-heading text-sm font-semibold text-foreground">
                Synthesizing Notebook Digests...
              </h4>
              <p className="text-xs text-muted-foreground max-w-sm mt-1">
                AI is processing active documents and combining concepts into a unified summary.
              </p>
            </div>
          </div>
        ) : !summaryText ? (
          /* CASE 3: CHƯA GENERATE -> KHUNG VIỀN NÉT ĐỨT ĐẨY LÊN SÁT TRÊN */
          <div className="mt-6">
            <div className="border-2 border-dashed border-border/80 bg-card/60 rounded-xl p-8 py-12 flex flex-col items-center justify-center text-center shadow-2xs">
              <div className="w-12 h-12 rounded-[8px] bg-secondary/80 text-muted-foreground flex items-center justify-center mb-3">
                <Icon name="menu_book" className="text-2xl" />
              </div>

              <h4 className="font-heading text-base font-semibold text-foreground">
                Generate Notebook Summary
              </h4>

              <p className="text-xs text-muted-foreground max-w-md mt-2 mb-6 leading-relaxed">
                Synthesize key concepts, formulas, and connections across all{" "}
                <span className="font-medium text-foreground/80 whitespace-nowrap">
                  {activeDocumentCount} active document(s)
                </span>{" "}
                in this notebook.
              </p>

              <Button
                onClick={handleGenerate}
                size="default"
                className="rounded-[8px] px-5 py-2 bg-[#3b5e47] hover:bg-[#2d4a37] text-white flex items-center gap-2 shadow-xs cursor-pointer text-xs font-medium"
              >
                <Icon name="auto_awesome" className="text-base" />
                <span>Summarize Notebook</span>
              </Button>
            </div>
          </div>
        ) : (
          /* CASE 4: HIỂN THỊ KẾT QUẢ SUMMARY (Đổi vị trí nút Copy & Toggle View Mode, Render bảng Markdown chuẩn) */
          <div className="space-y-4 pt-1 pb-12">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div>
                <h3 className="font-heading text-sm font-bold text-foreground">
                  Notebook Summary
                </h3>
                <p className="text-[11px] text-muted-foreground mt-0.5 capitalize">
                  Level: {level} • Format: {format}
                </p>
              </div>

              {/* Nút Copy sang bên phải phía header nếu muốn hoặc giữ nguyên tùy chỉnh */}
            </div>

            {/* CONTAINER HIỂN THỊ NỘI DUNG TÓM TẮT */}
            <div className="bg-card border border-border/80 rounded-[8px] p-6 shadow-2xs relative group">
              {/* 1. Toggle View Mode chuyển sang góc TRÊN BÊN TRÁI (Vị trí cũ của nút copy) */}
              <div className="absolute top-3 left-3 z-10 flex items-center gap-1 bg-secondary/80 p-1 rounded-[8px] border border-border/60">
                <button
                  onClick={() => setViewMode("rendered")}
                  className={`p-1 rounded-[8px] transition-all cursor-pointer ${
                    viewMode === "rendered"
                      ? "bg-card text-foreground shadow-2xs font-medium"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  title="Rendered View"
                >
                  <Icon name="visibility" className="text-sm" />
                </button>
                <button
                  onClick={() => setViewMode("raw")}
                  className={`p-1 rounded-[8px] transition-all cursor-pointer ${
                    viewMode === "raw"
                      ? "bg-card text-foreground shadow-2xs font-medium"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  title="Raw Markdown Source"
                >
                  <Icon name="code" className="text-sm" />
                </button>
              </div>

              {/* 2. Nút Copy chuyển sang góc TRÊN BÊN PHẢI */}
              <button
                onClick={handleCopyText}
                className="absolute top-3 right-3 z-10 p-1.5 rounded-[8px] bg-secondary/80 hover:bg-secondary text-muted-foreground hover:text-foreground border border-border/60 transition-all cursor-pointer flex items-center gap-1 text-[11px]"
                title="Copy raw content"
              >
                <Icon name={copied ? "check" : "content_copy"} className="text-sm" />
                {copied && <span>Copied</span>}
              </button>

              <div className="pt-10 text-xs leading-relaxed text-foreground">
                {viewMode === "rendered" ? (
                  /* Rendered Markdown View (Hỗ trợ render bảng Markdown chuẩn) */
                  <div className="prose prose-xs dark:prose-invert max-w-none space-y-3 font-sans">
                    {summaryText.split("\n\n").map((block, idx) => {
                      // Kiểm tra nếu là khối Markdown Table
                      if (block.includes("|") && block.includes("---")) {
                        const rows = block
                          .trim()
                          .split("\n")
                          .map((r) =>
                            r
                              .split("|")
                              .map((cell) => cell.trim())
                              .filter(Boolean)
                          )
                          .filter((r) => r.length > 0 && !r[0].includes("---"));

                        if (rows.length > 0) {
                          const [header, ...bodyRows] = rows;
                          return (
                            <div key={idx} className="my-4 overflow-x-auto">
                              <table className="w-full border-collapse border border-border text-xs text-left">
                                <thead>
                                  <tr className="bg-secondary/50">
                                    {header.map((th, thIdx) => (
                                      <th
                                        key={thIdx}
                                        className="border border-border px-3 py-2 font-bold text-foreground"
                                      >
                                        {th}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {bodyRows.map((row, rIdx) => (
                                    <tr key={rIdx} className="hover:bg-secondary/20">
                                      {row.map((td, tdIdx) => (
                                        <td
                                          key={tdIdx}
                                          className="border border-border px-3 py-2 text-foreground/90"
                                        >
                                          {td}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          );
                        }
                      }

                      if (block.startsWith("## ")) {
                        return (
                          <h2
                            key={idx}
                            className="text-sm font-bold text-foreground border-b border-border/40 pb-1 mt-4 mb-2"
                          >
                            {block.replace("## ", "")}
                          </h2>
                        );
                      }
                      if (block.startsWith("# ")) {
                        return (
                          <h1
                            key={idx}
                            className="text-base font-bold text-foreground border-b border-border/60 pb-1 mt-5 mb-2"
                          >
                            {block.replace("# ", "")}
                          </h1>
                        );
                      }
                      return (
                        <p key={idx} className="whitespace-pre-wrap leading-relaxed">
                          {block}
                        </p>
                      );
                    })}
                  </div>
                ) : (
                  /* Raw Code View */
                  <pre className="font-mono text-xs whitespace-pre-wrap overflow-x-auto bg-secondary/30 p-3 rounded-[8px] border border-border/40">
                    {summaryText}
                  </pre>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* MODAL SAVE */}
      {isSaveModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-[8px] w-full max-w-md p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-heading text-sm font-bold">Save Summary Version</h3>
              <button
                onClick={() => setIsSaveModalOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-[8px]"
              >
                <Icon name="close" className="text-base" />
              </button>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Summary Title</label>
              <Input
                value={saveTitle}
                onChange={(e) => setSaveTitle(e.target.value)}
                placeholder={`Summary - ${new Date().toLocaleDateString("vi-VN")}`}
                className="text-xs rounded-[8px]"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsSaveModalOpen(false)}
                className="rounded-[8px] text-xs"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSaveSummary}
                disabled={isSaving}
                size="sm"
                className="rounded-[8px] text-xs font-medium bg-primary text-primary-foreground hover:bg-[var(--primary-hover)] cursor-pointer"
              >
                {isSaving && (
                  <Icon name="progress_activity" className="animate-spin text-sm mr-1.5" />
                )}
                Save
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}