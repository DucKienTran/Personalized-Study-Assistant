"use client";
import { useState } from "react";

import {
  AddIcon,
  ChatBubbleIcon,
  PenIcon,
  TrashIcon,
  CheckIcon,
  CloseIcon,
} from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { ConversationSummary } from "@/types/chat";
import { cn } from "@/lib/utils";
import { groupConversationsByDate } from "@/utils/conversation-grouping";

interface ConversationSidebarProps {
  conversations: ConversationSummary[];
  isLoading: boolean;
  activeConversationId: number | null;
  onSelect: (id: number) => void;
  onNewChat: () => void;
  onRename: (id: number, title: string) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

export function ConversationSidebar({
  conversations,
  isLoading,
  activeConversationId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
}: ConversationSidebarProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  const startEdit = (conv: ConversationSummary) => {
    setEditingId(conv.id);
    setDraftTitle(conv.title);
  };

  const commitEdit = async () => {
    if (editingId !== null && draftTitle.trim()) {
      await onRename(editingId, draftTitle.trim());
    }
    setEditingId(null);
  };

  const renderConversationRow = (conv: ConversationSummary) => {
    const isActive = conv.id === activeConversationId;
    const isEditing = editingId === conv.id;

    return (
      <div
        key={conv.id}
        className={cn(
          "group flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm transition-colors",
          isActive
            ? "border-l-2 border-primary bg-primary/5 font-medium text-foreground"
            : "border-l-2 border-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
        )}
      >
        <ChatBubbleIcon size={16} className="shrink-0" />

        {isEditing ? (
          <>
            <input
              autoFocus
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitEdit();
                if (e.key === "Escape") setEditingId(null);
              }}
              className="flex-1 rounded border border-border bg-white px-1.5 py-0.5 text-sm outline-none focus:border-primary"
            />
            <button onClick={commitEdit} className="shrink-0 text-primary">
              <CheckIcon size={14} />
            </button>
            <button onClick={() => setEditingId(null)} className="shrink-0 text-muted-foreground">
              <CloseIcon size={14} />
            </button>
          </>
        ) : (
          <>
            <button onClick={() => onSelect(conv.id)} className="flex-1 truncate text-left">
              {conv.title}
            </button>
            <button
              onClick={() => startEdit(conv)}
              className="hidden shrink-0 text-muted-foreground hover:text-foreground group-hover:block"
            >
              <PenIcon size={14} />
            </button>
            <button
              onClick={() => {
                if (confirm("Delete this conversation?")) onDelete(conv.id);
              }}
              className="hidden shrink-0 text-muted-foreground hover:text-destructive group-hover:block"
            >
              <TrashIcon size={14} />
            </button>
          </>
        )}
      </div>
    );
  };

  const groups = groupConversationsByDate(conversations);

  return (
    <aside className="hidden md:flex md:w-72 md:flex-col md:border-r md:border-border md:bg-white">
      <div className="p-3">
        <Button className="w-full gap-2" onClick={onNewChat}>
          <AddIcon size={18} />
          New chat
        </Button>
      </div>

      <ScrollArea className="flex-1">
        {isLoading && conversations.length === 0 ? (
          <div className="space-y-2 px-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-11 w-full rounded-lg" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-muted-foreground">
            No conversations yet.
          </p>
        ) : (
          <div className="space-y-4 px-2 pb-2">
            {groups.map((group) => (
              <div key={group.label}>
                <p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {group.label}
                </p>
                <div className="space-y-1">
                  {group.conversations.map(renderConversationRow)}
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </aside>
  );
}