
import type { AssistantResource } from "@/types/assistant-resource";

export type MessageSender = "user" | "ai";


/**
 * Citation source trả về từ RAG pipeline
 */
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


/**
 * Metadata của quá trình retrieval
 * Dùng cho debug / hiển thị nâng cao sau này
 */
/**
 * Metadata của quá trình retrieval
 * Dùng cho debug / hiển thị nâng cao sau này
 */
export interface RetrievalMetadata {
  originalQuery?: string;

  /**
   * Query sau khi LLM rewrite
   */
  rewrittenQuery?: string;

  /**
   * Số lượng chunk lấy được từ hybrid search (trước khi lọc theo citation)
   */
  retrievedChunks?: number;

  /**
   * Số lượng chunk thực sự đưa vào context gửi cho LLM
   */
  contextChunks?: number;

  /**
   * Có sử dụng reranker hay không
   */
  usedReranker?: boolean;
}


/**
 * Response dạng non-stream
 */
export interface RAGQueryResponse {
  answer: string;
  sources: CitationSource[];

  metadata?: RetrievalMetadata;
}


/**
 * Request gửi lên backend
 */
export interface RAGQueryRequest {
    query: string;
    notebookId: number;
    topK?: number;
    chatHistory?: ChatHistoryItem[];
    conversationId?: number;
}


export interface ChatHistoryItem {
  role: MessageSender;
  content: string;
}


export interface BaseResponse<T> {
  data: T;
  message?: string;
  status?: number;
}


/**
 * Message hiển thị trong UI
 */
export interface ChatMessage {
  id: string;

  sender: MessageSender;

  content: string;

  sources?: CitationSource[];

  resource?: AssistantResource;

  /**
   * Metadata từ RAG pipeline
   */
  metadata?: RetrievalMetadata;

  createdAt: string;

  isStreaming?: boolean;

  isError?: boolean;

  isStopped?: boolean;

}

export interface ConversationSummary {
  id: number;
  title: string;
  updatedAt: string;
}

export interface ConversationDetailMessage {
  id: number;
  sender: MessageSender;
  content: string;
  sourcesJson?: string | null;
  resourceJson?: string | null;
  createdAt: string;
}

export interface ConversationDetail {
  id: number;
  title: string;
  messages: ConversationDetailMessage[];
}

export interface ChatError {
  message: string;
  retry?: () => void;
}

export interface AssistantSendRequest {
  id: string;
  content: string;
}
