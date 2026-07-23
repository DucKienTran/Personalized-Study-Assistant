import { CitationSource } from "@/types/chat";
import { apiFetch } from "./api-fetch";

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


export interface StreamCallbacks {
  onSources?: (sources: CitationSource[]) => void;
  onToken?: (token: string) => void;
  onError?: (errorMessage: string) => void;
  onDone?: () => void;
}

class ChatService {
  private mapCitationSource(
    source: BackendCitationSource
  ): CitationSource {
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

  async streamQuestion(
    question: string,
    callbacks: StreamCallbacks
  ): Promise<void> {
    const response = await apiFetch(
      "/rag/stream",
      {
        method:"POST",
        body: JSON.stringify({
          question
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
            case "sources": {
              const parsed = JSON.parse(rawData);

              // Support:
              // 1. [...]
              // 2. { data: [...] }
              const rawSources: BackendCitationSource[] =
                Array.isArray(parsed)
                  ? parsed
                  : parsed.data || [];

              callbacks.onSources?.(
                rawSources.map((source) =>
                  this.mapCitationSource(source)
                )
              );

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
  }
}

export const chatService = new ChatService();