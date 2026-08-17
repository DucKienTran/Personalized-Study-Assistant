"use client";

import { useMemo, useRef, useState } from "react";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ConversationSummary } from "@/types/chat";

interface ConversationSwitcherProps {
  conversations: ConversationSummary[];
  activeConversationId: number | null;
  isLoading: boolean;
  onSelect: (id: number) => Promise<void>;
  onRename: (id: number, title: string) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

export function ConversationSwitcher({
  conversations,
  activeConversationId,
  isLoading,
  onSelect,
  onRename,
  onDelete,
}: ConversationSwitcherProps) {
  const [panelQuery, setPanelQuery] = useState("");
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingOrigin, setEditingOrigin] = useState<"header" | "list" | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [actionConversationId, setActionConversationId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ConversationSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const cancelRenameRef = useRef(false);

  const sortedConversations = useMemo(
    () =>
      [...conversations].sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      ),
    [conversations]
  );
  const activeConversation = sortedConversations.find(
    (conversation) => conversation.id === activeConversationId
  );
  const quickConversations = sortedConversations.slice(0, 7);
  const filteredConversations = useMemo(() => {
    const query = panelQuery.trim().toLocaleLowerCase();
    if (!query) return sortedConversations;
    return sortedConversations.filter((conversation) =>
      conversation.title.toLocaleLowerCase().includes(query)
    );
  }, [panelQuery, sortedConversations]);

  const beginRename = (
    conversation: ConversationSummary,
    origin: "header" | "list"
  ) => {
    cancelRenameRef.current = false;
    setEditingId(conversation.id);
    setEditingOrigin(origin);
    setDraftTitle(conversation.title);
  };

