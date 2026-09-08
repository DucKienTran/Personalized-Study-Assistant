import { CitationSource, ConversationDetail, ConversationSummary } from "@/types/chat";
import { apiFetch } from "./api-fetch";
import {
  RAGQueryRequest,
  RetrievalMetadata
} from "@/types/chat";
import type { AssistantResource } from "@/types/assistant-resource";

interface BackendCitationSource {
  index: number;
  document_id: number;
  document_title: string;
  page_start: number;
  page_end: number;
  header_path: string[];
  chunk_id: string;
  snippet?: string;
}

export type CitationMap = Record<string, number>;

export interface StreamCallbacks {
  onConversationId?: (id: number) => void;
  onConversationUpdated?: (conversation: ConversationSummary) => void;
  onCitationMap?: (map: Record<string, number>) => void;
  onSources?: (
    sources: CitationSource[]
  ) => void;

  onResource?: (resource: AssistantResource) => void;

  onToken?: (
    token: string
  ) => void;

  onMetadata?: (
    metadata: RetrievalMetadata
  ) => void;

  onError?: (
    errorMessage: string
  ) => void;

  onDone?: () => void;
}

export function mapCitationSource(source: BackendCitationSource): CitationSource {
  return {
    index: source.index,
    documentId: source.document_id,
    documentTitle: source.document_title,
    pageStart: source.page_start,
    pageEnd: source.page_end,
    headerPath: source.header_path || [],
    chunkId: source.chunk_id,
    snippet: source.snippet,
  };
}

class ChatService {
  async listConversations(notebookId?: number): Promise<ConversationSummary[]> {
    const query = notebookId ? `?notebook_id=${notebookId}` : "";
    const res = await apiFetch(`/conversations${query}`, { method: "GET" });
    if (!res.ok) throw new Error("Failed to load conversations");
    const data = await res.json();
    return data.map((c: any) => ({
      id: c.id,
      title: c.title,
      updatedAt: c.updated_at,
    }));
  }

  async createConversation(notebookId: number): Promise<ConversationSummary> {
    const res = await apiFetch("/conversations", {
      method: "POST",
      body: JSON.stringify({ notebook_id: notebookId }),
    });
    if (!res.ok) throw new Error("Failed to create conversation");
    const conversation = await res.json();
    return {
      id: conversation.id,
      title: conversation.title,
      updatedAt: conversation.updated_at,
    };
  }

  async getConversation(id: number): Promise<ConversationDetail> {
    const res = await apiFetch(`/conversations/${id}`, { method: "GET" });
    if (!res.ok) throw new Error("Failed to load conversation");
    const data = await res.json();
    return {
      id: data.id,
      title: data.title,
      messages: data.messages.map((m: any) => ({
        id: m.id,
        sender: m.sender,
        content: m.content,
        sourcesJson: m.sources_json,
        resourceJson: m.resource_json,
        createdAt: m.created_at,
      })),
    };
  }

