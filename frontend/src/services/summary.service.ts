import api from "./api";

export type SummaryLevel = "short" | "normal" | "detailed";
export type SummaryFormat = "paragraph" | "bullet" | "markdown";

export interface SummaryHistoryItem {
    id: number;             
    document_id: number;
    title: string;
    level: string;
    format: string;
    created_at: string;
}

export interface SummaryDetail extends SummaryHistoryItem {
    document_title: string;
    instruction: string | null;
    summary_text: string;      
    draft_text: string | null;
}

interface ApiResponse<T> { status: string; message?: string; data: T; }

export const summaryService = {
    async summarize(payload: { document_id: number; level?: SummaryLevel; format?: SummaryFormat; instruction?: string }) {
        const res = await api.post<ApiResponse<{ summary: string }>>("/documents/summarize", {
            level: "normal", format: "markdown", instruction: "", ...payload,
        });
        return res.data.data.summary;
    },

    async listHistory(documentId: number) {
        const res = await api.get<ApiResponse<SummaryHistoryItem[]>>("/documents/summaries", {
            params: { document_id: documentId },
        });
        return res.data.data;
    },

    async getDetail(summaryId: number) {
        const res = await api.get<ApiResponse<SummaryDetail>>(`/documents/summaries/${summaryId}`);
        return res.data.data;
    },

    async save(payload: { document_id: number; title: string; summary_text: string; level: string; format: string; instruction?: string }) {
        const res = await api.post<ApiResponse<{ summary_id: number; title: string; mongo_summary_id: string; message: string }>>("/documents/summaries", payload);
        return res.data.data;
    },

    async overwrite(summaryId: number, summary_text: string) {
        const res = await api.put<ApiResponse<{ summary_id: number; message: string }>>(`/documents/summaries/${summaryId}`, { summary_text }); // 👈 chỉ gửi đúng 1 field
        return res.data.data;
    },

    async listAllHistory() {
    const res = await api.get<ApiResponse<SummaryHistoryItem[]>>("/documents/summaries"); // không truyền document_id → BE trả toàn bộ của user
    return res.data.data;
},
};