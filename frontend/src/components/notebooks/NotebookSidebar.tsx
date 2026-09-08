"use client";

import { Icon, SidebarIcon } from "@/components/shared/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { NotebookDetailOut } from "@/types/notebook";

interface NotebookSidebarProps {
  notebook: NotebookDetailOut;
  activeTab: "assistant" | "summary" | "quizzes" | "flashcards" | "mindmap";
  onTabChange: (
    tab: "assistant" | "summary" | "quizzes" | "flashcards" | "mindmap"
  ) => void;
  onOpenAddModal: () => void;
  onEditNotebook: () => void;
  onClose: () => void;
  onExpand: () => void;
  isCollapsed: boolean;
  onViewDoc: (docId: number, title: string) => void;
  onToggleDoc: (docId: number, currentActive: boolean) => void;
  onDeleteDoc: (docId: number) => Promise<void>;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getDocumentIcon(fileType?: string): string {
  const normalizedType = fileType?.toLowerCase().replace(/^\./, "");

  if (normalizedType === "pdf") return "picture_as_pdf";
  if (normalizedType === "md" || normalizedType === "markdown") return "markdown";
  if (normalizedType === "doc" || normalizedType === "docx") return "description";
  if (normalizedType === "txt" || normalizedType === "text") return "article";
  return "description";
}

function formatDocumentType(fileType?: string): string {
  const normalizedType = fileType?.toLowerCase().replace(/^\./, "");
  if (normalizedType === "pdf") return "PDF";
  if (normalizedType === "doc" || normalizedType === "docx") return "DOCX";
  if (normalizedType === "md" || normalizedType === "markdown") return "markdown";
  if (normalizedType === "txt" || normalizedType === "text") return "text";
  return normalizedType || "file";
}

export function NotebookSidebar({
  notebook,
  activeTab,
  onTabChange,
  onOpenAddModal,
  onEditNotebook,
  onClose,
  onExpand,
  isCollapsed,
  onViewDoc,
  onToggleDoc,
  onDeleteDoc,
}: NotebookSidebarProps) {
  const navigationItems = [
    { value: "assistant", label: "Assistant", icon: "forum" },
    { value: "summary", label: "Summary", icon: "summarize" },
    { value: "quizzes", label: "Quizzes", icon: "quiz" },
    { value: "flashcards", label: "Flashcards", icon: "style" },
    { value: "mindmap", label: "Mindmap", icon: "account_tree" },
  ] as const;

  if (isCollapsed) {
    return (
      <aside className="absolute inset-y-0 left-0 z-30 flex h-full w-full shrink-0 flex-col items-center overflow-y-auto border-r border-border/60 bg-background py-2 shadow-lg md:relative md:bg-card/20 md:shadow-none">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger render={<span className="inline-flex" />}>
              <button
                type="button"
                onClick={onExpand}
                className="flex h-10 w-10 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                aria-label="Expand sidebar"
              >
                <SidebarIcon size={19} />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">Expand sidebar</TooltipContent>
          </Tooltip>

          <nav className="mt-2 flex flex-col gap-1" aria-label="Notebook navigation">
            {navigationItems.map((item) => {
              const isActive = activeTab === item.value;
              return (
                <Tooltip key={item.value}>
                  <TooltipTrigger render={<span className="inline-flex" />}>
                    <button
                      type="button"
                      onClick={() => onTabChange(item.value)}
                      aria-current={isActive ? "page" : undefined}
                      aria-label={item.label}
                      className={`relative flex h-10 w-10 cursor-pointer items-center justify-center rounded-md transition-colors before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:bg-primary before:opacity-0 ${
                        isActive
                          ? "bg-secondary/75 text-foreground before:opacity-100"
                          : "text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
                      }`}
                    >
                      <Icon name={item.icon} className={`text-base ${isActive ? "text-primary" : ""}`} />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="right">{item.label}</TooltipContent>
                </Tooltip>
              );
            })}
          </nav>
        </TooltipProvider>
      </aside>
    );
  }

  return (
    <aside className="notebook-sidebar-scroll absolute inset-y-0 left-0 z-30 h-full w-full shrink-0 overflow-y-auto overscroll-contain border-r border-border/60 bg-background shadow-lg touch-pan-y md:relative md:bg-card/20 md:shadow-none">
      <div className="min-h-full">
        {/* Title Notebook */}
        <div className="group border-b border-border/40 px-5 py-2">
          <div className="flex items-start justify-between">
            <div className="flex min-w-0 flex-1 items-center gap-1.5 pr-3">
              <h2 className="truncate font-heading text-base font-bold text-foreground">
                {notebook.title}
              </h2>

              <button
                type="button"
                onClick={onEditNotebook}
                className="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded-md bg-secondary/60 text-muted-foreground opacity-0 transition-[opacity,background-color,color] hover:bg-secondary hover:text-foreground group-hover:opacity-100"
                title="Edit Title"
                aria-label="Edit notebook"
              >
                <Icon name="edit" className="text-[8px] text-muted-foreground/50" />
              </button>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              title="Close notebook sidebar"
              aria-label="Close notebook sidebar"
            >
              <SidebarIcon size={19} />
            </button>
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
            <span>{notebook.active_document_count}/{notebook.documents.length} Active docs</span>
            <span>{notebook.message_count} Messages</span>
            <span>{notebook.quiz_count} Quizzes</span>
          </div>
        </div>

        <nav className="shrink-0 border-b border-border/40 px-3 py-1" aria-label="Notebook navigation">
          <div className="space-y-0">
            {navigationItems.map((item) => {
              const isActive = activeTab === item.value;
              return (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => onTabChange(item.value)}
                  aria-current={isActive ? "page" : undefined}
                  className={`relative flex w-full items-center gap-3 rounded-md px-3 py-1 text-left text-xs transition-colors before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:bg-primary before:opacity-0 ${
                    isActive
                      ? "bg-secondary/75 font-medium text-foreground before:opacity-100"
                      : "text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
                  }`}
                >
                  <Icon name={item.icon} className={`text-base ${isActive ? "text-primary" : ""}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </nav>

        <div>
          <div className="shrink-0 px-5 pb-1 pt-2">
            <button
              onClick={onOpenAddModal}
              className="mt-1.5 flex h-7 w-full cursor-pointer items-center justify-center gap-2 rounded-lg border border-primary/25 bg-card text-xs font-medium text-foreground/85 transition-colors hover:border-primary/40 hover:bg-primary/5"
            >
              <Icon name="add" className="text-sm text-primary" />
              <span>Add source</span>
            </button>
          </div>

          <div className="space-y-0.5 pb-2 pl-4 pr-1">
            {notebook.documents.map(({ document: doc, is_active }) => {
            const isProcessing = doc.status === "pending" || doc.status === "processing";
            const hasFailed = doc.status === "failed";
            const isReady = doc.status === "completed";

            return (
              <div
                key={doc.id}
                aria-busy={isProcessing}
                onDoubleClick={(event) => {
                  if (!isReady) return;
                  if ((event.target as HTMLElement).closest("button")) return;
                  onViewDoc(doc.id, doc.title);
                }}
                className={`group flex items-center justify-between gap-2 rounded-xl border px-3 py-1 shadow-2xs transition-all ${
                  isProcessing
                    ? "border-border/60 bg-card/60 opacity-55"
                    : is_active
                      ? "border-border/80 bg-card hover:border-primary/40 hover:bg-card hover:shadow-sm"
                      : "border-border/40 bg-card/60 opacity-80 hover:border-primary/40 hover:bg-card hover:shadow-sm"
                }`}
              >
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <div
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-secondary/80 text-muted-foreground"
                  title={hasFailed ? "Document processing failed" : undefined}
                >
                  <Icon
                    name={isProcessing ? "progress_activity" : hasFailed ? "warning" : getDocumentIcon(doc.file_type)}
                    className={`text-base ${isProcessing ? "animate-spin" : hasFailed ? "text-destructive" : ""}`}
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium text-foreground">
                    {doc.title}
                  </p>
                  <div
                    className={`mt-0 flex items-center justify-between gap-2 text-[10px] ${hasFailed ? "text-destructive" : "text-muted-foreground"}`}
                    title={hasFailed ? "Document processing failed" : undefined}
                  >
                    <span className="shrink-0">{formatDocumentType(doc.file_type)}</span>
                    <span className="truncate text-right">
                      {isProcessing
                        ? "Processing..."
                        : hasFailed
                          ? "Processing failed"
                          : formatFileSize(doc.file_size)}
                    </span>
                  </div>
                </div>
              </div>

              <DropdownMenu>
                <DropdownMenuTrigger
                  className="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded-md text-muted-foreground opacity-0 outline-none transition hover:bg-secondary focus-visible:opacity-100 group-hover:opacity-100 data-popup-open:bg-secondary data-popup-open:opacity-100"
                  title="More options"
                  aria-label={`More options for ${doc.title}`}
                >
                  <Icon name="more_vert" className="text-base" />
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  side="top"
                  align="end"
                  sideOffset={6}
                  className="w-28 min-w-0 p-0.5"
                >
                  <DropdownMenuItem
                    disabled={!isReady}
                    onClick={() => onViewDoc(doc.id, doc.title)}
                    className="cursor-pointer gap-1 px-1 py-0.5 text-[10px] data-disabled:cursor-not-allowed"
                  >
                    <Icon name="visibility" size={10} />
                    View
                  </DropdownMenuItem>
                  <DropdownMenuSeparator className="my-0.5" />
                  <DropdownMenuItem
                    variant="destructive"
                    onClick={() => onDeleteDoc(doc.id)}
                    className="cursor-pointer gap-1 px-1 py-0.5 text-[10px]"
                  >
                    <Icon name="delete" size={10} />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              <button
                type="button"
                disabled={!isReady}
                onClick={() => onToggleDoc(doc.id, is_active)}
                title={!isReady ? (hasFailed ? "Processing failed" : "Available after processing") : undefined}
                aria-label={`${is_active ? "Deactivate" : "Activate"} ${doc.title}`}
                className={`flex h-4.5 w-8 shrink-0 items-center rounded-full p-0.5 transition-colors ${
                  is_active
                    ? "justify-end bg-[#3b5e47]"
                    : "justify-start bg-muted"
                } disabled:cursor-not-allowed disabled:opacity-50`}
              >
                <span className="h-3.5 w-3.5 rounded-full bg-white shadow-xs" />
              </button>
              </div>
            );
            })}
          </div>
        </div>
      </div>

    </aside>
  );
}
