import React from "react";

export function ChatStopSeparator() {
  return (
    <div className="flex items-center w-full my-4 gap-3">
      <div className="flex-1 h-px bg-border/60" />
      <span className="text-xs text-muted-foreground select-none">
        Response stopped
      </span>
      <div className="flex-1 h-px bg-border" />
    </div>
  );
}