    "use client";

    import { useState, useRef } from "react";
    import * as Icons from "@/components/shared/icons";

    interface Option {
        id: number;
        option_text: string;
    }

    interface QuestionProps {
        index: number;
        questionId: number;
        questionText: string;
        options: Option[];
        correctAnswer: any;
        explanations: any;
        selectedOptionId: number | null | undefined;
        onSelectOption: (optionId: number) => void;
        mode: "study" | "exam";
        points?: number;
        hint?: string;
    }

    // ICON BÓNG ĐÈN SVG VECTOR SIÊU ĐẸP - Hỗ trợ phát quang lấp lánh và tô vàng thông minh khi Hover/Active
    const BulbIcon = ({ className = "w-5 h-5", active = false }: { className?: string; active?: boolean }) => (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill={active ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`${className} transition-all duration-300 ${
                active 
                    ? "text-amber-500 drop-shadow-[0_0_10px_rgba(245,158,11,0.7)] animate-pulse" 
                    : "text-gray-400 hover:text-amber-400"
            }`}
        >
            {/* Bong bóng đèn thủy tinh */}
            <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A5 5 0 0 0 8 8c0 1.3.5 2.6 1.5 3.5.8.8 1.3 1.5 1.5 2.5" />
            {/* Đuôi kim loại xoáy */}
            <path d="M9 18h6" />
            <path d="M10 22h4" />
            {/* Các tia sáng lấp lánh xung quanh bóng đèn phát ra khi active */}
            {active && (
                <>
                    <line x1="12" y1="2" x2="12" y2="4" />
                    <line x1="5" y1="5" x2="6.5" y2="6.5" />
                    <line x1="2" y1="12" x2="4" y2="12" />
                    <line x1="19" y1="5" x2="17.5" y2="6.5" />
                    <line x1="22" y1="12" x2="20" y2="12" />
                </>
            )}
        </svg>
    );

    export default function QuizQuestionCard({
        index,
        questionId,
        questionText,
        options,
        correctAnswer,
        explanations,
        selectedOptionId,
        onSelectOption,
        mode,
        points,
        hint,
    }: QuestionProps) {
        
        // SỬA LỖI CRITICAL: isAnswered chỉ đúng khi option đã chọn khác cả undefined và null (đáp ứng reload F5)
        const isAnswered = selectedOptionId !== undefined && selectedOptionId !== null;
        // Kiểm tra xem Option hiện tại có phải là Option được người dùng chọn không
        const checkIsSelected = (opt: Option): boolean => {
            if (!isAnswered) return false;

            if (Number(selectedOptionId) === opt.id) return true;

            const optTextClean = opt.option_text.trim();
            const selStr = String(selectedOptionId).trim();
            const labelPattern = new RegExp(`^${selStr}\\s*[.\\-:]`, "i");

            if (labelPattern.test(optTextClean)) return true;
            if (optTextClean.toLowerCase() === selStr.toLowerCase()) return true;

            return false;
        };

        // Kiểm tra xem Option hiện tại có phải là đáp án đúng không
        const checkIsCorrect = (opt: Option): boolean => {
            if (correctAnswer === undefined || correctAnswer === null) return false;

            if (Array.isArray(correctAnswer)) {
                return correctAnswer.some((item) => {
                    if (Number(item) === opt.id) return true;

                    const optTextClean = opt.option_text.trim();
                    const itemStr = String(item).trim();
                    const labelPattern = new RegExp(`^${itemStr}\\s*[.\\-:]`, "i");

                    return (
                        labelPattern.test(optTextClean) ||
                        optTextClean.toLowerCase() === itemStr.toLowerCase()
                    );
                });
            }

            if (Number(correctAnswer) === opt.id) return true;

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
        const explanationText = (() => {
            if (!explanations) return null;

            if (typeof explanations === "string") {
                return explanations;
            }

            const correctKey = String(correctAnswer);

            const selectedKey =
                selectedOptionId !== undefined &&
                selectedOptionId !== null
                    ? String(selectedOptionId)
                    : null;

            const wrongExplanation =
                selectedKey &&
                selectedKey !== correctKey
                    ? explanations[selectedKey]
                    : null;

            const correctExplanation =
                explanations[correctKey];

            return {
                wrongExplanation,
                correctExplanation,
            };
        })();

        // Logic Quản lý Hover Gợi Ý (Hint) với độ trễ nhỏ tránh hụt chuột tắt bất ngờ
        const [showHint, setShowHint] = useState(false);
        const hintTimeoutRef = useRef<NodeJS.Timeout | null>(null);

        const handleMouseEnterHint = () => {
            if (hintTimeoutRef.current) {
                clearTimeout(hintTimeoutRef.current);
                hintTimeoutRef.current = null;
            }
            setShowHint(true);
        };

        const handleMouseLeaveHint = () => {
            if (hintTimeoutRef.current) {
                clearTimeout(hintTimeoutRef.current);
            }

            hintTimeoutRef.current = setTimeout(() => {
                setShowHint(false);
            }, 180);
        };

        return (
            <div data-question-id={questionId} className="bg-white/90 backdrop-blur-sm border border-gray-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 relative overflow-visible">
                
                {/* Tiêu đề câu hỏi */}
                <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                        <span className={`text-white font-bold rounded-lg px-2.5 py-1 text-xs shrink-0 mt-0.5 shadow-sm whitespace-nowrap ${
                            mode === "exam" ? "bg-purple-600" : "bg-blue-600"
                        }`}>
                            Câu {index + 1} {points ? `(${points}đ)` : ""}
                        </span>
                        <h3 className="text-base font-semibold text-gray-800 leading-relaxed">
                            {questionText}
                        </h3>
                    </div>

                    {/* KHU VỰC HINT (Bóng đèn thông minh) */}
                    {hint && (
                        <div className="relative shrink-0 select-none">
                            <button
                                type="button"
                                onMouseLeave={handleMouseLeaveHint}
                                onClick={() => setShowHint((prev) => !prev)}
                                className="p-1.5 hover:bg-amber-50 rounded-xl transition-all duration-200 focus:outline-none"
                                aria-label="Gợi ý đáp án"
                            >
                                <BulbIcon active={showHint} className="w-5 h-5" />
                            </button>

                            {/* Popover gợi ý bay lên trên bóng đèn */}
                            {showHint && (
                                <div
                                    onMouseEnter={handleMouseEnterHint}
                                    onMouseLeave={handleMouseLeaveHint}
                                    className="absolute right-0 bottom-full mb-3 w-72 bg-gradient-to-br from-amber-50 to-white border border-amber-200 text-amber-900 text-xs rounded-2xl p-4 shadow-xl backdrop-blur-sm z-30 animate-in fade-in slide-in-from-bottom-2 duration-200"
                                >
                                    <div className="flex items-center gap-2 mb-1.5">
                                        <span className="p-1 bg-amber-100 rounded-lg text-amber-600">
                                            <BulbIcon active className="w-3.5 h-3.5" />
                                        </span>
                                        <span className="font-extrabold text-amber-950 uppercase tracking-wide text-[10px]">
                                            Gợi ý từ hệ thống
                                        </span>
                                    </div>
                                    <p className="leading-relaxed text-gray-700 font-medium">{hint}</p>
                                    
                                    {/* Mũi tên chỉ xuống bóng đèn */}
                                    <div className="absolute top-full right-4 w-3 h-3 bg-white border-r border-b border-amber-200 rotate-45 -translate-y-1.5"></div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Danh sách các tùy chọn đáp án */}
                <div className="grid grid-cols-1 gap-3 mt-5 pl-0 md:pl-12">
                    {options && options.map((opt) => {
                        const isCurrentOptSelected = checkIsSelected(opt);
                        const isCurrentOptCorrect = checkIsCorrect(opt);

                        let buttonStyles = "";

                        if (!isAnswered) {
                            if (mode === "study") {
                                buttonStyles = "bg-white border-gray-200 text-gray-700 hover:bg-blue-50/80 hover:border-blue-400 hover:text-blue-900 cursor-pointer";
                            } else {
                                buttonStyles = "bg-white border-gray-200 text-gray-700 hover:bg-purple-50/80 hover:border-purple-400 hover:text-purple-900 cursor-pointer";
                            }
                        } else {
                            // ĐÃ BẤM CHỌN: Khóa tương tác, hiển thị màu cố định và xóa bỏ hover pointer-events
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
                                disabled={isAnswered}
                                onClick={() => onSelectOption(opt.id)}
                                className={`w-full text-left p-4 rounded-xl border text-sm font-medium transition-all duration-150 transform active:scale-[0.99] shadow-sm ${buttonStyles}`}
                            >
                                <div className="flex items-center gap-3">
                                    {/* Vòng tròn ký hiệu nhỏ trước đáp án */}
                                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center text-xs shrink-0 ${
                                        isAnswered && isCurrentOptCorrect
                                            ? "border-green-500 bg-green-500 text-white"
                                            : isAnswered && isCurrentOptSelected
                                            ? "border-red-500 bg-red-500 text-white"
                                            : "border-gray-300"
                                    }`}>
                                        {isAnswered && isCurrentOptCorrect ? "✓" : isAnswered && isCurrentOptSelected ? "✗" : ""}
                                    </div>
                                    <span>{opt.option_text}</span>
                                </div>
                            </button>
                        );
                    })}
                </div>

                {/* Khu vực Giải thích */}
                {isAnswered && (
                    <div className="mt-6 pt-4 border-t border-dashed border-gray-100 pl-0 md:pl-12 animate-in fade-in slide-in-from-top-2 duration-200">
                        <div
                            className={`border rounded-xl p-4 text-xs leading-relaxed ${
                                mode === "exam"
                                    ? "bg-purple-50/60 border-purple-100 text-purple-900"
                                    : "bg-blue-50/60 border-blue-100 text-blue-900"
                            }`}
                        >
                            <div className="flex items-start gap-2.5">
                                <Icons.InfoCircleIcon
                                    className={`w-4 h-4 shrink-0 mt-0.5 ${
                                        mode === "exam"
                                            ? "text-purple-700"
                                            : "text-blue-600"
                                    }`}
                                />

                                <div className="flex-1">
                                    <span
                                        className={`font-bold block mb-3 ${
                                            mode === "exam"
                                                ? "text-purple-950"
                                                : "text-blue-950"
                                        }`}
                                    >
                                        Giải thích
                                    </span>

                                    {typeof explanationText === "string" ? (
                                        <p className="text-gray-700">
                                            {explanationText}
                                        </p>
                                    ) : (
                                        <>
                                            {explanationText?.wrongExplanation && (
                                                <div className="mb-4">
                                                    <div className="font-semibold text-red-700 mb-1">
                                                        Đáp án bạn chọn:
                                                    </div>

                                                    <p className="text-gray-700">
                                                        {explanationText.wrongExplanation}
                                                    </p>
                                                </div>
                                            )}

                                            <div>
                                                <div className="font-semibold text-green-700 mb-1">
                                                    Đáp án đúng:
                                                </div>

                                                <p className="text-gray-700">
                                                    {explanationText?.correctExplanation ??
                                                        "Chưa có giải thích"}
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