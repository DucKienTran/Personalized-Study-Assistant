// src/constants/quiz-type.ts

import { QuestionType } from "@/services/quiz.service";

export type QuizTypeId =
    | "multiple_choice"
    | "multiple_response"
    | "true_false"
    | "fill_blank"
    | "short_answer"
    | "essay"
    | "custom";

export interface QuizTypeItem {
    id: QuizTypeId;

    title: string;

    description?: string;

    iconId: QuizTypeId;

    color:
        | "blue"
        | "emerald"
        | "amber"
        | "purple"
        | "rose"
        | "cyan"
        | "slate";

    generationMode: "simple" | "custom";

    /**
     * Các QuestionType mặc định sẽ gửi cho BE.
     * Với Custom sẽ để [] và popup sẽ quyết định.
     */
    defaultQuestionTypes: QuestionType[];
}

export const QUIZ_TYPES: QuizTypeItem[] = [
    {
        id: "multiple_choice",
        title: "Multiple Choice",
        iconId: "multiple_choice",
        color: "blue",
        generationMode: "simple",
        defaultQuestionTypes: ["multiple_choice"],
    },
    {
        id: "multiple_response",
        title: "Multiple Response",
        iconId: "multiple_response",
        color: "emerald",
        generationMode: "simple",
        defaultQuestionTypes: ["multiple_response"],
    },
    {
        id: "true_false",
        title: "True / False",
        iconId: "true_false",
        color: "amber",
        generationMode: "simple",
        defaultQuestionTypes: ["true_false"],
    },
    {
        id: "fill_blank",
        title: "Fill Blank",
        iconId: "fill_blank",
        color: "purple",
        generationMode: "simple",
        defaultQuestionTypes: ["fill_blank"],
    },
    {
        id: "short_answer",
        title: "Short Answer",
        iconId: "short_answer",
        color: "rose",
        generationMode: "simple",
        defaultQuestionTypes: ["short_answer"],
    },
    {
        id: "essay",
        title: "Essay",
        iconId: "essay",
        color: "cyan",
        generationMode: "simple",
        defaultQuestionTypes: ["essay"],
    },
    {
        id: "custom",
        title: "Custom",
        description: "Tạo đề theo ý thích của bạn",
        iconId: "custom",
        color: "slate",
        generationMode: "custom",
        defaultQuestionTypes: [],
    },
];