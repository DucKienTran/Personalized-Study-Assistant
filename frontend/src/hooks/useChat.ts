"use client";

import { useState, useCallback, useRef } from "react";
import { ChatMessage, ConversationSummary } from "@/types/chat";
import { chatService, mapCitationSource } from "@/services/chat.service";
import { remapCitations } from "@/utils/citations";

export type ChatError = {
  message: string;
  retry?: () => void;
};

interface UseChatOptions {
  notebookId: number;
  onConversationUpdated?: (conversation?: ConversationSummary) => void;
}

export function useChat({
  notebookId,
  onConversationUpdated,
}: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<ChatError | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingRef = useRef(false);
  const conversationOperationRef = useRef(0);

  const hydrateConversation = useCallback(
    (conversation: Awaited<ReturnType<typeof chatService.getConversation>>) =>
      conversation.messages.map((message): ChatMessage => {
        let sources: ChatMessage["sources"];
        let resource: ChatMessage["resource"];
        if (message.sourcesJson) {
          try {
            sources = JSON.parse(message.sourcesJson).map(mapCitationSource);
          } catch {
            sources = undefined;
          }
        }
        if (message.resourceJson) {
          try {
            resource = JSON.parse(message.resourceJson);
          } catch {
            resource = undefined;
          }
        }
        return {
          id: String(message.id),
          sender: message.sender,
          content: message.content,
          sources,
          resource,
          createdAt: message.createdAt,
          isStreaming: false,
        };
      }),
    []
  );

  // Hàm xử lý chung cho streaming (bao gồm cả gửi mới và retry)
  const executeStreamQuestion = useCallback(
    async (trimmedContent: string, isRetry = false) => {
      setError(null);
      setChatError(null);
      setIsLoading(true);

      const chatHistory = messages
        .filter((m) => !m.isError)
        .slice(-8)
        .map((m) => ({
          role: m.sender,
          content: m.content,
        }));

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

      if (!isRetry) {
        const userMessage: ChatMessage = {
          id: crypto.randomUUID(),
          sender: "user",
          content: trimmedContent,
          createdAt: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage, aiMessage]);
      } else {
        // Nếu là Retry: không append thêm user message, chỉ append aiMessage mới
        setMessages((prev) => [...prev, aiMessage]);
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;
      setIsStreaming(true);
      streamingRef.current = true;

      // Helper khi gặp lỗi: Xóa bubble AI bị hỏng & set ChatError state
      const handleStreamError = (customMessage?: string) => {
        // Xóa bubble AI dở dang
        setMessages((prev) => prev.filter((m) => m.id !== aiMessageId));

        setChatError({
          message: customMessage || "This response didn’t load.",
          retry: async () => {
            await executeStreamQuestion(trimmedContent, true);
          }
        });
      };

      try {
        let receivedConversationUpdate = false;
        await chatService.streamQuestion(
          {
            query: trimmedContent,
            notebookId,
            topK: 5,
            chatHistory,
            conversationId: conversationId ?? undefined,
          },
          {
            onConversationId: (id) => {
              setConversationId(id);
            },

            onConversationUpdated: (conversation) => {
              receivedConversationUpdate = true;
              onConversationUpdated?.(conversation);
            },

            onMetadata: (metadata) => {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === aiMessageId
                    ? { ...message, metadata }
                    : message
                )
              );
            },

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

            onCitationMap: (citationMap) => {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === aiMessageId
                    ? {
                        ...message,
                        content: remapCitations(message.content, citationMap),
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

            onResource: (resource) => {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === aiMessageId
                    ? { ...message, resource }
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

              if (!receivedConversationUpdate) {
                onConversationUpdated?.();
              }
            },

            onError: (errorMessage) => {
              setError(errorMessage);
              handleStreamError();
            },
          },
          controller.signal
        );
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }

        const errorMessage =
          err instanceof Error ? err.message : "Failed to connect to server";

        setError(errorMessage);
        handleStreamError();
      } finally {
        setIsLoading(false);

        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
          streamingRef.current = false;
          setIsStreaming(false);
        }

        setMessages((prev) =>
          prev.map((message) =>
            message.id === aiMessageId && !message.isStopped
              ? {
                  ...message,
                  isStreaming: false,
                }
              : message
          )
        );
      }
    },
    [notebookId, messages, conversationId, onConversationUpdated]
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmedContent = content.trim();

      if (!trimmedContent || streamingRef.current) return;

      await executeStreamQuestion(trimmedContent, false);
    },
    [executeStreamQuestion]
  );

  const stopStreaming = useCallback(() => {
    streamingRef.current = false;
    setIsStreaming(false);

    setMessages((prev) => {
      const lastStreamingIndex = [...prev]
        .reverse()
        .findIndex(
          (message) => message.sender === "ai" && message.isStreaming
        );

      if (lastStreamingIndex === -1) return prev;

      const targetIndex = prev.length - 1 - lastStreamingIndex;

      return prev.map((message, index) =>
        index === targetIndex
          ? {
              ...message,
              isStreaming: false,
              isStopped: true,
            }
          : message
      );
    });

    abortControllerRef.current?.abort();
  }, []);

  const loadConversation = useCallback(async (id: number) => {
    try {
      setIsLoading(true);
      setError(null);
      setChatError(null);

      const conversation = await chatService.getConversation(id);

      const hydrated = hydrateConversation(conversation);

      setMessages(hydrated);
      setConversationId(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load conversation");
    } finally {
      setIsLoading(false);
    }
  }, [hydrateConversation]);

  const initializeLatestConversation = useCallback(async () => {
    const operation = ++conversationOperationRef.current;
    setIsLoading(true);
    setError(null);
    setChatError(null);

    try {
      const conversations = await chatService.listConversations(notebookId);
      if (operation !== conversationOperationRef.current) return;

      if (conversations.length === 0) {
        const conversation = await chatService.createConversation(notebookId);
        if (operation !== conversationOperationRef.current) return;
        setMessages([]);
        setConversationId(conversation.id);
        return;
      }

      const conversation = await chatService.getConversation(conversations[0].id);
      if (operation !== conversationOperationRef.current) return;
      setMessages(hydrateConversation(conversation));
      setConversationId(conversation.id);
    } catch (initializationError) {
      if (operation !== conversationOperationRef.current) return;
      setError(
        initializationError instanceof Error
          ? initializationError.message
          : "Failed to load conversation"
      );
    } finally {
      if (operation === conversationOperationRef.current) setIsLoading(false);
    }
  }, [hydrateConversation, notebookId]);

  const startNewConversation = useCallback(async () => {
    const operation = ++conversationOperationRef.current;
    abortControllerRef.current?.abort();
    streamingRef.current = false;
    setIsStreaming(false);
    setIsLoading(true);
    setError(null);
    setChatError(null);

    try {
      const conversation = await chatService.createConversation(notebookId);
      if (operation !== conversationOperationRef.current) return false;
      setMessages([]);
      setConversationId(conversation.id);
      return true;
    } catch (creationError) {
      if (operation === conversationOperationRef.current) {
        setError(
          creationError instanceof Error
            ? creationError.message
            : "Failed to create conversation"
        );
      }
      return false;
    } finally {
      if (operation === conversationOperationRef.current) setIsLoading(false);
    }
  }, [notebookId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    setChatError(null);
    setConversationId(null);
  }, []);

  return {
    messages,
    isLoading,
    isStreaming,
    error,
    chatError,
    conversationId,
    sendMessage,
    stopStreaming,
    clearMessages,
    loadConversation,
    initializeLatestConversation,
    startNewConversation,
  };
}
