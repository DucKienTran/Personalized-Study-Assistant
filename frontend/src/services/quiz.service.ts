import api from "./api";

interface ApiResponse<T> {
    status: string;
    message?: string;
    data: T;
}

/* =========================
 * Enums / Types
 * ========================= */

export type Difficulty = "easy" | "medium" | "hard" | "mixed";

export type QuizMode = "study" | "exam";

export type GenerationStatus =
    | "processing"
    | "completed"
    | "failed";

export type DerivedStatus =
    | "processing"
    | "failed"
    | "todo"
    | "in_progress"
    | "completed";

export type QuestionType =
    | "multiple_choice"
    | "multiple_response"
    | "true_false"
    | "fill_blank"
    | "short_answer"
    | "essay";

export type FeedbackTag =
    | "too_hard"
    | "too_easy"
    | "repetitive"
    | "not_relevant"
    | "too_shallow"
    | "too_long"
    | "too_short"
    | "not_enough_source_coverage"
    | "hallucinated";

export interface QuizFeedbackPayload {
    tags: FeedbackTag[];
    comment?: string;
}

/* =========================
 * Document
 * ========================= */

export interface QuizDocumentItem {
    id: number;
    title: string;
    created_at: string;
}

/* =========================
 * Quiz Card
 * ========================= */

export interface QuizItem {
    id: number;

    notebook_id: number;

    title: string;

    mode: QuizMode;

    total_questions: number;

    time_limit_minutes?: number | null;

    generation_strategy: "manual" | "ai_recommended";

    difficulty_distribution: Record<string, number> | null;

    generation_status: GenerationStatus;

    derived_status: DerivedStatus;

    error_message?: string | null;

    created_at: string;
}

export interface QuizDetail {
    id: number;
    notebook_id: number;
    title: string;
    mode: QuizMode;
    total_questions: number;
    time_limit_minutes?: number | null;
    generation_status: GenerationStatus;
    error_message?: string | null;
}

interface QuizDetailResponse extends Omit<QuizDetail, "total_questions"> {
    total_questions?: number;
    questions?: unknown[];
}

export interface ExamHistoryItem extends QuizItem {
    attempt_id: number;
    score: number | null;
    submitted_at: string | null;
    duration_seconds: number | null;
}

/* =========================
 * Processing Banner
 * ========================= */

export interface ProcessingQuizItem {
    id: number;

    title: string;

    difficulty: Difficulty;

    total_questions: number;

    created_at: string;

    generation_status: "processing";
}

/* =========================
 * Generate Payload
 * ========================= */

export interface GenerateQuizPayload {
    notebook_id: number;

    generation_strategy: "manual";

    question_types: QuestionType[];

    difficulty_distribution: Record<"easy" | "medium" | "hard", number>;

    total_questions: number;

    target_total_points: number;

    mode: QuizMode;

    time_limit_minutes?: number;

    custom_instruction: string | null;
}

/* =========================
 * Generate Result
 * ========================= */

export interface GenerateQuizResult {
    quiz_id: number;
    generation_status: GenerationStatus;
}

/* =========================
 * Hint
 * ========================= */

export interface QuestionHint {
    question_id: number;

    hint: string;
}

/* =========================
 * Service
 * ========================= */

export const quizService = {
    async getQuiz(quizId: number) {
        const res = await api.get<ApiResponse<QuizDetailResponse>>(`/quizzes/${quizId}`);
        const quiz = res.data.data;
        return {
            ...quiz,
            total_questions: quiz.total_questions ?? quiz.questions?.length ?? 0,
        } satisfies QuizDetail;
    },

    /**
     * Danh sách quiz của user
     */
    async listQuizzes(notebookId?: number) {
        const res = await api.get<ApiResponse<QuizItem[]>>(
            "/quizzes",
            {
                params: notebookId === undefined
                    ? undefined
                    : { notebook_id: notebookId },
            }
        );

        return res.data.data;
    },

    /**
     * Quiz đang processing
     */
    async listProcessing() {
        const res = await api.get<ApiResponse<ProcessingQuizItem[]>>(
            "/quizzes/processing"
        );

        return res.data.data;
    },

    /**
     * Sinh quiz
     */
    async generate(payload: GenerateQuizPayload) {
        const res = await api.post<ApiResponse<GenerateQuizResult>>(
            "/quizzes/generate",
            payload
        );

        return res.data.data;
    },

    async listExamHistory(notebookId: number) {
        const res = await api.get<ApiResponse<ExamHistoryItem[]>>(
            "/quizzes/exam-history",
            { params: { notebook_id: notebookId } }
        );
        return res.data.data;
    },

    async delete(quizId: number) {
        await api.delete<ApiResponse<null>>(`/quizzes/${quizId}`);
    },

    async submitFeedback(quizId: number, payload: QuizFeedbackPayload) {
        await api.post<ApiResponse<unknown>>(
            `/quizzes/${quizId}/feedback`,
            payload
        );
    },

    /**
     * Hint toàn bộ câu hỏi
     */
    async getHints(quizId: number) {
        const res = await api.get<ApiResponse<QuestionHint[]>>(
            `/quizzes/${quizId}/hints`
        );

        return res.data.data;
    },
};
