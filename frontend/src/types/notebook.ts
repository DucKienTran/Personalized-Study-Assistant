// types/notebook.ts

export type DocumentProcessingStatus = "pending" | "processing" | "completed" | "failed";

export interface DocumentOut {
  id: number;
  title: string;
  file_path?: string;
  file_type?: string;
  file_size: number;
  total_pages?: number;
  status: DocumentProcessingStatus;
  created_at: string;
}

export interface NotebookDocumentOut {
  is_active: boolean;
  added_at: string;
  document: DocumentOut;
}

export interface NotebookOut {
  id: number;
  title: string;
  description: string | null;
  color: string;
  document_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface NotebookDetailOut {
  id: number;
  title: string;
  description: string | null;
  color: string;
  documents: NotebookDocumentOut[];
  active_document_count: number;
  quiz_count: number;
  message_count: number;
  total_size: number;
  created_at: string;
  updated_at: string | null;
}

// Payloads
export interface NotebookCreatePayload {
  title: string;
  description?: string;
  color?: string;
}

export interface NotebookUpdatePayload {
  title?: string;
  description?: string;
  color?: string;
}

export interface AddDocumentsToNotebookPayload {
  document_ids: number[];
}

export interface ToggleDocumentActivePayload {
  is_active: boolean;
}
