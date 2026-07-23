"use client";

import { QUIZ_TYPES, QuizTypeId, QuizTypeItem } from "@/constants/quiz-type";
import * as Icons from "@/components/shared/icons";

interface QuizTypeCardProps {
    selected: QuizTypeId | null;
    onSelect: (type: QuizTypeItem) => void;
}

function renderIcon(iconId: QuizTypeItem["iconId"]) {
    switch (iconId) {
        case "multiple_choice":
            return <Icons.MultipleChoiceIcon className="w-8 h-8" />;

        case "multiple_response":
            return <Icons.MultipleResponseIcon className="w-8 h-8" />;

        case "true_false":
            return <Icons.TrueFalseIcon className="w-8 h-8" />;

        case "fill_blank":
            return <Icons.FillBlankIcon className="w-8 h-8" />;

        case "short_answer":
            return <Icons.ShortAnswerIcon className="w-8 h-8" />;

        case "essay":
            return <Icons.DocumentIcon className="w-8 h-8" />;

        case "custom":
            return <Icons.CustomQuizIcon className="w-8 h-8" />;

        default:
            return <Icons.DocumentIcon className="w-8 h-8" />;
    }
}

const colorMap: Record<
    QuizTypeItem["color"],
    {
        active: string;
        icon: string;
    }
> = {
    blue: {
        active: "border-blue-500 bg-blue-50",
        icon: "text-blue-600",
    },
    emerald: {
        active: "border-emerald-500 bg-emerald-50",
        icon: "text-emerald-600",
    },
    amber: {
        active: "border-amber-500 bg-amber-50",
        icon: "text-amber-600",
    },
    purple: {
        active: "border-purple-500 bg-purple-50",
        icon: "text-purple-600",
    },
    rose: {
        active: "border-rose-500 bg-rose-50",
        icon: "text-rose-600",
    },
    cyan: {
        active: "border-cyan-500 bg-cyan-50",
        icon: "text-cyan-600",
    },
    slate: {
        active: "border-slate-500 bg-slate-50",
        icon: "text-slate-600",
    },
};

export default function QuizTypeCard({
    selected,
    onSelect,
}: QuizTypeCardProps) {
    return (
        <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-900">
                Question Types
            </h3>

            <div className="grid grid-cols-4 gap-3">
                {QUIZ_TYPES.map((item) => {
                    const active = selected === item.id;
                    const color = colorMap[item.color];

                    return (
                        <button
                            key={item.id}
                            type="button"
                            onClick={() => onSelect(item)}
                            className={[
                                "group relative h-28 rounded-2xl border transition-all duration-200",
                                "flex flex-col items-center justify-center gap-3",
                                active
                                    ? `${color.active} ring-2 ring-offset-1 ring-gray-200`
                                    : "border-gray-200 bg-white hover:border-gray-300 hover:-translate-y-0.5 hover:shadow-sm",
                            ].join(" ")}
                        >
                            <div
                                className={
                                    active
                                        ? color.icon
                                        : "text-gray-500 group-hover:text-gray-700"
                                }
                            >
                                {renderIcon(item.iconId)}
                            </div>

                            <span
                                className={
                                    active
                                        ? "text-sm font-semibold text-gray-900"
                                        : "text-sm font-medium text-gray-700"
                                }
                            >
                                {item.title}
                            </span>

                            {item.id === "custom" && item.description && (
                                <p className="absolute bottom-3 left-3 right-3 text-[11px] leading-4 text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                    {item.description}
                                </p>
                            )}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}