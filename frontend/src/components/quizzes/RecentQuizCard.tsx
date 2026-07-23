"use client";

import Link from "next/link";
import * as Icons from "@/components/shared/icons";

import { QuizItem } from "@/services/quiz.service";
import { QUIZ_STATUS } from "@/constants/quiz-status";
import {
    canOpenQuiz,
    getQuizModeLabel,
} from "@/utils/quiz";
import { formatRelative } from "@/utils/date";

interface Props {
    quiz: QuizItem;
}

export default function RecentQuizCard({
    quiz,
}: Props) {
    const status = QUIZ_STATUS[quiz.derived_status];

    const content = (
        <div
            className={[
                "rounded-2xl border bg-white p-4 transition-all duration-200",
                canOpenQuiz(quiz.derived_status)
                    ? "border-gray-100 hover:border-purple-300 hover:shadow-md hover:-translate-y-0.5"
                    : "border-gray-100 opacity-80 cursor-default",
            ].join(" ")}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                    <span className="rounded-xl bg-purple-50 p-2 text-purple-600 shrink-0">
                        <Icons.PenIcon className="w-5 h-5" />
                    </span>

                    <div className="min-w-0">
                        <h3 className="truncate text-sm font-semibold text-gray-900">
                            {quiz.title}
                        </h3>

                        <p className="mt-1 text-xs text-gray-500">
                            {getQuizModeLabel(quiz.mode)}
                            {" • "}
                            {formatRelative(quiz.created_at)}
                        </p>

                        {quiz.generation_status === "failed" &&
                            quiz.error_message && (
                                <p className="mt-2 text-xs text-red-500 line-clamp-2">
                                    {quiz.error_message}
                                </p>
                            )}
                    </div>
                </div>

                <span
                    className={[
                        "shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium",
                        status.badgeClass,
                    ].join(" ")}
                >
                    {status.label}
                </span>
            </div>
        </div>
    );


    if (!canOpenQuiz(quiz.derived_status)) {
        return content;
    }

    // Logic điều hướng theo yêu cầu của bạn
    const targetHref =
        quiz.mode === "exam" && quiz.derived_status !== "completed"
            ? `/quizzes/${quiz.id}/exam`
            : `/quizzes/${quiz.id}`;

    return (
        <Link href={targetHref}>
            {content}
        </Link>
    );
}
