import { DerivedStatus } from "@/services/quiz.service";
import { QuizMode } from "@/services/quiz.service";

export function isGenerating(status: DerivedStatus) {
    return status === "processing";
}

export function canOpenQuiz(status: DerivedStatus) {
    return (
        status === "todo" ||
        status === "in_progress" ||
        status === "completed"
    );
}
export function getQuizModeLabel(mode: string) {
    return mode === "exam" ? "Exam" : "Study";
}
export function canRetry(status: DerivedStatus) {
    return status === "failed";
}

export function formatQuizMode(
    mode: QuizMode
) {
    switch (mode) {
        case "study":
            return "Study";

        case "exam":
            return "Exam";

        default:
            return mode;
    }
}