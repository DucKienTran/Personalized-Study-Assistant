"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useChat } from "@/hooks/useChat";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";
import { ChatHistory } from "@/components/chat/chat-history";
import { ChatInput, ChatInputHandle } from "@/components/chat/chat-input";
import { ConversationSwitcher } from "@/components/chat/conversation-switcher";
import {
  AssistantSendRequest,
  CitationSource,
  ConversationSummary,
} from "@/types/chat";
import { chatService } from "@/services/chat.service";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface AssistantTabProps {
  notebookId: number;
  activeDocumentCount: number;
  autoSendRequest: AssistantSendRequest | null;
  onAutoSendConsumed: (requestId: string) => void;
}

export function AssistantTab({
  notebookId,
  activeDocumentCount,
  autoSendRequest,
  onAutoSendConsumed,
}: AssistantTabProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isConversationListLoading, setIsConversationListLoading] = useState(false);
  const refreshConversations = useCallback(async () => {
    setIsConversationListLoading(true);
    try {
      setConversations(await chatService.listConversations(notebookId));
    } catch {
      // Conversation initialization already surfaces API failures in the chat.
    } finally {
      setIsConversationListLoading(false);
    }
  }, [notebookId]);

  const {
    messages,
    isLoading,
    isStreaming,
    chatError,
    conversationId,
    sendMessage,
    stopStreaming,
    loadConversation,
    initializeLatestConversation,
    startNewConversation,
  } = useChat({ notebookId, onConversationUpdated: refreshConversations });
  const chatInputRef = useRef<ChatInputHandle>(null);
  const initializedNotebookRef = useRef<number | null>(null);
  const handledAutoSendRef = useRef<string | null>(null);
  const [isConversationReady, setIsConversationReady] = useState(false);

  // PDF Viewer for citations
  const pdfViewer = usePdfViewer();

  const handleCitationClick = (source: CitationSource) => {
    if (pdfViewer?.openCitation) {
      pdfViewer.openCitation(source);
    }
  };

  useEffect(() => {
    if (initializedNotebookRef.current === notebookId) return;
    initializedNotebookRef.current = notebookId;
    setIsConversationReady(false);
    void Promise.all([initializeLatestConversation(), refreshConversations()]).finally(
      () => setIsConversationReady(true)
    );
  }, [initializeLatestConversation, notebookId, refreshConversations]);

  useEffect(() => {
    if (
      !autoSendRequest ||
      !isConversationReady ||
      activeDocumentCount === 0 ||
      isLoading ||
      isStreaming ||
      handledAutoSendRef.current === autoSendRequest.id
    ) {
      return;
    }

    handledAutoSendRef.current = autoSendRequest.id;
    onAutoSendConsumed(autoSendRequest.id);
    void sendMessage(autoSendRequest.content);
  }, [
    activeDocumentCount,
    autoSendRequest,
    isConversationReady,
    isLoading,
    isStreaming,
    onAutoSendConsumed,
    sendMessage,
  ]);

  const handleNewChat = async () => {
    if (!(await startNewConversation())) return;
    await refreshConversations();
    chatInputRef.current?.clear();
    window.requestAnimationFrame(() => chatInputRef.current?.focus());
  };

  const handleSelectConversation = async (id: number) => {
    if (id === conversationId || isStreaming) return;
    await loadConversation(id);
  };

  const handleRenameConversation = async (id: number, title: string) => {
    const updated = await chatService.renameConversation(id, title);
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === id ? updated : conversation
      )
    );
  };

  const handleDeleteConversation = async (id: number) => {
    await chatService.deleteConversation(id);
    const remaining = conversations
      .filter((conversation) => conversation.id !== id)
      .sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
    setConversations(remaining);

    if (id !== conversationId) return;
    if (remaining.length > 0) {
      await loadConversation(remaining[0].id);
      return;
    }
    await handleNewChat();
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden relative">
      <header className="relative flex h-12 shrink-0 items-center border-b border-border/60 bg-background">
        <div className="mx-auto w-full max-w-4xl min-w-0 px-4 pr-14 sm:px-6 sm:pr-32">
          <ConversationSwitcher
            conversations={conversations}
            activeConversationId={conversationId}
            isLoading={isConversationListLoading}
            onSelect={handleSelectConversation}
            onRename={handleRenameConversation}
            onDelete={handleDeleteConversation}
          />
        </div>

        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  onClick={handleNewChat}
                  disabled={isStreaming || isLoading}
                  variant="outline"
                  size="sm"
                  className="absolute right-4 size-8 cursor-pointer rounded-[10px] border-border bg-secondary px-0 text-primary transition-all hover:border-primary/50 hover:bg-secondary sm:right-6 sm:w-auto sm:px-3"
                  aria-label="New chat"
                >
                  <Icon name="add_comment" className="text-sm" />
                  <span className="hidden sm:inline">New chat</span>
                </Button>
              }
            />
            <TooltipContent side="left">New chat</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </header>

      {/* MAIN CONTENT AREA */}
      <div className="relative min-h-0 flex-1 overflow-hidden">
        {activeDocumentCount === 0 && (
          <div className="absolute left-6 right-16 top-6 z-10 flex items-center gap-2 rounded-[8px] border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-muted-foreground">
            <Icon name="warning" className="text-base text-amber-600" />
            Enable at least one document to send a new question.
          </div>
        )}
        <ChatHistory
          messages={messages}
          isLoading={isLoading}
          chatError={chatError}
          onCitationClick={handleCitationClick}
        />

        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 bg-background pb-4">
          <div className="pointer-events-auto mx-auto w-full max-w-4xl px-4 sm:px-6">
            <ChatInput
              ref={chatInputRef}
              onSend={sendMessage}
              onStop={stopStreaming}
              isStreaming={isStreaming}
              disabled={activeDocumentCount === 0 || (isLoading && !isStreaming)}
              placeholder="Ask a question about your documents (e.g. Summarize Chapter 1...)"
              className="rounded-[10px]"
              inputClassName="rounded-[10px]"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
