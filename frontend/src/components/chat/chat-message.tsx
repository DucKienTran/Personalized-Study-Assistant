"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  ChatMessage as ChatMessageType,
  CitationSource,
} from "@/types/chat";
import { MarkdownRenderer } from "./markdown-renderer";
import { CitationCard } from "./citation-card";

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationClick?: (source: CitationSource) => void;
}

const THINKING_MESSAGES = [
  "Thinking...",
  "Musing...",
  "Analyzing...",
  "Searching documents...",
  "Sleuthing...",
  "Honing...",
  "Preparing...",
  "Generating answer...",
];

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onCitationClick,
}) => {
  const isUser = message.sender === "user";
  const isError = message.isError;
  const isStreaming = message.isStreaming;

  const isThinking =
    !isUser &&
    isStreaming &&
    message.content.trim().length === 0;

  const [thinkingIndex, setThinkingIndex] = useState(0);

  useEffect(() => {
    if (!isThinking) return;

    const timer = setInterval(() => {
      setThinkingIndex((i) => (i + 1) % THINKING_MESSAGES.length);
    }, 2000);

    return () => clearInterval(timer);
  }, [isThinking]);

  const visibleSources = useMemo(() => {
    if (!message.sources?.length) return [];

    const matches = [
      ...message.content.matchAll(/\[(\d+)\]/g),
    ];

    const usedIndexes = new Set(
      matches.map((m) => Number(m[1]))
    );

    return message.sources.filter((source) =>
      usedIndexes.has(source.index)
    );
  }, [message.content, message.sources]);

  const hasSources =
    !isUser &&
    !isStreaming &&
    visibleSources.length > 0;

  return (
    <div
      className={`flex w-full min-w-0 max-w-full ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      <div
        data-chat-bubble
        className={`min-w-0 max-w-full [overflow-wrap:anywhere] ${
          isUser
            ? "max-w-[85%] rounded-[10px] border border-border/80 bg-secondary/70 text-foreground shadow-xs transition-colors sm:max-w-[68%]"
            : `w-full ${isError ? "text-destructive" : "text-foreground"}`
        }`}
      >
        <div className={isUser ? "px-4 py-3" : "min-w-0 max-w-full"}>
          {isThinking ? (
            <p className="text-sm italic text-muted-foreground">
              {THINKING_MESSAGES[thinkingIndex]
                .split("")
                .map((char, index) => (
                  <span
                    key={index}
                    className="thinking-char"
                    style={{
                      animationDelay: `${index * 80}ms`,
                    }}
                  >
                    {char === " " ? "\u00A0" : char}
                  </span>
                ))}
            </p>
          ) : (
            <MarkdownRenderer
              content={message.content}
              isStreaming={isStreaming}
            />
          )}
        </div>

        {hasSources && (
          <div className="mt-6 min-w-0 max-w-full">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Sources
            </p>

            <div className="flex min-w-0 max-w-full flex-wrap gap-1.5">
              {visibleSources.map((source) => (
                <CitationCard
                  key={source.chunkId}
                  source={source}
                  onClick={onCitationClick}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
