import { DerivedStatus } from "@/services/quiz.service";

export interface QuizStatusMeta {
    label: string;

    badgeClass: string;
}

export const QUIZ_STATUS: Record<DerivedStatus, QuizStatusMeta> = {
    processing: {
        label: "Generating",
        badgeClass:
            "bg-blue-50 text-blue-600",
    },

    failed: {
        label: "Failed",
        badgeClass:
            "bg-red-50 text-red-600",
    },

    todo: {
        label: "Not Started",
        badgeClass:
            "bg-gray-100 text-gray-600",
    },

    in_progress: {
        label: "In Progress",
        badgeClass:
            "bg-amber-50 text-amber-600",
    },

    completed: {
        label: "Completed",
        badgeClass:
            "bg-emerald-50 text-emerald-600",
    },
}; 