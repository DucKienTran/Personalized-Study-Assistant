"use client";

import { useEffect, useRef, useState } from "react";

import ProcessingQuizBanner from "@/components/quizzes/ProcessingQuizBanner";
import StudyExamTabs from "@/components/quizzes/StudyExamTabs";
import RecentQuizCard from "@/components/quizzes/RecentQuizCard";

import { QUIZ_TYPES, QuizTypeId } from "@/constants/quiz-type";
import * as Icons from "@/components/shared/icons";
import { documentService } from "@/services/document.service"; 
import { 
    quizService, 
    QuizItem, 
    ProcessingQuizItem,
    QuizMode, 
    Difficulty,
    QuestionType
} from "@/services/quiz.service";

// Bảng màu 7 loại
const quizColorVariants = {
    blue: { bg: "bg-blue-50/50 border-blue-100 hover:border-blue-300 hover:bg-blue-100/50", icon: "text-blue-500" },
    emerald: { bg: "bg-emerald-50/50 border-emerald-100 hover:border-emerald-300 hover:bg-emerald-100/50", icon: "text-emerald-500" },
    amber: { bg: "bg-amber-50/50 border-amber-100 hover:border-amber-300 hover:bg-amber-100/50", icon: "text-amber-500" },
    purple: { bg: "bg-purple-50/50 border-purple-100 hover:border-purple-300 hover:bg-purple-100/50", icon: "text-purple-500" },
    rose: { bg: "bg-rose-50/50 border-rose-100 hover:border-rose-300 hover:bg-rose-100/50", icon: "text-rose-500" },
    cyan: { bg: "bg-cyan-50/50 border-cyan-100 hover:border-cyan-300 hover:bg-cyan-100/50", icon: "text-cyan-500" },
    slate: { bg: "bg-slate-50 border-slate-200 hover:border-slate-300 hover:bg-slate-100 text-slate-700", icon: "text-slate-600" }
};

const ALL_QUESTION_TYPES: { id: QuestionType; label: string }[] = [
    { id: "multiple_choice", label: "Multiple Choice" },
    { id: "multiple_response", label: "Multiple Response" },
    { id: "true_false", label: "True / False" },
    { id: "fill_blank", label: "Fill Blank" },
    { id: "short_answer", label: "Short Answer" },
    { id: "essay", label: "Essay" },
];

function renderQuizIcon(iconId: string) {
    switch (iconId) {
        case "multiple_choice": return <Icons.MultipleChoiceIcon className="w-8 h-8" />;
        case "multiple_response": return <Icons.MultipleResponseIcon className="w-8 h-8" />;
        case "true_false": return <Icons.TrueFalseIcon className="w-8 h-8" />;
        case "fill_blank": return <Icons.FillBlankIcon className="w-8 h-8" />;
        case "short_answer": return <Icons.ShortAnswerIcon className="w-8 h-8" />;
        case "essay": return <Icons.DocumentIcon className="w-8 h-8" />;
        case "custom": return <Icons.CustomQuizIcon className="w-8 h-8" />;
        default: return <Icons.DocumentIcon className="w-8 h-8" />;
    }
}

