"use client";

import { QuizMode } from "@/services/quiz.service";

interface Props {
    value: QuizMode;
    onChange: (mode: QuizMode) => void;
}

export default function StudyExamTabs({ value, onChange }: Props) {
    return (
        <div className="flex w-full items-end relative">
            {/* Tab Study (Chiếm 50% chiều rộng) */}
            <button
                type="button"
                onClick={() => onChange("study")}
                className={`w-1/2 py-3.5 rounded-t-2xl border text-sm font-bold transition-all relative z-10 -mb-[1px] text-center ${
                    value === "study"
                        ? "bg-blue-100 border-blue-300 border-b-blue-100 text-blue-900"
                        : "bg-white border-transparent border-b-purple-300 text-gray-400 hover:text-gray-600"
                }`}
            >
                Study Mode
            </button>

            {/* Tab Exam (Chiếm 50% chiều rộng) */}
            <button
                type="button"
                onClick={() => onChange("exam")}
                className={`w-1/2 py-3.5 rounded-t-2xl border text-sm font-bold transition-all relative z-10 -mb-[1px] text-center ${
                    value === "exam"
                        ? "bg-purple-100 border-purple-300 border-b-purple-100 text-purple-900"
                        : "bg-white border-transparent border-b-blue-300 text-gray-400 hover:text-gray-600"
                }`}
            >
                Exam Mode
            </button>
        </div>
    );
}