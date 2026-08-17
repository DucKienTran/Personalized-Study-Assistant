"use client";

import React, { useEffect, useRef } from "react";
import {
  ChatMessage as ChatMessageType,
  CitationSource,
} from "@/types/chat";
import { ChatMessage } from "./chat-message";
import { ChatStopSeparator } from "./chat-stop-separator";
import { ChatErrorMessage } from "./chat-error-message";
import { ChatError } from "@/hooks/useChat";
import { MessageSquare } from "lucide-react";

interface ChatHistoryProps {
  messages: ChatMessageType[];
  isLoading?: boolean;
  chatError?: ChatError | null;
  onCitationClick?: (source: CitationSource) => void;
  onClear?: () => void;
}

export const ChatHistory: React.FC<ChatHistoryProps> = ({
  messages,
  isLoading = false,
  chatError,
  onCitationClick,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, chatError]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="absolute inset-0 flex min-h-0 flex-col items-center justify-center bg-background px-6 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
          <MessageSquare size={26} />
        </div>

        <h3 className="text-base font-semibold text-foreground">
          No messages yet
        </h3>

        <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
          Ask a question about your uploaded documents to start chatting with
          LearningAid AI.
        </p>
      </div>
    );
  }

  return (
    <div className="notebook-sidebar-scroll absolute inset-0 min-h-0 min-w-0 overflow-x-hidden overflow-y-auto bg-background">
      <div className="mx-auto flex w-full min-w-0 max-w-4xl flex-col px-4 pt-8 sm:px-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={message.sender === "user" ? "mb-6" : "mb-10"}
          >
            {!(message.sender === "ai" && message.isStopped) && (
              <ChatMessage
                message={message}
                onCitationClick={onCitationClick}
              />
            )}

            {message.sender === "ai" && message.isStopped && (
              <ChatStopSeparator />
            )}
          </div>
        ))}

        {chatError && (
          <ChatErrorMessage
            message={chatError.message}
            onRetry={chatError.retry}
          />
        )}

        <div
          ref={bottomRef}
          className="h-[calc(2.75rem+1rem+1.5rem)] shrink-0"
        />
      </div>
    </div>
  );
};