export default function QuizzesPage() {
    const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);

    // Form config
    const [mode, setMode] = useState<QuizMode>("study");
    const [selectedDocId, setSelectedDocId] = useState<number | "">("");
    const [selectedTypeId, setSelectedTypeId] = useState<QuizTypeId>("multiple_choice");
    const [difficulty, setDifficulty] = useState<Difficulty | "mixed">("medium");
    const [totalQuestions, setTotalQuestions] = useState<number>(10);
    const [targetTotalPoints, setTargetTotalPoints] = useState<number | string>(100);
    const [timeLimitMinutes, setTimeLimitMinutes] = useState<number>(15);
    
    // Tham số riêng cho Custom
    const [selectedCustomTypes, setSelectedCustomTypes] = useState<QuestionType[]>(["multiple_choice"]);
    const [isInstructionOpen, setIsInstructionOpen] = useState<boolean>(false);
    const [customInstruction, setCustomInstruction] = useState<string>("");

    // State data
    const [recentQuizzes, setRecentQuizzes] = useState<QuizItem[]>([]);
    const [processingQuizzes, setProcessingQuizzes] = useState<ProcessingQuizItem[]>([]);
    const [documents, setDocuments] = useState<{ id: number; title: string }[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [generating, setGenerating] = useState<boolean>(false);

    const [displayProcessingQuizzes, setDisplayProcessingQuizzes] =
        useState<ProcessingQuizItem[]>([]);
    const hideBannerTimer = useRef<NodeJS.Timeout | null>(null);

    const currentTypeConfig = QUIZ_TYPES.find((t) => t.id === selectedTypeId) || QUIZ_TYPES[0];

    const fetchData = async () => {
        try {
            const [quizzesRes, processingRes, docsRes] = await Promise.all([
                quizService.listQuizzes(),
                quizService.listProcessing(),
                documentService.listDocuments().catch(() => []),
            ]);

            setRecentQuizzes(quizzesRes);
            setProcessingQuizzes(processingRes);

            setDocuments(
                (docsRes || []).map((doc: any) => ({
                    id: doc.id,
                    title: doc.title || "Tài liệu không tên",
                }))
            );
        } catch (error) {
            console.error("Lỗi đồng bộ dữ liệu:", error);
        } finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        fetchData();

        const interval = setInterval(fetchData, 1000);

        return () => {
            clearInterval(interval);

            if (hideBannerTimer.current) {
                clearTimeout(hideBannerTimer.current);
            }
        };
    }, []);

    useEffect(() => {
        if (processingQuizzes.length > 0) {
            if (hideBannerTimer.current) {
                clearTimeout(hideBannerTimer.current);
                hideBannerTimer.current = null;
            }

            setDisplayProcessingQuizzes(processingQuizzes);
            return;
        }

        // Chỉ khi BE xác nhận đã xử lý xong
        if (displayProcessingQuizzes.length === 0) return;

        hideBannerTimer.current = setTimeout(() => {
            setDisplayProcessingQuizzes([]);
            hideBannerTimer.current = null;
        }, 2000);

        return () => {
            if (hideBannerTimer.current) {
                clearTimeout(hideBannerTimer.current);
                hideBannerTimer.current = null;
            }
        };
    }, [processingQuizzes, displayProcessingQuizzes.length]);

    const toggleQuestionType = (typeId: QuestionType) => {
        setSelectedCustomTypes(prev => 
            prev.includes(typeId) ? prev.filter(t => t !== typeId) : [...prev, typeId]
        );
    };

    const handleGenerateQuiz = async () => {
        if (!selectedDocId) return;

        try {
            setGenerating(true);

            // Chuẩn hóa danh sách câu hỏi: Custom thì lấy mảng chọn, Simple lấy mặc định
            const questionTypes: QuestionType[] =
                currentTypeConfig.generationMode === "custom"
                    ? selectedCustomTypes
                    : ["multiple_choice"];

            // Lấy giá trị hệ số điểm an toàn: Nếu ở Exam thì lấy số người dùng nhập, nếu trống hoặc ở Study thì mặc định là 100
            const pointsValue = mode === "exam" && targetTotalPoints !== "" ? Number(targetTotalPoints) : 100;

            // Xây dựng payload chuẩn chỉ, không truyền null để tránh lỗi 422 từ Pydantic BE
            const payload: any = {
                document_id: Number(selectedDocId),
                generation_mode: currentTypeConfig.generationMode,
                question_types: questionTypes,
                difficulty: difficulty,
                total_questions: Number(totalQuestions),
                mode: mode,
                target_total_points: pointsValue, // Mặc định 100 thay vì null
                time_limit_minutes: mode === "exam" ? Number(timeLimitMinutes) : 60 // Mặc định 60 phút ở Study
            };

            // Thêm custom instruction nếu có nhập
            if (currentTypeConfig.generationMode === "custom" && customInstruction?.trim()) {
                payload.custom_instruction = customInstruction.trim();
            }

            console.log("Payload gửi lên BE (Đã bọc chống 422):", payload);

            await quizService.generate(payload); 
            await fetchData();
            setIsCreateModalOpen(false);
            
        } catch (err: any) {
            console.error("Lỗi chi tiết khi gọi API sinh đề:", err);
            // Thay vì setError, ta bắn toast cảnh báo hoặc alert nhanh để không làm crash UI
            alert(err.response?.data?.message || "Tạo đề thất bại, vui lòng kiểm tra lại cấu hình.");
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div className="mx-auto max-w-5xl px-4 py-6 space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-gray-900">Tạo Đề Thi AI</h1>
                <p className="text-sm text-gray-500 mt-1">Chọn phương thức để bắt đầu thiết kế bộ câu hỏi.</p>
            </div>

            {displayProcessingQuizzes.length > 0 && (
            <ProcessingQuizBanner
                quizzes={displayProcessingQuizzes}
                completed={processingQuizzes.length === 0}
            />
        )}

            <div className="space-y-4">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Chọn phương thức sinh đề</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {QUIZ_TYPES.map((item) => {
                        const colorStyle = quizColorVariants[item.color] || quizColorVariants.blue;
                        return (
                            <button
                                key={item.id}
                                onClick={() => { setSelectedTypeId(item.id); setIsCreateModalOpen(true); }}
                                className={`group relative border rounded-2xl p-4 flex flex-col items-start gap-3 text-left transition-all duration-300 shadow-sm cursor-pointer hover:shadow-md hover:-translate-y-1 h-[140px] overflow-hidden ${colorStyle.bg}`}
                            >
                                <div className={`p-2 bg-white rounded-xl inline-block border border-gray-100 shadow-sm transition-transform duration-300 group-hover:scale-110 ${colorStyle.icon}`}>
                                    {renderQuizIcon(item.iconId)}
                                </div>
                                <span className="text-sm font-bold text-gray-900 block mt-1">{item.title}</span>
                            </button>
                        );
                    })}
                </div>
            </div>

            <div className="space-y-4 border-t border-gray-100 pt-6">
                <h2 className="text-base font-bold text-gray-800">Đề thi mới tạo gần đây</h2>
                {loading ? (
                    <div className="flex flex-col gap-4"><div className="h-24 w-full animate-pulse bg-gray-50 rounded-2xl border" /></div>
                ) : recentQuizzes.length === 0 ? (
                    <div className="text-center py-12 bg-gray-50/50 rounded-2xl border border-dashed text-sm text-gray-400">Chưa có đề thi nào được tạo.</div>
                ) : (
                    <div className="flex flex-col gap-4">
                        {recentQuizzes.map((quiz) => <RecentQuizCard key={quiz.id} quiz={quiz} />)}
                    </div>
                )}
            </div>

            {isCreateModalOpen && (
                <div 
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
                    onClick={() => setIsCreateModalOpen(false)}
                >
                    <div 
                        className="bg-white rounded-2xl w-full max-w-2xl max-h-[95vh] flex flex-col animate-in fade-in zoom-in-95 duration-150 shadow-2xl"
                        onClick={(e) => e.stopPropagation()}
                    >
                        
                        {/* Header */}
                        <div className="p-6 pb-4 flex items-center justify-between shrink-0">
                            <div>
                                <h3 className="text-lg font-bold text-gray-900">Thiết kế đề: {currentTypeConfig.title}</h3>
                                <p className="text-xs text-gray-400 mt-0.5">Cấu hình các thông số chi tiết để AI phân tích.</p>
                            </div>
                            <button onClick={() => setIsCreateModalOpen(false)} className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-50 transition">✕</button>
                        </div>

                        <div className="px-6 pb-6 flex-1 flex flex-col overflow-y-auto">
                            
                            {/* Tabs trải rộng 100% */}
                            <StudyExamTabs value={mode} onChange={setMode} />

                            {/* Phần điền thông tin: Nối liền mạch với tab được chọn, không có khoảng hở hay viền trắng */}
                            <div className={`border-x border-b rounded-b-2xl p-6 space-y-6 transition-colors duration-200 -mt-[1px] ${
                                mode === "study" 
                                    ? "bg-blue-100 border-blue-300" 
                                    : "bg-purple-100 border-purple-300"
                            }`}>
                                
                                {/* 1. CHỌN TÀI LIỆU */}
                                <div className="space-y-2">
                                    <label className={`block text-xs font-bold uppercase tracking-wider ${mode === "exam" ? "text-purple-900" : "text-blue-900"}`}>
                                        1. Chọn tài liệu nguồn
                                    </label>
                                    <select
                                        value={selectedDocId}
                                        onChange={(e) => setSelectedDocId(e.target.value ? Number(e.target.value) : "")}
                                        className={`w-full rounded-xl border px-4 py-3 text-sm focus:outline-none focus:ring-2 bg-white transition ${
                                            mode === "exam" 
                                                ? "border-purple-200 focus:ring-purple-600 focus:border-purple-400" 
                                                : "border-blue-200 focus:ring-blue-600 focus:border-blue-400"
                                        }`}
                                    >
                                        <option value="">-- Bấm vào đây để chọn tài liệu --</option>
                                        {documents.map((doc) => <option key={doc.id} value={doc.id}>{doc.title}</option>)}
                                    </select>
                                </div>

                                {/* 2. CHỌN LOẠI CÂU HỎI (Chỉ hiển thị khi là Custom) */}
                                {currentTypeConfig.generationMode === "custom" && (
                                    <div className="space-y-2">
                                        <label className={`block text-xs font-bold uppercase tracking-wider ${mode === "exam" ? "text-purple-900" : "text-blue-900"}`}>
                                            2. Câu hỏi bạn mong muốn
                                        </label>
                                        <div className={`grid grid-cols-2 gap-3 bg-white p-4 rounded-xl border ${mode === "exam" ? "border-purple-200" : "border-blue-200"}`}>
                                            {ALL_QUESTION_TYPES.map(type => {
                                                const isChecked = selectedCustomTypes.includes(type.id);
                                                return (
                                                    <button
                                                        key={type.id}
                                                        type="button"
                                                        onClick={() => toggleQuestionType(type.id)}
                                                        className="flex items-center space-x-3 text-left group"
                                                    >
                                                        {isChecked ? (
                                                            <Icons.CheckedBoxIcon className={`w-5 h-5 transition-colors ${mode === "exam" ? "text-purple-800" : "text-blue-700"}`} />
                                                        ) : (
                                                            <Icons.UncheckedBoxIcon className={`w-5 h-5 text-gray-300 transition-colors ${mode === "exam" ? "group-hover:text-purple-400" : "group-hover:text-blue-400"}`} />
                                                        )}
                                                        <span className={`text-sm font-medium transition-colors ${
                                                            isChecked 
                                                                ? (mode === "exam" ? "text-purple-900 font-bold" : "text-blue-900 font-bold") 
                                                                : "text-gray-600 group-hover:text-gray-900"
                                                        }`}>
                                                            {type.label}
                                                        </span>
                                                    </button>
                                                )
                                            })}
                                        </div>
                                    </div>
                                )}

                                {/* 3. CẤU HÌNH THÔNG SỐ */}
                                <div className="space-y-2">
                                    <label className={`block text-xs font-bold uppercase tracking-wider ${mode === "exam" ? "text-purple-900" : "text-blue-900"}`}>
                                        {currentTypeConfig.generationMode === "custom" ? "3." : "2."} Cấu hình thông số
                                    </label>
                                    
                                    <div className={`bg-white rounded-xl border p-5 ${mode === "exam" ? "border-purple-200" : "border-blue-200"}`}>
                                        {mode === "study" ? (
                                            /* LAYOUT CHO STUDY MODE: Xếp dọc trên 1 cột */
                                            <div className="flex flex-col gap-4">
                                                {/* Số lượng câu hỏi */}
                                                <div className="space-y-1.5">
                                                    <label className="block text-sm font-medium text-gray-700">Số lượng câu hỏi</label>
                                                    <input 
                                                        type="number" min="1" max="100"
                                                        value={totalQuestions}
                                                        onChange={(e) => setTotalQuestions(Number(e.target.value))}
                                                        className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                                                    />
                                                </div>

                                                {/* Độ khó */}
                                                <div className="space-y-1.5">
                                                    <div className="flex items-center gap-1.5">
                                                        <label className="block text-sm font-medium text-gray-700">Độ khó</label>
                                                        {difficulty === "mixed" && (
                                                            <div className="relative group flex items-center">
                                                                <Icons.InfoCircleIcon className="w-4 h-4 text-blue-600 cursor-help" />
                                                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2.5 bg-gray-800 text-white text-[11px] leading-relaxed rounded-lg shadow-xl z-50 text-center pointer-events-none">
                                                                    Các câu có độ khó khác nhau, câu có độ khó cao hơn cũng cho nhiều điểm hơn.
                                                                    <svg className="absolute text-gray-800 h-2 w-full left-0 top-full" x="0px" y="0px" viewBox="0 0 255 255"><polygon className="fill-current" points="0,0 127.5,127.5 255,0"/></svg>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                    <select
                                                        value={difficulty}
                                                        onChange={(e) => setDifficulty(e.target.value as any)}
                                                        className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                                                    >
                                                        <option value="easy">Dễ (Easy)</option>
                                                        <option value="medium">Trung bình (Medium)</option>
                                                        <option value="hard">Khó (Hard)</option>
                                                        <option value="mixed">Hỗn hợp (Mixed)</option>
                                                    </select>
                                                </div>
                                            </div>
                                        ) : (
                                            /* LAYOUT CHO EXAM MODE */
                                            <div className="space-y-5">
                                                {/* Hàng 1: Số lượng câu và Tổng điểm xếp song song */}
                                                <div className="grid grid-cols-2 gap-5">
                                                    {/* Số lượng câu hỏi */}
                                                    <div className="space-y-1.5">
                                                        <label className="block text-sm font-medium text-gray-700">Số lượng câu hỏi</label>
                                                        <input 
                                                            type="number" min="1" max="100"
                                                            value={totalQuestions}
                                                            onChange={(e) => setTotalQuestions(Number(e.target.value))}
                                                            className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-600"
                                                        />
                                                    </div>

                                                    {/* Hệ số (Tổng điểm) */}
                                                    <div className="space-y-1.5">
                                                        <label className="block text-sm font-medium text-gray-700">Hệ số (Tổng điểm)</label>
                                                        <input 
                                                            type="number" 
                                                            list="points-preset"
                                                            value={targetTotalPoints}
                                                            onChange={(e) => setTargetTotalPoints(e.target.value)}
                                                            placeholder="Nhập hoặc chọn..."
                                                            className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-600"
                                                        />
                                                        <datalist id="points-preset">
                                                            <option value="10" />
                                                            <option value="20" />
                                                            <option value="40" />
                                                            <option value="100" />
                                                        </datalist>
                                                    </div>
                                                </div>

                                                {/* Hàng bổ sung độ khó cho Exam */}
                                                <div className="space-y-1.5">
                                                    <div className="flex items-center gap-1.5">
                                                        <label className="block text-sm font-medium text-gray-700">Độ khó đề thi</label>
                                                        {difficulty === "mixed" && (
                                                            <div className="relative group flex items-center">
                                                                {/* Đã sửa: Icon thông tin chuyển màu tím đậm đồng bộ */}
                                                                <Icons.InfoCircleIcon className="w-4 h-4 text-purple-700 cursor-help" />
                                                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2.5 bg-gray-800 text-white text-[11px] leading-relaxed rounded-lg shadow-xl z-50 text-center pointer-events-none">
                                                                    Các câu có độ khó khác nhau, câu có độ khó cao hơn cũng cho nhiều điểm hơn.
                                                                    <svg className="absolute text-gray-800 h-2 w-full left-0 top-full" x="0px" y="0px" viewBox="0 0 255 255"><polygon className="fill-current" points="0,0 127.5,127.5 255,0"/></svg>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                    <select
                                                        value={difficulty}
                                                        onChange={(e) => setDifficulty(e.target.value as any)}
                                                        className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-600"
                                                    >
                                                        <option value="easy">Dễ (Easy)</option>
                                                        <option value="medium">Trung bình (Medium)</option>
                                                        <option value="hard">Khó (Hard)</option>
                                                        <option value="mixed">Hỗn hợp (Mixed)</option>
                                                    </select>
                                                </div>

                                                {/* Hàng 2 bên dưới: Thời gian thi kèm thanh trượt màu tím */}
                                                <div className="pt-4 border-t border-gray-100">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <label className="block text-sm font-medium text-gray-700">Thời gian thi</label>
                                                        <span className="text-sm font-bold text-purple-800">{timeLimitMinutes} phút</span>
                                                    </div>
                                                    {/* Đã sửa: Thanh trượt kéo chỉnh thời gian chuyển thành màu tím chuẩn accent-purple-700 */}
                                                    <input 
                                                        type="range" min="5" max="120" step="5"
                                                        value={timeLimitMinutes} 
                                                        onChange={(e) => setTimeLimitMinutes(Number(e.target.value))}
                                                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-700"
                                                    />
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* 4. INSTRUCTION */}
                                {currentTypeConfig.generationMode === "custom" && (
                                    <div className={`border-t pt-4 ${mode === "exam" ? "border-purple-300/60" : "border-blue-300/60"}`}>
                                        <button 
                                            type="button"
                                            onClick={() => setIsInstructionOpen(!isInstructionOpen)}
                                            className={`flex items-center gap-1.5 text-sm font-bold transition-colors ${
                                                mode === "exam" ? "text-purple-900 hover:text-purple-750" : "text-blue-900 hover:text-blue-750"
                                            }`}
                                        >
                                            {isInstructionOpen ? <Icons.ChevronDownIcon className="w-4 h-4" /> : <Icons.ChevronRightIcon className="w-4 h-4" />}
                                            Hướng dẫn nâng cao cho AI (Tùy chọn)
                                        </button>
                                        
                                        {isInstructionOpen && (
                                            <textarea
                                                value={customInstruction}
                                                onChange={(e) => setCustomInstruction(e.target.value)}
                                                placeholder="Ví dụ: Chỉ quét nội dung chương 3, diễn giải chi tiết bằng tiếng Việt..."
                                                className={`w-full h-24 rounded-xl border p-3 text-sm focus:outline-none focus:ring-2 mt-3 resize-none bg-white shadow-inner ${
                                                    mode === "exam" ? "border-purple-200 focus:ring-purple-600" : "border-blue-200 focus:ring-blue-600"
                                                }`}
                                            />
                                        )}
                                    </div>
                                )}

                            </div>
                        </div>
                                
                        {/* Footer hoàn chỉnh: Chứa nút tạo đề phong cách OUTLINE, hiệu ứng nảy khi bấm cực đã */}
                        <div className="p-5 border-t border-gray-100 bg-gray-50 flex items-center justify-end gap-3 rounded-b-2xl shrink-0">
                            <button
                                type="button"
                                onClick={() => setIsCreateModalOpen(false)}
                                className="px-5 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-xl transition active:scale-95"
                            >
                                Hủy bỏ
                            </button>
                            
                            <button
                                type="button"
                                onClick={handleGenerateQuiz}
                                disabled={generating || !selectedDocId || (currentTypeConfig.generationMode === "custom" && selectedCustomTypes.length === 0)}
                                className={`font-bold px-6 py-2.5 rounded-xl text-sm transition-all border-2 bg-white disabled:bg-gray-100 disabled:border-gray-200 disabled:text-gray-400 disabled:scale-100 shadow-sm transform active:scale-95 ${
                                    mode === "exam" 
                                        ? "border-purple-800 text-purple-800 hover:bg-purple-50 active:bg-purple-100" 
                                        : "border-blue-800 text-blue-800 hover:bg-blue-50 active:bg-blue-100"
                                }`}
                            >
                                {generating ? "Đang xử lý..." : "Bắt đầu tạo đề thi"}
                            </button>
                        </div>
                        
                    </div>
                </div>
            )}
        </div>
    );
}