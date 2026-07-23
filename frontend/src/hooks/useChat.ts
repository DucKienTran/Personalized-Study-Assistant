"use client";

import { useState, useCallback } from "react";
import { ChatMessage } from "@/types/chat";
import { chatService } from "@/services/chat.service";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmedContent = content.trim();

      if (!trimmedContent || isLoading) return;

      setError(null);
      setIsLoading(true);

      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        sender: "user",
        content: trimmedContent,
        createdAt: new Date().toISOString(),
      };

      const aiMessageId = crypto.randomUUID();

      const aiMessage: ChatMessage = {
        id: aiMessageId,
        sender: "ai",
        content: "",
        sources: [],
        createdAt: new Date().toISOString(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, aiMessage]);

      try {
        await chatService.streamQuestion(trimmedContent, {
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === aiMessageId
                  ? {
                      ...message,
                      content: message.content + token,
                    }
                  : message
              )
            );
          },

          onSources: (sources) => {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === aiMessageId
                  ? {
                      ...message,
                      sources,
                    }
                  : message
              )
            );
          },

          onDone: () => {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === aiMessageId
                  ? {
                      ...message,
                      isStreaming: false,
                    }
                  : message
              )
            );
          },

          onError: (errorMessage) => {
            setError(errorMessage);

            setMessages((prev) =>
              prev.map((message) =>
                message.id === aiMessageId
                  ? {
                      ...message,
                      content:
                        "An error occurred while processing your request.",
                      isError: true,
                      isStreaming: false,
                    }
                  : message
              )
            );
          },
        });
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : "Failed to connect to server";

        setError(errorMessage);

        setMessages((prev) =>
          prev.map((message) =>
            message.id === aiMessageId
              ? {
                  ...message,
                  content:
                    "Unable to establish connection with AI service.",
                  isError: true,
                  isStreaming: false,
                }
              : message
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  };
}