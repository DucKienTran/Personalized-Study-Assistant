"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";

import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { Icon, ProgressActivityIcon, WarningIcon } from "@/components/shared/icons";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";
import {
  documentService,
  DocumentContent,
  DocumentOutlineItem,
} from "@/services/document.service";

interface ContentSection {
  anchor: string;
  content: string;
}

function normalizeForMatch(value: string): string {
  return value
    .replace(/<!--.*?-->/gs, " ")
    .replace(/[#*_>`~\[\]()|!-]/g, " ")
    .toLocaleLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function buildMarkdownSections(
  content: string,
  outline: DocumentOutlineItem[]
): ContentSection[] {
  const lines = content.replace(/<!--.*?-->/gs, "").split("\n");
  const sections: ContentSection[] = [];
  let headingIndex = 0;
  let currentAnchor = "content-start";
  let currentLines: string[] = [];

  const appendCurrent = () => {
    const sectionContent = currentLines.join("\n").trim();
    if (sectionContent) sections.push({ anchor: currentAnchor, content: sectionContent });
  };

  lines.forEach((line) => {
    if (/^#{1,4}\s+\S/.test(line)) {
      appendCurrent();
      currentAnchor = outline[headingIndex]?.anchor ?? `section-${headingIndex + 1}`;
      currentLines = [line];
      headingIndex += 1;
    } else {
      currentLines.push(line);
    }
  });
  appendCurrent();

  return sections.length > 0
    ? sections
    : [{ anchor: "content-start", content }];
}

function buildTextSections(content: string): ContentSection[] {
  const paragraphs = content
    .replace(/<!--.*?-->/gs, "")
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  return paragraphs.map((paragraph, index) => ({
    anchor: `content-${index + 1}`,
    content: paragraph,
  }));
}

function findCitationAnchor(
  sections: ContentSection[],
  snippet: string | null,
  headerPath: string[],
  outline: DocumentOutlineItem[]
): string | null {
  const normalizedSnippet = normalizeForMatch(snippet ?? "");
  if (normalizedSnippet) {
    const words = normalizedSnippet.split(" ");
    const probes = [
      normalizedSnippet.slice(0, 180),
      words.slice(0, 18).join(" "),
      words.slice(0, 10).join(" "),
    ].filter((probe) => probe.length >= 20);
    const matchingSection = sections.find((section) => {
      const normalizedSection = normalizeForMatch(section.content);
      return probes.some((probe) => normalizedSection.includes(probe));
    });
    if (matchingSection) return matchingSection.anchor;
  }

  const targetHeading = headerPath.at(-1)?.trim().toLocaleLowerCase();
  return targetHeading
    ? outline.find((item) => item.text.trim().toLocaleLowerCase() === targetHeading)?.anchor ?? null
    : null;
}

export function TextDocumentViewer({
  documentId,
  mode = "split",
  onClose,
}: {
  documentId: number;
  mode?: "split" | "full";
  onClose?: () => void;
}) {
  const {
    documentTitle,
    targetSnippet,
    targetHeaderPath,
    highlightRequestId,
    closeViewer,
  } = usePdfViewer();
  const handleClose = onClose ?? closeViewer;
  const [document, setDocument] = useState<DocumentContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeAnchor, setActiveAnchor] = useState<string | null>(null);
  const [isOutlineOpen, setIsOutlineOpen] = useState(true);
  const [viewMode, setViewMode] = useState<"rendered" | "raw">("rendered");

  useEffect(() => {
    let active = true;
    setDocument(null);
    setError(null);
    setIsOutlineOpen(true);
    setViewMode("rendered");
    documentService
      .getDocumentContent(documentId)
      .then((content) => {
        if (active) setDocument(content);
      })
      .catch(() => {
        if (active) setError("The document content could not be loaded.");
      });
    return () => {
      active = false;
    };
  }, [documentId]);

  const fileType = document?.file_type.toLowerCase().replace(/^\./, "") ?? "";
  const isMarkdown = fileType === "md" || fileType === "markdown";
  const hasTableOfContents = ["doc", "docx", "md", "markdown"].includes(fileType);
  const sections = useMemo(() => {
    if (!document) return [];
    return hasTableOfContents
      ? buildMarkdownSections(document.content_raw, document.outline)
      : buildTextSections(document.content_raw);
  }, [document, hasTableOfContents]);

  const scrollToAnchor = useCallback((anchor: string) => {
    const target = window.document.getElementById(`document-${documentId}-${anchor}`);
    if (!target) return;
    setActiveAnchor(anchor);
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [documentId]);

  useEffect(() => {
    if (
      !document ||
      (!targetSnippet && targetHeaderPath.length === 0) ||
      sections.length === 0
    ) return;
    const anchor = findCitationAnchor(
      sections,
      targetSnippet,
      targetHeaderPath,
      document.outline
    );
    if (!anchor) return;
    window.requestAnimationFrame(() => scrollToAnchor(anchor));
  }, [
    document,
    highlightRequestId,
    scrollToAnchor,
    sections,
    targetHeaderPath,
    targetSnippet,
  ]);

  return (
    <div className={`flex h-full min-h-0 flex-col bg-background ${mode === "split" ? "border-l border-border/70" : ""}`}>
      <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border/60 bg-card/70 px-3">
        <button
          type="button"
          title={mode === "full" ? "Back to Library" : "Hide document viewer"}
          aria-label={mode === "full" ? "Back to Library" : "Hide document viewer"}
          onClick={handleClose}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          <Icon name={mode === "full" ? "arrow_back" : "visibility_off"} size={18} />
        </button>
        <span className="h-5 w-px bg-border/80" aria-hidden />
        <p className="min-w-0 flex-1 truncate font-heading text-xs font-semibold text-foreground">
          {document?.title ?? documentTitle}
        </p>
        {isMarkdown && document && (
          <div className="flex shrink-0 items-center rounded-md border border-border/70 bg-secondary/45 p-0.5">
            {([
              { mode: "rendered", icon: "visibility", label: "Rendered view" },
              { mode: "raw", icon: "code", label: "Raw Markdown" },
            ] as const).map(({ mode, icon, label }) => (
              <button
                key={mode}
                type="button"
                onClick={() => setViewMode(mode)}
                title={label}
                aria-label={label}
                aria-pressed={viewMode === mode}
                className={`flex h-7 w-7 items-center justify-center rounded transition-colors ${
                  viewMode === mode
                    ? "bg-card text-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon name={icon} size={14} />
              </button>
            ))}
          </div>
        )}
        {hasTableOfContents && document && document.outline.length > 0 && (
          <button
            type="button"
            title={isOutlineOpen ? "Hide outline" : "Show outline"}
            aria-label={isOutlineOpen ? "Hide outline" : "Show outline"}
            aria-pressed={isOutlineOpen}
            onClick={() => setIsOutlineOpen((current) => !current)}
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md transition-colors ${
              isOutlineOpen
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            }`}
          >
            <Icon name="view_sidebar" size={18} />
          </button>
        )}
      </header>

      {error ? (
        <div className="flex flex-1 items-center justify-center gap-2 px-6 text-center text-xs text-destructive">
          <WarningIcon size={18} />
          {error}
        </div>
      ) : !document ? (
        <div className="flex flex-1 items-center justify-center gap-2 text-xs text-muted-foreground">
          <ProgressActivityIcon size={18} className="animate-spin" />
          Loading document...
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <main className="min-w-0 flex-1 overflow-y-auto bg-secondary/20 px-5 py-6 scroll-pt-5">
            <article className="mx-auto min-w-0 max-w-3xl space-y-5 overflow-hidden rounded-xl border border-border/60 bg-card px-6 py-7 shadow-xs">
              <div
                key={viewMode}
                className="space-y-5 animate-in fade-in-0 slide-in-from-bottom-1 duration-200 motion-reduce:animate-none"
              >
                {sections.map((section) => (
                  <section
                    key={section.anchor}
                    id={`document-${documentId}-${section.anchor}`}
                    className={`min-w-0 scroll-mt-5 overflow-hidden rounded-md transition-colors [overflow-wrap:anywhere] [&_code]:whitespace-pre-wrap [&_code]:break-all [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_pre]:whitespace-pre-wrap ${
                      activeAnchor === section.anchor
                        ? "bg-amber-100/70 ring-4 ring-amber-100/70"
                        : ""
                    }`}
                  >
                    {isMarkdown && viewMode === "raw" ? (
                      <pre className="min-w-0 whitespace-pre-wrap break-words font-mono text-xs leading-6 text-foreground/85 [overflow-wrap:anywhere]">
                        {section.content}
                      </pre>
                    ) : hasTableOfContents ? (
                      <MarkdownRenderer content={section.content} linkCitations={false} />
                    ) : (
                      <p className="whitespace-pre-wrap text-sm leading-7 text-foreground/90">
                        {section.content}
                      </p>
                    )}
                  </section>
                ))}
              </div>
            </article>
          </main>

          {hasTableOfContents && document.outline.length > 0 && isOutlineOpen && (
            <aside className="w-36 shrink-0 overflow-y-auto border-l border-border/60 bg-card/45 px-2 py-3">
              <p className="mb-3 px-2 text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Outline
              </p>
              <nav aria-label="Document outline" className="space-y-0">
                {document.outline.map((item) => (
                  <button
                    key={item.anchor}
                    type="button"
                    onClick={() => scrollToAnchor(item.anchor)}
                    title={item.text}
                    className={`block w-full truncate rounded-md py-0.5 pr-2 text-left text-[11px] leading-5 transition-colors ${
                      activeAnchor === item.anchor
                        ? "bg-primary/10 font-semibold text-primary"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    }`}
                    style={{ paddingLeft: `${8 + (item.level - 1) * 10}px` }}
                  >
                    {item.text}
                  </button>
                ))}
              </nav>
            </aside>
          )}
        </div>
      )}
    </div>
  );
}
