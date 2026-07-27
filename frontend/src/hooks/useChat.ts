"use client";

import { useState, useCallback } from "react";
import { ChatMessage } from "@/types/chat";
import { chatService, mapCitationSource } from "@/services/chat.service";
import { remapCitations } from "@/utils/citations";

interface UseChatOptions {
  onConversationUpdated?: () => void;
}

export function useChat(options?: UseChatOptions) {
  const { onConversationUpdated } = options ?? {};
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmedContent = content.trim();

      if (!trimmedContent || isLoading) return;

      setError(null);
      setIsLoading(true);

      const chatHistory = messages
      .filter((m) => !m.isError)
      .slice(-8)
      .map((m) => ({
        role: m.sender,
        content: m.content,
      }));

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
        metadata: undefined,
        sources: [],
        createdAt: new Date().toISOString(),
        isStreaming: true,
      };
      
      setMessages((prev) => [...prev, userMessage, aiMessage]);

      try {
        await chatService.streamQuestion(
          {
            query: trimmedContent,
            documentIds: [],
            topK: 5,
            chatHistory, // ← was [], now uses the built history
            conversationId: conversationId ?? undefined,
          },
          {
            onConversationId: (id) => {
              setConversationId(id); // ← no longer calls onConversationUpdated here
            },
            onMetadata: (metadata) => {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === aiMessageId ? { ...message, metadata } : message
                )
              );
            },
            onToken: (token) => {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === aiMessageId
                    ? { ...message, content: message.content + token }
                    : message
                )
              );
            },
            onCitationMap: (citationMap) => {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === aiMessageId
                    ? { ...message, content: remapCitations(message.content, citationMap) }
                    : message
                )
              );
            },
            onSources: (sources) => {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === aiMessageId ? { ...message, sources } : message
                )
              );
            },
            onDone: () => {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === aiMessageId ? { ...message, isStreaming: false } : message
                )
              );
              onConversationUpdated?.(); // ← moved here: fires once the turn is fully saved
            },
            onError: (errorMessage) => {
              setError(errorMessage);
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === aiMessageId
                    ? {
                        ...message,
                        content: "An error occurred while processing your request.",
                        isError: true,
                        isStreaming: false,
                      }
                    : message
                )
              );
            },
          }
        );
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to connect to server";
        setError(errorMessage);
        setMessages((prev) =>
          prev.map((message) =>
            message.id === aiMessageId
              ? {
                  ...message,
                  content: "Unable to establish connection with AI service.",
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
    [isLoading, messages, conversationId, onConversationUpdated]
  );

  const loadConversation = useCallback(async (id: number) => {
    try {
      setIsLoading(true);
      setError(null);

      const conversation = await chatService.getConversation(id);

      const hydrated: ChatMessage[] = conversation.messages.map((m) => ({
        id: String(m.id),
        sender: m.sender,
        content: m.content,
        sources: m.sourcesJson ? JSON.parse(m.sourcesJson).map(mapCitationSource) : undefined,
        createdAt: m.createdAt,
        isStreaming: false,
      }));

      setMessages(hydrated);
      setConversationId(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load conversation");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    setConversationId(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    conversationId,
    sendMessage,
    clearMessages,
    loadConversation,
  };
}