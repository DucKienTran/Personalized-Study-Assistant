import api from "./api"; 
import { apiFetch } from "./api-fetch";


export interface DocumentListItem {
    id: number;
    title: string;
    status: string;
    file_type?: string;
    file_size: number;
    created_at?: string;
}

export interface DocumentOutlineItem {
    text: string;
    level: number;
    anchor: string;
}

export interface DocumentContent {
    title: string;
    file_type: string;
    total_pages: number;
    content_raw: string;
    outline: DocumentOutlineItem[];
}

interface ApiResponse<T> {
    status: string;
    data: T;
}

interface UploadResponseData {
    document_id: number;
    title: string;
    pages: number;
    status: string;
}

export const documentService = {
    async listDocuments(params?: { status_filter?: string; search?: string; skip?: number; limit?: number }) {
        const res = await api.get<ApiResponse<DocumentListItem[]>>("/documents/", { params });
        return res.data.data;
    },

    async uploadDocument(file: File): Promise<DocumentListItem> {
        const formData = new FormData();
        formData.append("file", file);
        const res = await api.post<ApiResponse<DocumentListItem>>("/documents/upload", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        return res.data.data; 
    },

    async createTextDocument(title: string, content: string): Promise<DocumentListItem> {
        const res = await api.post<ApiResponse<DocumentListItem>>("/documents/paste-text", {
            title,
            content,
        });
        return res.data.data;
    },

    async getDocument(id: number): Promise<DocumentListItem> {
        const res = await api.get<ApiResponse<DocumentListItem[]>>(
            "/documents/",
            { params: { document_id: id } }
        );

        return res.data.data[0];
    },

    async getDocumentContent(id: number): Promise<DocumentContent> {
        const res = await api.get<ApiResponse<DocumentContent>>(`/documents/${id}/content`);
        return res.data.data;
    },

    async deleteDocument(id: number): Promise<void> {
        await api.delete(`/documents/${id}`);
    },

    async getDocumentFileUrl(documentId: number): Promise<string> {
        const res = await apiFetch(`/documents/${documentId}/file-url`, { method: "GET" });
        if (!res.ok) throw new Error("Failed to get document URL");
        const body = await res.json();
        return body.data.url;
      },

    async getDocumentDownloadUrl(documentId: number): Promise<string> {
        const res = await apiFetch(`/documents/${documentId}/download-url`, { method: "GET" });
        if (!res.ok) throw new Error("Failed to get document download URL");
        const body = await res.json();
        return body.data.url;
    }
};