  async renameConversation(id: number, title: string): Promise<ConversationSummary> {
    const res = await apiFetch(`/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error("Failed to rename conversation");
    const data = await res.json();
    return { id: data.id, title: data.title, updatedAt: data.updated_at };
  }

  async deleteConversation(id: number): Promise<void> {
    const res = await apiFetch(`/conversations/${id}`, {
      method: "DELETE",
    });

    if (!res.ok) {
      throw new Error("Failed to delete conversation");
    }
  }

  async getDocumentFileUrl(documentId: number): Promise<string> {
    const res = await apiFetch(`/documents/${documentId}/file-url`, {
      method: "GET",
    });

    if (!res.ok) {
      throw new Error(`Failed to get document file URL (${res.status})`);
    }

    const response = await res.json();

    const url = response?.data?.url;

    if (!url) {
      console.error(
        "[ChatService] Invalid file-url response:",
        response
      );

      throw new Error("Document file URL is missing from API response");
    }

    return url;
  }

  async streamQuestion(
    payload: RAGQueryRequest,
    callbacks: StreamCallbacks,
    signal?: AbortSignal,
  ): Promise<void> {
    const response = await apiFetch(
      "/rag/stream",
      {
        method: "POST",
        signal,
        body: JSON.stringify({
          query: payload.query,
          notebook_id: payload.notebookId,
          top_k: payload.topK ?? 5,
          chat_history: payload.chatHistory,
          conversation_id: payload.conversationId,
        }),
      }
    );

    if (!response.ok || !response.body) {
      throw new Error(
        `Streaming request failed with status ${response.status}`
      );
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let buffer = "";
    let doneCalled = false;

    const notifyDone = () => {
      if (!doneCalled) {
        doneCalled = true;
        callbacks.onDone?.();
      }
    };

    const abortHandler = () => {
      void reader.cancel();
    };

    if (signal) {
      signal.addEventListener("abort", abortHandler, { once: true });
    }

    try {
      while (true) {
        const { value, done } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, {
          stream: true,
        });

        // SSE event kết thúc bằng \n\n
        const events = buffer.split("\n\n");

        // Giữ lại event chưa hoàn thành
        buffer = events.pop() || "";

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;

          let eventType = "";
          const dataLines: string[] = [];

          for (const line of eventBlock.split("\n")) {
            if (line.startsWith("event:")) {
              eventType = line
                .replace("event:", "")
                .trim();
            }

            if (line.startsWith("data:")) {
              dataLines.push(
                line.replace("data:", "").trim()
              );
            }
          }

          const rawData = dataLines.join("\n");

          if (!rawData) continue;

          try {
            switch (eventType) {
              case "conversation_id": {
                const parsed = JSON.parse(rawData);
                callbacks.onConversationId?.(parsed.id);
                break;
              }
              case "conversation_updated": {
                const parsed = JSON.parse(rawData);
                callbacks.onConversationUpdated?.({
                  id: parsed.id,
                  title: parsed.title,
                  updatedAt: parsed.updated_at,
                });
                break;
              }
              case "citation_map": {
                const parsed = JSON.parse(rawData);
                const rawMap: Record<string, number> =
                  Array.isArray(parsed) ? {} : parsed.data || parsed;

                callbacks.onCitationMap?.(rawMap);
                break;
              }
              case "sources": {
                const parsed = JSON.parse(rawData);

                const rawSources: BackendCitationSource[] =
                  Array.isArray(parsed)
                    ? parsed
                    : parsed.data || [];

                callbacks.onSources?.(
                  rawSources.map((source) =>
                    mapCitationSource(source)
                  )
                );

                break;
              }

              case "resource": {
                const parsed = JSON.parse(rawData);
                callbacks.onResource?.(parsed.data || parsed);
                break;
              }

              case "token": {
                let token = rawData;

                try {
                  const parsed = JSON.parse(rawData);

                  if (typeof parsed === "string") {
                    token = parsed;
                  } else if (parsed.content) {
                    token = parsed.content;
                  }
                } catch {
                  // raw text token
                }

                callbacks.onToken?.(token);
                break;
              }

              case "error": {
                const parsed = JSON.parse(rawData);

                callbacks.onError?.(
                  parsed.message || "Streaming error occurred"
                );

                break;
              }

              case "done": {
                notifyDone();
                break;
              }

              case "metadata": {
                const parsed = JSON.parse(rawData);
                callbacks.onMetadata?.({
                  originalQuery: parsed.original_query,
                  rewrittenQuery: parsed.rewritten_query,
                  retrievedChunks: parsed.retrieved_chunks,
                  contextChunks: parsed.context_chunks,
                  usedReranker: parsed.used_reranker,
                });
                break;
              }
            }
          } catch (error) {
            console.error(
              "[ChatService] SSE parse error:",
              error,
              rawData
            );
          }
        }
      }

      // Stream đóng tự nhiên nhưng backend không gửi done
      notifyDone();
    } finally {
      if (signal && abortHandler) {
        signal.removeEventListener("abort", abortHandler);
      }
    }
  }
}

export const chatService = new ChatService();
