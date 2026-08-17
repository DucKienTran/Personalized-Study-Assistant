// components/notebooks/NotebookCard.tsx
import Link from "next/link";
import { Icon } from "@/components/shared/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { NotebookOut } from "@/types/notebook";

interface NotebookCardProps {
  notebook: NotebookOut;
  variant?: "dashboard" | "full";
  initialTab?: "assistant" | "summary";
  fitViewport?: boolean;
  onEdit?: (notebook: NotebookOut) => void;
  onDelete?: (notebook: NotebookOut) => void;
}

function formatDate(dateStr: string | null, includeYear = true): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    ...(includeYear && { year: "numeric" }),
  });
}

export function NotebookCard({
  notebook,
  variant = "dashboard",
  initialTab,
  fitViewport = false,
  onEdit,
  onDelete,
}: NotebookCardProps) {
  const accentColor = notebook.color || "var(--primary)";
  const isDashboard = variant === "dashboard";

  return (
    <div
      className={`group relative min-h-[160px] overflow-visible rounded-2xl border border-border/80 bg-card shadow-2xs transition-all duration-200 hover:shadow-md ${
        isDashboard ? "border-t-[3px]" : "border-l-[3px]"
      }`}
      style={{
        // Tận dụng CSS border native để tự động ôm cong góc theo border-radius
        borderTopColor: isDashboard ? accentColor : undefined,
        borderLeftColor: !isDashboard ? accentColor : undefined,
      }}
    >
      <Link
        href={`/notebooks/${notebook.id}${initialTab ? `?tab=${initialTab}` : ""}`}
        className={`flex h-full min-h-[156px] flex-col justify-between rounded-2xl ${
          isDashboard || fitViewport ? "p-3 lg:p-5" : "p-5"
        }`}
      >
        <div className="pr-8">
          <h3 className="line-clamp-1 font-heading text-base font-bold text-foreground transition-colors group-hover:text-primary">
            {notebook.title}
          </h3>
          <p className={`mt-2 text-xs font-normal leading-relaxed text-muted-foreground ${
            isDashboard || fitViewport ? "hidden lg:line-clamp-2" : "line-clamp-2"
          }`}>
            {notebook.description || (isDashboard ? "No description" : "No description provided.")}
          </p>
        </div>

        <div className={`flex items-center justify-between text-xs text-muted-foreground ${
          isDashboard || fitViewport ? "mt-2 lg:mt-5" : "mt-5"
        }`}>
          {isDashboard ? (
            <span className="flex items-center gap-1.5 text-[11px] font-medium text-foreground/80">
              <Icon name="description" className="text-sm text-muted-foreground" />
              {notebook.document_count ?? 0} docs
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-lg bg-secondary px-2.5 py-1 text-[11px] font-medium text-foreground">
              <Icon name="description" className="text-xs text-muted-foreground" />
              {notebook.document_count ?? 0}
            </span>
          )}

          <span className="text-[11px] text-muted-foreground/80">
            {formatDate(notebook.updated_at || notebook.created_at, !isDashboard)}
          </span>
        </div>
      </Link>

      {(onEdit || onDelete) && (
        <DropdownMenu>
          <DropdownMenuTrigger
            className="absolute right-2 top-2 z-10 flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground opacity-100 outline-none transition-colors hover:bg-secondary hover:text-foreground sm:opacity-0 sm:group-hover:opacity-100 sm:data-popup-open:opacity-100"
            aria-label={`More options for ${notebook.title}`}
          >
            <Icon name="more_vert" className="text-lg" />
          </DropdownMenuTrigger>
          <DropdownMenuContent side="top" align="end" sideOffset={4} className="w-32">
            {onEdit && (
              <DropdownMenuItem onClick={() => onEdit(notebook)} className="cursor-pointer">
                <Icon name="edit" />
                Edit
              </DropdownMenuItem>
            )}
            {onEdit && onDelete && <DropdownMenuSeparator />}
            {onDelete && (
              <DropdownMenuItem
                variant="destructive"
                onClick={() => onDelete(notebook)}
                className="cursor-pointer"
              >
                <Icon name="delete" />
                Delete
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
