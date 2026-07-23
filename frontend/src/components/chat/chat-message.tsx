"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Bot, User, AlertCircle } from "lucide-react";
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
  "Analyzing...",
  "Searching documents...",
  "Retrieving knowledge...",
  "Generating answer...",
];

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onCitationClick,
}) => {
  const isUser = message.sender === "user";
  const isError = message.isError;
  const isStreaming = message.isStreaming;

  /* Chỉ hiện thinking khi stream nhưng chưa có token nào */
  const isThinking =
    !isUser &&
    isStreaming &&
    message.content.trim().length === 0;

  const [thinkingIndex, setThinkingIndex] = useState(0);

  useEffect(() => {
    if (!isThinking) return;

    const timer = setInterval(() => {
      setThinkingIndex((i) => (i + 1) % THINKING_MESSAGES.length);
    }, 1200);

    return () => clearInterval(timer);
  }, [isThinking]);

  /* Chỉ giữ citation thật sự được dùng trong câu trả lời */
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
      className={`flex gap-3 ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {/* AI Avatar */}
      {!isUser && (
        <div
          className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
            isError
              ? "bg-red-100 text-red-600"
              : "bg-[#8FCFA9]/20 text-[#69B989]"
          }`}
        >
          {isError ? (
            <AlertCircle size={18} />
          ) : (
            <Bot size={18} />
          )}
        </div>
      )}

      {/* Message */}
      <div className={isUser ? "max-w-[80%]" : "flex-1 min-w-0"}>
        <div
          className={`rounded-2xl border shadow-sm transition-colors ${
            isUser
              ? "border-[#B9DFC7] bg-[#CFEBD8] text-[#173D2A]"
              : isError
              ? "border-red-200 bg-red-50 text-red-800"
              : "border-gray-200 bg-white text-[#111827]"
          }`}
        >
          <div className="px-5 py-4">
            {isThinking ? (
              <p className="text-sm italic text-gray-500">
                {THINKING_MESSAGES[thinkingIndex]}
              </p>
            ) : (
              <MarkdownRenderer
                content={message.content}
                isStreaming={isStreaming}
              />
            )}
          </div>

          {hasSources && (
            <>
              <div className="border-t border-gray-100" />

              <div className="px-5 py-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Sources
                </p>

                <div className="flex flex-wrap gap-2">
                  {visibleSources.map((source) => (
                    <CitationCard
                      key={source.chunkId}
                      source={source}
                      onClick={onCitationClick}
                    />
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#2E6F57] text-white">
          <User size={18} />
        </div>
      )}
    </div>
  );
};