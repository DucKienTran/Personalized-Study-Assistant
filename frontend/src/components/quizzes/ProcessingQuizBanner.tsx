"use client";

import { useEffect, useState } from "react";
import { ProcessingQuizItem } from "@/services/quiz.service";
import * as Icons from "@/components/shared/icons";

interface Props {
    quizzes: ProcessingQuizItem[];
    completed?: boolean;
}

const difficultyLabel: Record<string, string> = {
    easy: "Easy",
    medium: "Medium",
    hard: "Hard",
    mixed: "Mixed",
};

function formatRelative(createdAt: string) {
    const diff = Date.now() - new Date(createdAt).getTime();
    const minute = Math.floor(diff / 60000);

    if (minute < 1) return "Just now";
    if (minute < 60) return `${minute} minute${minute > 1 ? "s" : ""} ago`;

    const hour = Math.floor(minute / 60);
    return `${hour} hour${hour > 1 ? "s" : ""} ago`;
}

export default function ProcessingQuizBanner({
    quizzes,
    completed = false,
}: Props) {
    const [progressMap, setProgressMap] = useState<Record<number, number>>({});
    // State để quản lý việc ẩn banner khi bấm nút X
    const [isVisible, setIsVisible] = useState(true);

    /**
     * Fake progress.
     * Chạy từ từ đến 99%.
     */
    useEffect(() => {
        if (quizzes.length === 0) return;

        const interval = setInterval(() => {
            setProgressMap((prev) => {
                const next = { ...prev };

                quizzes.forEach((quiz) => {
                    const current = next[quiz.id] ?? 0;

                    if (current >= 99) return;

                    let step = 0;

                    if (current < 30) {
                        step = Math.random() * 5 + 3;
                    } else if (current < 60) {
                        step = Math.random() * 2.5 + 1.5;
                    } else if (current < 85) {
                        step = Math.random() * 1.2 + 0.5;
                    } else {
                        step = Math.random() * 0.3;
                    }

                    next[quiz.id] = Math.min(current + step, 99);
                });

                return next;
            });
        }, 450);

        return () => clearInterval(interval);
    }, [quizzes]);

    useEffect(() => {
        if (!completed) return;

        setProgressMap((prev) => {
            const next = { ...prev };

            quizzes.forEach((quiz) => {
                next[quiz.id] = 100;
            });

            return next;
        });
    }, [completed, quizzes]);

    // Khi có quiz mới nhảy vào (quizzes thay đổi), tự động hiện lại banner nếu trước đó user đã tắt
    useEffect(() => {
        if (quizzes.length > 0) {
            setIsVisible(true);
        }
    }, [quizzes.length]);

    // Nếu không có quiz hoặc user đã bấm tắt thì ẩn component
    if (quizzes.length === 0 || !isVisible) return null;

    return (
        <div className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-5 shadow-sm relative">
            
            {/* Nút X đóng banner với hiệu ứng hover và active */}
            <button
                onClick={() => setIsVisible(false)}
                className="absolute top-4 right-4 p-1.5 text-indigo-400 hover:text-indigo-600 hover:bg-indigo-100/80 active:bg-indigo-200 rounded-lg transition-all active:scale-95"
                aria-label="Đóng thông báo"
            >
                <Icons.CloseIcon className="w-5 h-5" />
            </button>

            {/* Header */}
            <div className="flex items-center gap-3 mb-5 pr-10"> {/* Thêm pr-10 để tránh đè chữ vào nút X */}
                <div className="h-10 w-10 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600">
                    <Icons.PenIcon className="w-5 h-5 animate-bounce" />
                </div>

                <div>
                    <h2 className="font-semibold text-indigo-900 text-sm md:text-base">
                        AI đang tạo bộ câu hỏi ({quizzes.length})
                    </h2>

                    <p className="text-xs text-indigo-700 mt-0.5">
                        Bạn có thể rời khỏi trang hoặc đóng thông báo này, hệ thống vẫn tiếp tục xử lý.
                    </p>
                </div>
            </div>

            {/* Processing quizzes */}
            <div className="space-y-4">
                {quizzes.map((quiz) => {
                    const progress = Math.round(progressMap[quiz.id] ?? 0);
                    const isCompleted = completed && progress >= 100;
                    return (
                        <div
                            key={quiz.id}
                            className="bg-white rounded-xl border border-indigo-100 p-4 shadow-sm"
                        >
                            <div className="flex items-start justify-between gap-4 mb-3">
                                <div className="min-w-0">
                                    <h3 className="truncate text-sm font-semibold text-gray-900">
                                        {quiz.title}
                                    </h3>

                                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                                        <span>
                                            {difficultyLabel[
                                                quiz.difficulty
                                            ] ?? quiz.difficulty}
                                        </span>

                                        <span>•</span>

                                        <span>
                                            {quiz.total_questions} questions
                                        </span>

                                        <span>•</span>

                                        <span className="text-indigo-600 font-medium">
                                            {formatRelative(
                                                quiz.created_at
                                            )}
                                        </span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 shrink-0">
                                    <div
                                        className={`h-2.5 w-2.5 rounded-full ${
                                            isCompleted
                                                ? "bg-emerald-500"
                                                : "bg-indigo-500 animate-ping"
                                        }`}
                                    />

                                    <span
                                        className={`text-[11px] font-semibold uppercase tracking-wider px-2 py-1 rounded-full ${
                                            isCompleted
                                                ? "bg-emerald-100 text-emerald-700"
                                                : "bg-indigo-100 text-indigo-700"
                                        }`}
                                    >
                                        {isCompleted ? "Completed" : "Processing"}
                                    </span>
                                </div>
                            </div>

                            {/* Progress */}
                            <div className="flex items-center justify-between text-[11px] mb-1">
                                <span
                                    className={`font-medium ${
                                        isCompleted
                                            ? "text-emerald-700"
                                            : "text-indigo-700"
                                    }`}
                                >
                                    {isCompleted ? "Hoàn thành!" : "AI đang xử lý..."}
                                </span>

                                <span
                                    className={`font-semibold ${
                                        isCompleted
                                            ? "text-emerald-700"
                                            : "text-indigo-700"
                                    }`}
                                >
                                    {progress}%
                                </span>
                            </div>

                            <div
                                className={`h-2.5 w-full rounded-full overflow-hidden ${
                                    isCompleted
                                        ? "bg-emerald-100"
                                        : "bg-indigo-100"
                                }`}
                            >
                                <div
                                    className={`h-full rounded-full transition-[width] duration-500 ease-linear ${
                                        isCompleted
                                            ? "bg-gradient-to-r from-emerald-500 to-green-500"
                                            : "bg-gradient-to-r from-indigo-500 to-sky-500"
                                    }`}
                                    style={{
                                        width: `${progress}%`,
                                    }}
                                />
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}