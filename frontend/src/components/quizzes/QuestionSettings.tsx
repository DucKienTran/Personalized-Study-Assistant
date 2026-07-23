"use client";

import { Difficulty } from "@/services/quiz.service";
import QuestionCounter from "./QuestionCounter";

interface Props {
    difficulty: Difficulty;
    totalQuestions: number;

    onDifficultyChange: (value: Difficulty) => void;
    onQuestionChange: (value: number) => void;
}

export default function QuestionSettings({
    difficulty,
    totalQuestions,
    onDifficultyChange,
    onQuestionChange,
}: Props) {
    return (
        <div className="bg-white rounded-2xl border border-gray-100 p-5 space-y-5">

            <div>

                <label className="block text-xs font-medium text-gray-500 mb-2">
                    Difficulty
                </label>

                <select
                    value={difficulty}
                    onChange={(e) =>
                        onDifficultyChange(
                            e.target.value as Difficulty
                        )
                    }
                    className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                    <option value="mixed">Mixed</option>
                </select>

            </div>

            <div>

                <label className="block text-xs font-medium text-gray-500 mb-2">
                    Number of Questions
                </label>

                <QuestionCounter
                    value={totalQuestions}
                    min={5}
                    max={100}
                    onChange={onQuestionChange}
                />

            </div>

        </div>
    );
}