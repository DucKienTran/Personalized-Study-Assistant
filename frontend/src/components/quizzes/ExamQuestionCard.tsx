"use client";

import * as Icons from "@/components/shared/icons";

interface Option {
    id: string | number;
    option_text: string;
}

interface ExamQuestionCardProps {
    index: number;
    questionId: number;
    questionText: string;
    options: Option[];
    correctAnswer: any;
    explanations: any;
    selectedOptionId: string | number | undefined;
    onSelectOption: (optionId: string | number) => void;
    isSubmitted: boolean; // Điều khiển việc có hiển thị đáp án đúng/sai & giải thích hay không
    points?: number;
    hint?: string;
}

export default function ExamQuestionCard({
    index,
    questionId,
    questionText,
    options,
    correctAnswer,
    explanations,
    selectedOptionId,
    onSelectOption,
    isSubmitted,
    points,
    hint,
}: ExamQuestionCardProps) {
    const isAnswered = selectedOptionId !== undefined && selectedOptionId !== null;

    // Kiểm tra xem Option hiện tại có phải là Option người dùng đã chọn không
    // (giống hệt logic đã chạy đúng ở QuizQuestionCard, KHÔNG được tự rút gọn lại)
    const checkIsSelected = (opt: Option): boolean => {
        if (!isAnswered) return false;

        if (Number(selectedOptionId) === Number(opt.id)) return true;

        const optTextClean = opt.option_text.trim();
        const selStr = String(selectedOptionId).trim();
        const labelPattern = new RegExp(`^${selStr}\\s*[.\\-:]`, "i");

        if (labelPattern.test(optTextClean)) return true;
        if (optTextClean.toLowerCase() === selStr.toLowerCase()) return true;

        return false;
    };

    // Kiểm tra xem Option hiện tại có phải đáp án đúng không — hỗ trợ correctAnswer
    // là mảng nhiều phần tử (multiple_response), label ("A."), text, hoặc boolean (true_false)
    const checkIsCorrect = (opt: Option): boolean => {
        if (correctAnswer === undefined || correctAnswer === null) return false;

        if (Array.isArray(correctAnswer)) {
            return correctAnswer.some((item) => {
                if (Number(item) === Number(opt.id)) return true;

                const optTextClean = opt.option_text.trim();
                const itemStr = String(item).trim();
                const labelPattern = new RegExp(`^${itemStr}\\s*[.\\-:]`, "i");

                return (
                    labelPattern.test(optTextClean) ||
                    optTextClean.toLowerCase() === itemStr.toLowerCase()
                );
            });
        }

        if (Number(correctAnswer) === Number(opt.id)) return true;

        const optTextClean = opt.option_text.trim();
        const corrStr = String(correctAnswer).trim();
        const labelPattern = new RegExp(`^${corrStr}\\s*[.\\-:]`, "i");

        if (labelPattern.test(optTextClean)) return true;
        if (optTextClean.toLowerCase() === corrStr.toLowerCase()) return true;

        if (typeof correctAnswer === "boolean") {
            const boolStr = correctAnswer ? "true" : "false";
            const viBoolStr = correctAnswer ? "đúng" : "sai";
            const optLower = optTextClean.toLowerCase();

            return optLower === boolStr || optLower === viBoolStr;
        }

        return false;
    };

    // Đọc explanations đúng cấu trúc thật: dict key theo giá trị đáp án (correctAnswer/selectedOptionId đã stringify)
    const explanationText = (() => {
        if (!explanations) return null;
        if (typeof explanations === "string") return explanations;

        const correctKey = String(correctAnswer);
        const selectedKey =
            selectedOptionId !== undefined && selectedOptionId !== null
                ? String(selectedOptionId)
                : null;

        const wrongExplanation =
            selectedKey && selectedKey !== correctKey ? explanations[selectedKey] : null;
        const correctExplanation = explanations[correctKey];

        return { wrongExplanation, correctExplanation };
    })();

    return (
        <div data-question-id={questionId} className="bg-white/95 backdrop-blur-sm border border-purple-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 relative overflow-hidden">
            
            {/* Tiêu đề câu hỏi */}
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                    <span className="bg-purple-600 text-white font-bold rounded-lg px-2.5 py-1 text-xs shrink-0 mt-0.5 shadow-sm">
                        Câu {index + 1}
                    </span>
                    <h3 className="text-base font-semibold text-gray-800 leading-relaxed">
                        {questionText}
                    </h3>
                </div>
                {points !== undefined && (
                    <span className="text-xs font-semibold bg-purple-50 text-purple-600 px-2 py-0.5 rounded-md shrink-0">
                        {points} điểm
                    </span>
                )}
            </div>

            {/* Danh sách tùy chọn đáp án */}
            <div className="grid grid-cols-1 gap-3 mt-5 pl-0 md:pl-12">
                {options && options.map((opt) => {
                    const isCurrentOptSelected = checkIsSelected(opt);
                    const isCurrentOptCorrect = checkIsCorrect(opt);

                    let buttonStyles = "";

                    if (!isSubmitted) {
                        // CHƯA NỘP BÀI: Chỉ hiển thị trạng thái đã chọn màu TÍM trung tính, tuyệt đối không lộ đúng sai
                        if (isCurrentOptSelected) {
                            buttonStyles = "bg-purple-50 border-purple-500 text-purple-900 font-semibold shadow-sm";
                        } else {
                            buttonStyles = "bg-white border-gray-200 text-gray-700 hover:bg-purple-50/50 hover:border-purple-300 hover:text-purple-900 cursor-pointer";
                        }
                    } else {
                        // ĐÃ NỘP BÀI: Hiển thị xanh/đỏ rực rỡ để xem lại kết quả
                        if (isCurrentOptCorrect) {
                            buttonStyles = "bg-green-50/90 border-green-500 text-green-900 font-bold pointer-events-none";
                        } else if (isCurrentOptSelected) {
                            buttonStyles = "bg-red-50/90 border-red-500 text-red-900 font-bold pointer-events-none";
                        } else {
                            buttonStyles = "bg-white border-gray-100 text-gray-400 opacity-60 pointer-events-none";
                        }
                    }

                    return (
                        <button
                            key={`opt-${opt.id}`}
                            type="button"
                            disabled={isSubmitted}
                            onClick={() => onSelectOption(opt.id)}
                            className={`w-full text-left p-4 rounded-xl border text-sm font-medium transition-all duration-150 transform active:scale-[0.99] shadow-sm ${buttonStyles}`}
                        >
                            <div className="flex items-center gap-3">
                                <div className={`w-5 h-5 rounded-full border flex items-center justify-center text-xs shrink-0 ${
                                    isSubmitted && isCurrentOptCorrect
                                        ? "border-green-500 bg-green-500 text-white"
                                        : isSubmitted && isCurrentOptSelected
                                        ? "border-red-500 bg-red-500 text-white"
                                        : !isSubmitted && isCurrentOptSelected
                                        ? "border-purple-500 bg-purple-500 text-white"
                                        : "border-gray-300"
                                }`}>
                                    {isSubmitted && isCurrentOptCorrect ? "✓" : isSubmitted && isCurrentOptSelected ? "✗" : !isSubmitted && isCurrentOptSelected ? "●" : ""}
                                </div>
                                <span>{opt.option_text}</span>
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Gợi ý bài học (Chỉ hiện khi đã nộp xong và có gợi ý) */}
            {hint && isSubmitted && (
                <div className="mt-4 pl-0 md:pl-12 flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50/60 p-2.5 rounded-lg border border-amber-100/50">
                    <span className="font-bold">Gợi ý ôn tập:</span>
                    <span>{hint}</span>
                </div>
            )}

            {/* Khu vực giải thích - CHỈ HIỆN KHI ĐÃ NỘP BÀI */}
            {isSubmitted && isAnswered && (
                <div className="mt-6 pt-4 border-t border-dashed border-gray-100 pl-0 md:pl-12 animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="border border-purple-100 rounded-xl p-4 text-xs leading-relaxed bg-purple-50/60 text-purple-900">
                        <div className="flex items-start gap-2.5">
                            <Icons.InfoCircleIcon className="w-4 h-4 shrink-0 mt-0.5 text-purple-700" />
                            <div className="flex-1">
                                <span className="font-bold block mb-3 text-purple-950">Giải thích</span>

                                {typeof explanationText === "string" ? (
                                    <p className="text-gray-700">{explanationText}</p>
                                ) : (
                                    <>
                                        {explanationText?.wrongExplanation && (
                                            <div className="mb-4">
                                                <div className="font-semibold text-red-700 mb-1">Đáp án bạn chọn:</div>
                                                <p className="text-gray-700">{explanationText.wrongExplanation}</p>
                                            </div>
                                        )}
                                        <div>
                                            <div className="font-semibold text-green-700 mb-1">Đáp án đúng:</div>
                                            <p className="text-gray-700">
                                                {explanationText?.correctExplanation ?? "Chưa có giải thích"}
                                            </p>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}