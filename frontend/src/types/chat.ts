export type MessageSender = "user" | "ai";

export interface CitationSource {
  index: number;
  documentId: number;
  documentTitle: string;
  pageStart: number;
  pageEnd: number;
  headerPath: string[];
  chunkId: string;
  snippet?: string;
}

export interface RAGQueryResponse {
  answer: string;
  sources: CitationSource[];
}

export interface BaseResponse<T> {
  data: T;
  message?: string;
  status?: number;
}

export interface ChatMessage {
  id: string;
  sender: MessageSender;
  content: string;
  sources?: CitationSource[];
  createdAt: string;
  isStreaming?: boolean;
  isError?: boolean;
}