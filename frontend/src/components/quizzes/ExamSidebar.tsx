"use client";

interface Option {
    id: string | number;
    option_text: string;
}

interface QuizQuestion {
    id: number;
    question_text: string;
    options: Option[];
    correct_answer: any;
    explanations: any;
    user_answer?: any;
    is_correct?: boolean | null;
}

interface ExamSidebarProps {
    questions: QuizQuestion[];
    answers: Record<number, string | number>;
    markedReview: Record<number, boolean>;
    markedCritical: Record<number, boolean>;
    currentIndex: number;
    onSelectQuestion: (index: number) => void;
    isSubmitted: boolean;
    onSubmit: () => void;
    submitting: boolean;
    timeLeft: number; // Đơn vị: Giây
    violationsCount: number;
}

export default function ExamSidebar({
    questions,
    answers,
    markedReview,
    markedCritical,
    currentIndex,
    onSelectQuestion,
    isSubmitted,
    onSubmit,
    submitting,
    timeLeft,
    violationsCount,
}: ExamSidebarProps) {
    const answeredCount = Object.keys(answers).length;
    const totalCount = questions.length;
    const progressPercentage = totalCount > 0 ? Math.round((answeredCount / totalCount) * 100) : 0;

    // Định dạng đồng hồ đếm ngược thành dạng MM:SS
    const formatTime = (seconds: number) => {
        if (seconds <= 0) return "00:00";
        const m = Math.floor(seconds / 60).toString().padStart(2, "0");
        const s = (seconds % 60).toString().padStart(2, "0");
        return `${m}:${s}`;
    };

    return (
        <div className="bg-white/95 backdrop-blur-md border border-purple-100 rounded-2xl p-5 shadow-sm space-y-5">
            
            {/* 1. Đồng hồ đếm ngược & Chỉ số vi phạm */}
            <div className="flex items-center justify-between border-b border-gray-100 pb-4">
                <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Thời gian còn lại</p>
                    <p className={`text-2xl font-black ${timeLeft < 180 && !isSubmitted ? "text-red-600 animate-pulse" : "text-purple-950"}`}>
                        {isSubmitted ? "Đã nộp" : formatTime(timeLeft)}
                    </p>
                </div>
                {!isSubmitted && (
                    <div className="text-right">
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Lần vi phạm</p>
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${
                            violationsCount > 0 ? "bg-red-100 text-red-700 animate-pulse" : "bg-green-100 text-green-700"
                        }`}>
                            {violationsCount} / 3 lần
                        </span>
                    </div>
                )}
            </div>

            {/* 2. Thanh tiến độ hoàn thành */}
            <div className="space-y-1.5">
                <div className="flex justify-between items-center text-[10px] font-bold text-gray-500 uppercase">
                    <span>Tiến độ hoàn thành</span>
                    <span className="text-purple-600 font-extrabold">{answeredCount}/{totalCount} câu</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                        className="h-full bg-purple-600 rounded-full transition-all duration-300"
                        style={{ width: `${progressPercentage}%` }}
                    />
                </div>
            </div>

            {/* 3. Ma trận ô số câu hỏi */}
            <div>
                <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-3">
                    Lưới câu hỏi điều hướng
                </h3>
                <div className="grid grid-cols-4 sm:grid-cols-5 gap-2 max-h-[280px] overflow-y-auto pr-1">
                    {questions.map((q, idx) => {
                        const isCurrent = idx === currentIndex;
                        const isAnswered = answers[q.id] !== undefined && answers[q.id] !== null;
                        const isRev = markedReview[q.id];
                        const isCrit = markedCritical[q.id];

                        let cellStyles = "bg-slate-50 border-slate-200 text-gray-600 hover:bg-slate-100";

                        if (isCurrent) {
                            cellStyles = "bg-purple-50 border-purple-600 text-purple-700 font-bold ring-2 ring-purple-100";
                        } else if (isSubmitted) {
                            if (q.is_correct) {
                                cellStyles = "bg-green-500 border-green-600 text-white font-bold";
                            } else {
                                cellStyles = "bg-red-500 border-red-600 text-white font-bold";
                            }
                        } else if (isAnswered) {
                            cellStyles = "bg-purple-600 border-purple-700 text-white font-semibold";
                        }

                        return (
                            <button
                                key={`nav-${q.id}`}
                                type="button"
                                onClick={() => onSelectQuestion(idx)}
                                className={`h-10 w-full rounded-xl border text-xs font-semibold flex flex-col items-center justify-center relative transition-all active:scale-95 cursor-pointer ${cellStyles}`}
                                title={`Đi đến câu ${idx + 1}`}
                            >
                                <span>{idx + 1}</span>

                                {/* Trạng thái cờ đánh dấu (Chỉ hiển thị khi chưa nộp bài) */}
                                {!isSubmitted && (isRev || isCrit) && (
                                    <div className="absolute -top-1 -right-1 flex gap-0.5">
                                        {isCrit && <span className="w-2.5 h-2.5 rounded-full bg-red-500 border-2 border-white shadow-sm" title="Câu quan trọng / Nghi ngờ sai" />}
                                        {isRev && <span className="w-2.5 h-2.5 rounded-full bg-amber-400 border-2 border-white shadow-sm" title="Câu cần xem lại" />}
                                    </div>
                                )}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* 4. Chú giải màu sắc bảng */}
            <div className="pt-4 border-t border-gray-100 grid grid-cols-2 gap-2 text-[10px] text-gray-500">
                <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 bg-purple-600 rounded-md inline-block"></span>
                    <span>Đã chọn đáp án</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 bg-slate-100 border border-slate-200 rounded-md inline-block"></span>
                    <span>Chưa làm</span>
                </div>
                {!isSubmitted ? (
                    <>
                        <div className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 bg-amber-400 rounded-full inline-block"></span>
                            <span>Cần xem lại (Review)</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 bg-red-500 rounded-full inline-block"></span>
                            <span>Nghi ngờ sai (Critical)</span>
                        </div>
                    </>
                ) : (
                    <>
                        <div className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 bg-green-500 rounded-md inline-block"></span>
                            <span>Câu đúng</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 bg-red-500 rounded-md inline-block"></span>
                            <span>Câu sai</span>
                        </div>
                    </>
                )}
            </div>

            {/* 5. Nút bấm nộp bài trực tiếp */}
            {!isSubmitted && (
                <button
                    type="button"
                    onClick={onSubmit}
                    disabled={submitting}
                    className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-bold rounded-xl text-sm shadow-md transition-all active:scale-95 disabled:opacity-60 cursor-pointer flex items-center justify-center gap-2"
                >
                    {submitting ? (
                        <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            <span>Đang nộp...</span>
                        </>
                    ) : (
                        <span>Nộp bài ngay</span>
                    )}
                </button>
            )}
        </div>
    );
}