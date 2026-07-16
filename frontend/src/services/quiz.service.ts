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

export type GenerationMode = "simple" | "custom";

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

    title: string;

    mode: QuizMode;

    generation_status: GenerationStatus;

    derived_status: DerivedStatus;

    error_message?: string | null;

    created_at: string;
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
    document_id: number;

    generation_mode: GenerationMode;

    question_types: QuestionType[];

    difficulty: Difficulty;

    total_questions: number;

    target_total_points?: number | null;

    mode: QuizMode;

    time_limit_minutes?: number | null;

    custom_instruction?: string;
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
    /**
     * Danh sách quiz của user
     */
    async listQuizzes() {
        const res = await api.get<ApiResponse<QuizItem[]>>(
            "/quizzes"
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