  const commitRename = async () => {
    if (editingId === null) return;
    const conversation = conversations.find((item) => item.id === editingId);
    const title = draftTitle.trim();
    setEditingId(null);
    setEditingOrigin(null);
    if (!conversation || !title || title === conversation.title) return;
    await onRename(conversation.id, title);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await onDelete(deleteTarget.id);
      setDeleteTarget(null);
    } finally {
      setIsDeleting(false);
    }
  };

  const renderTitle = (
    conversation: ConversationSummary,
    origin: "header" | "list"
  ) =>
    editingId === conversation.id && editingOrigin === origin ? (
      <input
        autoFocus
        value={draftTitle}
        onChange={(event) => setDraftTitle(event.target.value)}
        onFocus={(event) => event.currentTarget.select()}
        onBlur={() => {
          if (cancelRenameRef.current) {
            cancelRenameRef.current = false;
            return;
          }
          void commitRename();
        }}
        onKeyDown={(event) => {
          event.stopPropagation();
          if (event.key === "Enter") event.currentTarget.blur();
          if (event.key === "Escape") {
            cancelRenameRef.current = true;
            setEditingId(null);
            setEditingOrigin(null);
          }
        }}
        onClick={(event) => event.stopPropagation()}
        className="h-7 min-w-0 flex-1 rounded-md border border-border bg-background px-2 text-sm text-foreground outline-none focus:border-primary"
      />
    ) : (
      <span className="min-w-0 flex-1 truncate">{conversation.title}</span>
    );

  const renderActions = (conversation: ConversationSummary) => (
    <div className="relative shrink-0" onClick={(event) => event.stopPropagation()}>
      <button
        type="button"
        onClick={() =>
          setActionConversationId((current) =>
            current === conversation.id ? null : conversation.id
          )
        }
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-70 outline-none hover:bg-secondary hover:text-foreground group-hover:opacity-100 data-popup-open:bg-secondary data-popup-open:opacity-100"
        aria-label={`More options for ${conversation.title}`}
      >
        <Icon name="more_vert" className="text-base" />
      </button>
      {actionConversationId === conversation.id && (
        <div className="absolute right-0 top-full z-50 mt-1 w-32 rounded-md bg-popover p-1 text-sm text-popover-foreground shadow-md ring-1 ring-foreground/10">
          <button
            type="button"
            onClick={() => {
              setActionConversationId(null);
              beginRename(conversation, "list");
            }}
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left hover:bg-accent"
          >
            <Icon name="edit" />
            Rename
          </button>
          <button
            type="button"
            onClick={() => {
              setActionConversationId(null);
              setDeleteTarget(conversation);
            }}
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-destructive hover:bg-destructive/10"
          >
            <Icon name="delete" />
            Delete
          </button>
        </div>
      )}
    </div>
  );

  const renderConversationRow = (
    conversation: ConversationSummary,
    closePanel = false
  ) => (
    <div
      key={conversation.id}
      className={`group relative flex min-w-0 items-center rounded-md px-2 py-1 text-sm hover:bg-muted ${
        conversation.id === activeConversationId ? "bg-muted text-foreground" : "text-muted-foreground"
      }`}
    >
      {editingId === conversation.id && editingOrigin === "list" ? (
        renderTitle(conversation, "list")
      ) : (
        <button
          type="button"
          onClick={() => {
            void onSelect(conversation.id);
            if (closePanel) setIsPanelOpen(false);
          }}
          className="flex min-w-0 flex-1 py-1.5 text-left"
        >
          {renderTitle(conversation, "list")}
        </button>
      )}
      {renderActions(conversation)}
    </div>
  );

  return (
    <>
      <div className="flex w-full max-w-[560px] min-w-0 items-center">
        <div className="min-w-0 flex-1 px-1.5">
          {activeConversation &&
          editingId === activeConversation.id &&
          editingOrigin === "header" ? (
            renderTitle(activeConversation, "header")
          ) : (
            <button
              type="button"
              onDoubleClick={() =>
                activeConversation && beginRename(activeConversation, "header")
              }
              className="block w-full truncate py-1 text-left text-sm text-foreground"
              title={activeConversation?.title || "New conversation"}
            >
              {activeConversation?.title || "New conversation"}
            </button>
          )}
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground outline-none hover:bg-muted data-popup-open:bg-muted"
            aria-label="Open conversations"
          >
            <Icon name="expand_more" className="text-base" />
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            sideOffset={8}
            className="w-[min(560px,calc(100vw-2rem))] overflow-visible p-2"
          >
            {isLoading && conversations.length === 0 ? (
              <p className="px-2 py-6 text-center text-sm text-muted-foreground">
                Loading conversations...
              </p>
            ) : quickConversations.length === 0 ? (
              <p className="px-2 py-6 text-center text-sm text-muted-foreground">
                No conversations yet.
              </p>
            ) : (
              <div className="space-y-0.5">
                {quickConversations.map((conversation) =>
                  renderConversationRow(conversation)
                )}
              </div>
            )}

            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setIsPanelOpen(true)}>
              <span>View all conversations</span>
              <Icon name="arrow_forward" className="ml-auto text-base" />
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Dialog open={isPanelOpen} onOpenChange={setIsPanelOpen}>
        <DialogContent className="max-h-[min(680px,calc(100vh-2rem))] grid-rows-[auto_auto_minmax(0,1fr)] sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Conversations</DialogTitle>
          </DialogHeader>

          <input
            value={panelQuery}
            onChange={(event) => setPanelQuery(event.target.value)}
            placeholder="Search conversations..."
            className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none placeholder:text-muted-foreground focus:border-primary"
          />

          <div className="min-h-0 overflow-y-auto">
            {filteredConversations.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No conversations found.
              </p>
            ) : (
              <div className="space-y-0.5">
                {filteredConversations.map((conversation) =>
                  renderConversationRow(conversation, true)
                )}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && !isDeleting && setDeleteTarget(null)}
      >
        <DialogContent showCloseButton={!isDeleting}>
          <DialogHeader>
            <DialogTitle>Delete conversation?</DialogTitle>
            <DialogDescription>
              Deleting <span className="font-medium text-foreground">{deleteTarget?.title}</span> will permanently remove its messages.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void confirmDelete()}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Delete conversation"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
