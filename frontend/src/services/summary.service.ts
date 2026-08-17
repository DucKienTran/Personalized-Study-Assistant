import api from "./api";

export type SummaryLevel = "brief" | "standard" | "comprehensive";
export type SummaryFormat = "markdown" | "raw_text";

interface ApiResponse<T> {
    status: string;
    message?: string;
    data: T;
}

/* ========================================================================== */
/* Types                                                                      */
/* ========================================================================== */

export interface SummaryHistoryItem {
    id: number;
    notebook_id: number;

    title: string;

    level: SummaryLevel;
    format: SummaryFormat;

    source_document_ids: number[];

    created_at: string;
}

export interface SummaryDetail {
    id: number;
    notebook_id: number;

    notebook_title: string;

    title: string;

    level: SummaryLevel;
    format: SummaryFormat;

    instruction: string | null;

    summary_text: string;
    draft_text: string | null;

    created_at: string;
}

/* ========================================================================== */
/* Service                                                                    */
/* ========================================================================== */

export const summaryService = {
    /**
     * Generate notebook summary (does not save).
     */
    async generate(payload: {
        notebook_id: number;
        level?: SummaryLevel;
        format?: SummaryFormat;
        instruction?: string;
    }) {
        const { notebook_id, ...body } = payload;

        const res = await api.post<
            ApiResponse<{
                summary_text: string;
            }>
        >(`/notebooks/${notebook_id}/summary`, {
            level: "standard",
            format: "markdown",
            instruction: "",
            ...body,
        });

        return res.data.data.summary_text;
    },

    /**
     * Save generated summary.
     */
    async save(payload: {
        notebook_id: number;
        title: string;
        summary_text: string;

        level: SummaryLevel;
        format: SummaryFormat;
        instruction?: string;
    }) {
        const { notebook_id, ...body } = payload;

        const res = await api.post<
            ApiResponse<{
                summary_id: number;
                title: string;
                mongo_summary_id: string;
                message: string;
            }>
        >(`/notebooks/${notebook_id}/summaries`, body);

        return res.data.data;
    },

    /**
     * Update an existing summary.
     */
    async update(payload: {
        notebook_id: number;
        summary_id: number;

        summary_text: string;
        title?: string;
    }) {
        const { notebook_id, summary_id, ...body } = payload;

        const res = await api.put<
            ApiResponse<{
                summary_id: number;
                message: string;
            }>
        >(`/notebooks/${notebook_id}/summaries/${summary_id}`, body);

        return res.data.data;
    },

    /**
     * Get summary history of a notebook.
     */
    async listHistory(notebookId: number) {
        const res = await api.get<ApiResponse<SummaryHistoryItem[]>>(
            `/notebooks/${notebookId}/summaries`
        );

        return res.data.data;
    },

    /**
     * Get summary detail.
     */
    async getDetail(notebookId: number, summaryId: number) {
        const res = await api.get<ApiResponse<SummaryDetail>>(
            `/notebooks/${notebookId}/summaries/${summaryId}`
        );

        return res.data.data;
    },
};