import api from "./api"; 

export interface DocumentListItem {
    id: number;
    title: string;
    status: string;
    file_type?: string;
    created_at?: string;
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
    async listDocuments(params?: { status_filter?: string; skip?: number; limit?: number }) {
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

    async getDocument(id: number): Promise<DocumentListItem> {
        const res = await api.get<ApiResponse<DocumentListItem>>("/documents/", { params: { document_id: id } });
        return res.data.data;
    },

    async deleteDocument(id: number): Promise<void> {
        await api.delete(`/documents/${id}`);
    },
};

