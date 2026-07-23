"use client";

import React, { useEffect, useRef } from "react";
import {
  ChatMessage as ChatMessageType,
  CitationSource,
} from "@/types/chat";
import { ChatMessage } from "./chat-message";
import { MessageSquare, Trash2 } from "lucide-react";

interface ChatHistoryProps {
  messages: ChatMessageType[];
  isLoading?: boolean;
  onCitationClick?: (source: CitationSource) => void;
  onClear?: () => void;
}

export const ChatHistory: React.FC<ChatHistoryProps> = ({
  messages,
  isLoading = false,
  onCitationClick,
  onClear,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-[#EDF6F0] px-6 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#8FCFA9]/20 text-[#5DAA7B]">
          <MessageSquare size={26} />
        </div>

        <h3 className="text-base font-semibold text-gray-700">
          No messages yet
        </h3>

        <p className="mt-2 max-w-md text-sm leading-6 text-gray-500">
          Ask a question about your uploaded documents to start chatting with
          LearningAid AI.
        </p>
      </div>
    );
  }

  return (
    <div className="relative flex-1 overflow-y-auto bg-[#EDF6F0]">

      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-5 py-8 pb-36">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            onCitationClick={onCitationClick}
          />
        ))}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};  