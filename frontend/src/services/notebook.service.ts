// services/notebook.service.ts
import api from "./api";
import {
  AddDocumentsToNotebookPayload,
  NotebookCreatePayload,
  NotebookDetailOut,
  NotebookOut,
  NotebookUpdatePayload,
  ToggleDocumentActivePayload,
} from "@/types/notebook";

interface BaseResponse<T = any> {
  message?: string;
  data: T;
}

class NotebookService {
  /**
   * List all notebooks owned by the current user.
   */
  async getNotebooks(): Promise<NotebookOut[]> {
    const response = await api.get<BaseResponse<NotebookOut[]>>("/notebooks/");
    return response.data.data;
  }

  /**
   * Create a new notebook.
   */
  async createNotebook(payload: NotebookCreatePayload): Promise<NotebookOut> {
    const response = await api.post<BaseResponse<NotebookOut>>(
      "/notebooks/",
      payload
    );
    return response.data.data;
  }

  /**
   * Get detail workspace of a single notebook.
   */
  async getNotebookDetail(notebookId: number): Promise<NotebookDetailOut> {
    const response = await api.get<BaseResponse<NotebookDetailOut>>(
      `/notebooks/${notebookId}`
    );
    return response.data.data;
  }

  /**
   * Update a notebook's title / description / color.
   */
  async updateNotebook(
    notebookId: number,
    payload: NotebookUpdatePayload
  ): Promise<NotebookOut> {
    const response = await api.put<BaseResponse<NotebookOut>>(
      `/notebooks/${notebookId}`,
      payload
    );
    return response.data.data;
  }

  /**
   * Delete a notebook.
   */
  async deleteNotebook(notebookId: number): Promise<string | undefined> {
    const response = await api.delete<BaseResponse<undefined>>(
      `/notebooks/${notebookId}`
    );
    return response.data.message;
  }

  /**
   * Duplicate an existing notebook.
   */
  async duplicateNotebook(notebookId: number): Promise<NotebookOut> {
    const response = await api.post<BaseResponse<NotebookOut>>(
      `/notebooks/${notebookId}/duplicate`
    );
    return response.data.data;
  }

  /**
   * Add documents to a notebook.
   */
  async addDocuments(
    notebookId: number,
    payload: AddDocumentsToNotebookPayload
  ): Promise<string | undefined> {
    const response = await api.post<BaseResponse<undefined>>(
      `/notebooks/${notebookId}/documents`,
      payload
    );
    return response.data.message;
  }

  /**
   * Remove a document from a notebook.
   */
  async removeDocument(
    notebookId: number,
    documentId: number
  ): Promise<string | undefined> {
    const response = await api.delete<BaseResponse<undefined>>(
      `/notebooks/${notebookId}/documents/${documentId}`
    );
    return response.data.message;
  }

  /**
   * Toggle document active state (for RAG / Chat context).
   */
  async toggleDocumentActive(
    notebookId: number,
    documentId: number,
    payload: ToggleDocumentActivePayload
  ): Promise<string | undefined> {
    const response = await api.patch<BaseResponse<undefined>>(
      `/notebooks/${notebookId}/documents/${documentId}/active`,
      payload
    );
    return response.data.message;
  }
}

export const notebookService = new NotebookService();