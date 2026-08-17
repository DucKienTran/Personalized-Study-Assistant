"use client";

import React from "react";
import { AlertCircle } from "lucide-react";

export interface ChatErrorMessageProps {
  message?: string;
  onRetry?: () => void;
}

export const ChatErrorMessage: React.FC<ChatErrorMessageProps> = ({
  message = "This response didn’t load.",
  onRetry,
}) => {
  return (
    <div className="mx-auto flex w-2/3 items-center justify-between gap-3 rounded-xl border border-[#e5e7eb] bg-card p-4 text-foreground shadow-sm dark:border-border">
      <div className="flex items-center gap-2.5">
        <AlertCircle className="h-5 w-5 shrink-0 text-amber-500 dark:text-amber-400" />
        <span className="text-sm font-medium text-foreground">
          {message}
        </span>
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          type="button"
          className="shrink-0 cursor-pointer select-none rounded-lg bg-secondary px-3 py-1.5 text-xs font-semibold text-secondary-foreground transition-colors hover:bg-secondary/80 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          Try again
        </button>
      )}
    </div>
  );
};