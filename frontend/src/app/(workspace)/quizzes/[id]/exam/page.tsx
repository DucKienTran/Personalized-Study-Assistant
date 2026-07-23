"use client";

import { useEffect, useState, useRef, use } from "react";
import { useRouter } from "next/navigation";
import api from "@/services/api";
import QuizQuestionCard from "@/components/quizzes/QuizQuestionCard";
import ExamQuestionCard from "@/components/quizzes/ExamQuestionCard";
import ExamSidebar from "@/components/quizzes/ExamSidebar";
import { useToast, ToastContainer } from "@/components/shared/Toast";
import ConfirmButton from "@/components/shared/ConfirmButton";

interface Option {
    id: string | number;
    option_text: string;
}

interface QuizQuestion {
    id: number;
    question_text: string;
    question_type: string;
    options: Option[];
    correct_answer: any;
    explanations: any;
    user_answer?: any;
    is_correct?: boolean | null;
    points?: number;
    hint?: string;
}

interface QuizDetails {
    id: number;
    title: string;
    mode: "study" | "exam";
    total_questions: number;
    target_total_points: number;
    questions: QuizQuestion[];
}

interface Props {
    params: Promise<{ id: string }>;
}

export default function QuizDoingPage({ params }: Props) {
    const router = useRouter();
    const { id: quizIdStr } = use(params);
    const quizId = Number(quizIdStr);

    const [quiz, setQuiz] = useState<QuizDetails | null>(null);
    const [loading, setLoading] = useState(true);
    const [answers, setAnswers] = useState<Record<number, string | number>>({});
    const [submitting, setSubmitting] = useState(false);
    const [examResult, setExamResult] = useState<any>(null);

    // QUẢN LÝ RIÊNG CHO EXAM MODE (SINGLE-QUESTION VÀ MARKING)
    const [currentIndex, setCurrentIndex] = useState(0);
    const [markedReview, setMarkedReview] = useState<Record<number, boolean>>({});
    const [markedCritical, setMarkedCritical] = useState<Record<number, boolean>>({});

    // QUẢN LÝ BẢO MẬT & CHỐNG GIAN LẬN (PROCTORING SHIELD)
    const [violations, setViolations] = useState(0);
    const [isOnline, setIsOnline] = useState(true);
    const [offlineSeconds, setOfflineSeconds] = useState(0);
    const [timeLeft, setTimeLeft] = useState(1800); // Mặc định 30 phút

    // Sử dụng Refs để lưu dữ liệu tức thời tránh bug stale closure trong event listeners
    const answersRef = useRef(answers);
    const quizRef = useRef(quiz);
    const isSubmittedRef = useRef(false);

    const { toasts, showToast, dismissToast } = useToast();


    useEffect(() => { answersRef.current = answers; }, [answers]);
    useEffect(() => { quizRef.current = quiz; }, [quiz]);
    
    const isSubmitted = quiz?.mode === "study"
        ? (quiz.questions && Object.keys(answers).length >= quiz.questions.length)
        : examResult !== null;

    useEffect(() => { isSubmittedRef.current = isSubmitted; }, [isSubmitted]);

    // 1. Tải thông tin bài làm / phòng thi từ API
    useEffect(() => {
        async function loadQuizData() {
            try {
                setLoading(true);
                const res = await api.get(`/quizzes/${quizId}`);
                const quizData = res.data.data;
                setQuiz(quizData);

                if (quizData && quizData.questions) {
                    const initialAnswers: Record<number, string | number> = {};
                    quizData.questions.forEach((q: any) => {
                        if (q.user_answer !== null && q.user_answer !== undefined) {
                            initialAnswers[q.id] = q.user_answer;
                        }
                    });
                    setAnswers(initialAnswers);
                    
                    // Thiết lập thời gian thi tương ứng số lượng câu hỏi (ví dụ: 2 phút một câu)
                    setTimeLeft(quizData.questions.length * 120);
                }
            } catch (err) {
                console.error("Lỗi khi tải chi tiết bài làm:", err);
                alert("Không thể tải thông tin phòng học.");
                router.push("/quizzes");
            } finally {
                setLoading(false);
            }
        }
        if (quizId) loadQuizData();
    }, [quizId, router]);

    // 2. Bộ đếm ngược thời gian làm bài (Chỉ kích hoạt ở Exam Mode)
    useEffect(() => {
        if (!quiz || quiz.mode !== "exam" || isSubmitted) return;

        const interval = setInterval(() => {
            setTimeLeft((prev) => {
                if (prev <= 1) {
                    clearInterval(interval);
                    showToast("Thời gian làm bài đã hết, đang tự động thu bài...", "warning")
                    handleAutoSubmitExam("hết_giờ_làm_bài");
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(interval);
    }, [quiz, isSubmitted]);

    // 3. Cơ chế Proctoring Shield (Nhận diện chuyển Tab, mất tiêu điểm, rời chuột, Split-view)
    useEffect(() => {
        if (!quiz || quiz.mode !== "exam" || isSubmitted) return;

        const triggerViolation = (reason: string) => {
            if (isSubmittedRef.current) return;
            setViolations((prev) => {
                const nextViolations = prev + 1;
                if (nextViolations >= 3) {
                    showToast(`PHÁT HIỆN GIAN LẬN QUÁ GIỚI HẠN (3/3)!\nLý do: ${reason}\nHệ thống tự động khóa và nộp bài!`, "danger");                    handleAutoSubmitExam("vi_phạm_quy_chế_quá_3_lần");
                    return 3;
                } else {
                    showToast(`CẢNH BÁO VI PHẠM PHÒNG THI (${nextViolations}/3)!\nHành vi: ${reason}`, "warning");                    return nextViolations;
                }
            });
        };

        const handleVisibilityChange = () => {
            if (document.hidden) triggerViolation("Chuyển Tab trình duyệt (Tab Switch)");
        };

        const handleBlur = () => {
            triggerViolation("Mất tiêu điểm cửa sổ thi (Rời khỏi ứng dụng)");
        };

        const handleMouseLeave = (e: MouseEvent) => {
            if (e.clientY < 0) triggerViolation("Di chuột ra ngoài phạm vi màn hình làm bài");
        };

        let lastWidth = window.innerWidth;
        const handleResize = () => {
            // Nhận diện hành vi bóp nhỏ kích thước màn hình để chia đôi (Split-view)
            if (window.innerWidth < 1024 && lastWidth >= 1024) {
                triggerViolation("Thay đổi kích thước cửa sổ / Bật chế độ Split-View");
            }
            lastWidth = window.innerWidth;
        };

        document.addEventListener("visibilitychange", handleVisibilityChange);
        window.addEventListener("blur", handleBlur);
        document.addEventListener("mouseleave", handleMouseLeave);
        window.addEventListener("resize", handleResize);

        return () => {
            document.removeEventListener("visibilitychange", handleVisibilityChange);
            window.removeEventListener("blur", handleBlur);
            document.removeEventListener("mouseleave", handleMouseLeave);
            window.removeEventListener("resize", handleResize);
        };
    }, [quiz, isSubmitted]);

    // 4. Phát hiện mất kết nối mạng và xử lý sau 15 giây liên tục
    useEffect(() => {
        if (!quiz || quiz.mode !== "exam" || isSubmitted) return;

        const handleOnline = () => {
            setIsOnline(true);
            setOfflineSeconds(0);
        };

        const handleOffline = () => {
            setIsOnline(false);
            showToast("Bạn đang bị ngắt mạng Internet! Nếu kéo dài quá 15s hệ thống sẽ tự động nộp bài.", "danger");        };

        window.addEventListener("online", handleOnline);
        window.addEventListener("offline", handleOffline);

        return () => {
            window.removeEventListener("online", handleOnline);
            window.removeEventListener("offline", handleOffline);
        };
    }, [quiz, isSubmitted]);

    useEffect(() => {
        if (isOnline || isSubmitted) return;

        const timer = setInterval(() => {
            setOfflineSeconds((prev) => {
                const next = prev + 1;
                if (next >= 15) {
                    clearInterval(timer);
                    showToast("Đã ngắt mạng quá 15 giây liên tục! Đang thực hiện nộp bài khẩn cấp.", "danger");                    handleAutoSubmitExam("mất_kết_nối_mạng_quá_15s");
                    return 15;
                }
                return next;
            });
        }, 1000);

        return () => clearInterval(timer);
    }, [isOnline, isSubmitted]);

    // 5. Ngăn cản người dùng vô tình reload trang hoặc back
    useEffect(() => {
        if (!quiz || quiz.mode !== "exam" || isSubmitted) return;

        const preventReload = (e: BeforeUnloadEvent) => {
            e.preventDefault();
        };

        window.addEventListener("beforeunload", preventReload);
        return () => window.removeEventListener("beforeunload", preventReload);
    }, [quiz, isSubmitted]);

    // Hàm thực hiện thu bài nộp tự động khi vi phạm / sập mạng / hết giờ
    const handleAutoSubmitExam = async (reason: string) => {
        if (isSubmittedRef.current) return;
        setSubmitting(true);
        try {
            const currentQuiz = quizRef.current;
            if (!currentQuiz) return;

            const answersPayload = currentQuiz.questions.map((q) => ({
                question_id: q.id,
                user_answer: answersRef.current[q.id] !== undefined ? answersRef.current[q.id] : null,
            }));

            const res = await api.post(`/quizzes/${quizId}/submit`, {
                answers: answersPayload,
                submit_reason: `auto_submit_${reason}`,
            });

            const result = res.data.data;
            setExamResult(result);

            setQuiz((prevQuiz) => {
                if (!prevQuiz) return null;
                const updatedQuestions = prevQuiz.questions.map((q) => {
                    const qDetail = result.details.find((d: any) => d.question_id === q.id);
                    return {
                        ...q,
                        correct_answer: qDetail?.correct_answer,
                        explanations: qDetail?.explanations,
                        user_answer: qDetail?.user_answer,
                        is_correct: qDetail?.is_correct,
                    };
                });
                return {
                    ...prevQuiz,
                    questions: updatedQuestions,
                };
            });

            showToast(`Đã tự động thu bài thành công!\nĐiểm đạt được: ${result.score}/${result.score_scale}`, "success");            
            setCurrentIndex(0); // Trở về câu đầu tiên để xem đáp án giải thích
        } catch (err) {
            console.error("Lỗi khi tự động nộp bài:", err);
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-[#eef6ff]">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                    <div className="text-sm font-semibold text-purple-600 animate-pulse">
                        Đang đồng bộ hóa phòng kiểm tra...
                    </div>
                </div>
            </div>
        );
    }

    if (!quiz) return null;

    const answeredCount = Object.keys(answers).length;
    const totalCount = quiz.questions?.length || 0;

    const isStudyCompleted = quiz.mode === "study" && answeredCount >= totalCount;
    const isExamSubmitted = examResult !== null;

    const correctCount = quiz.questions.filter((q) => q.is_correct).length;
    const earnedPoints = quiz.questions.reduce((sum, q) => {
        if (q.is_correct) {
            return sum + (q.points ?? 0);
        }
        return sum;
    }, 0);

    const showCorrectAnswers = quiz.mode === "study" || isSubmitted;
    
    const progressPercentage = showCorrectAnswers
        ? Math.round((earnedPoints / quiz.target_total_points) * 100)
        : Math.round((answeredCount / totalCount) * 100);

    // Sự kiện xử lý bấm chọn đáp án
    const handleAnswerQuestion = async (questionId: number, optionId: string | number) => {
        const nextAnswers = {
            ...answers,
            [questionId]: optionId,
        };
        setAnswers(nextAnswers);

        // Chế độ ôn tập (Lưu ngay & Hiện giải thích cuốn chiếu)
        if (quiz.mode === "study") {
            try {
                const res = await api.post(
                    `/quizzes/${quizId}/questions/${questionId}/answer`,
                    { user_answer: optionId }
                );

                const result = res.data.data;

                setQuiz((prevQuiz) => {
                    if (!prevQuiz) return null;
                    return {
                        ...prevQuiz,
                        questions: prevQuiz.questions.map((q) =>
                            q.id === questionId
                                ? {
                                    ...q,
                                    user_answer: optionId,
                                    correct_answer: result.correct_answer,
                                    explanations: result.explanations,
                                    is_correct: result.is_correct,
                                }
                                : q
                        ),
                    };
                });
            } catch (err) {
                console.error(err);
                setAnswers((prev) => {
                    const rollback = { ...prev };
                    delete rollback[questionId];
                    return rollback;
                });
                showToast("Không thể lưu kết quả câu hỏi.", "danger");
            }
        }
    };

    // Làm mới tiến trình (Chỉ hiện khi đã thi xong hoặc ở chế độ học)
    const doResetQuiz = async () => {
        
        try {
            if (quiz.mode === "study") {
                await api.delete(`/quizzes/${quizId}/progress`);
            }
            setAnswers({});
            setExamResult(null);
            setViolations(0);
            setCurrentIndex(0);
            setMarkedReview({});
            setMarkedCritical({});

            setQuiz((prevQuiz) => {
                if (!prevQuiz) return null;
                return {
                    ...prevQuiz,
                    questions: prevQuiz.questions.map((q) => ({
                        ...q,
                        user_answer: null,
                        correct_answer: null,
                        explanations: null,
                        is_correct: null,
                    })),
                };
            });
            window.scrollTo({ top: 0, behavior: "smooth" });
        } catch (err) {
            console.error("Lỗi làm mới:", err);
            showToast("Không thể xóa tiến trình cũ.", "danger");
        }
        
    };

    // Nộp bài thi thủ công (Exam Mode)
    const doSubmitExam = async () => {
        const unanswered = quiz.questions.filter((q) => answers[q.id] === undefined).length;
        let confirmMsg = "Bạn có chắc muốn nộp bài thi ngay?";
        if (unanswered > 0) {
            confirmMsg = `Cảnh báo: Bạn còn ${unanswered} câu chưa chọn đáp án. Bạn vẫn muốn nộp bài chứ?`;
        }
       
        try {
            setSubmitting(true);
            const answersPayload = quiz.questions.map((q) => ({
                question_id: q.id,
                user_answer: answers[q.id] !== undefined ? answers[q.id] : null,
            }));

            const res = await api.post(`/quizzes/${quizId}/submit`, {
                answers: answersPayload,
                submit_reason: "user_click",
            });

            const result = res.data.data;
            setExamResult(result);
                showToast(`Nộp bài thành công! Điểm số: ${result.score}/${result.score_scale}`, "success");
            setQuiz((prevQuiz) => {
                if (!prevQuiz) return null;
                return {
                    ...prevQuiz,
                    questions: prevQuiz.questions.map((q) => {
                        const qDetail = result.details.find((d: any) => d.question_id === q.id);
                        return {
                            ...q,
                            correct_answer: qDetail?.correct_answer,
                            explanations: qDetail?.explanations,
                            user_answer: qDetail?.user_answer,
                            is_correct: qDetail?.is_correct,
                        };
                    }),
                };
            });
            
            // Đưa người dùng về câu số 1 để xem lại chi tiết lỗi sai
            setCurrentIndex(0);
        } catch (err) {
            console.error("Lỗi khi nộp bài:", err);
            showToast("Nộp bài thi thất bại. Vui lòng thử lại.", "danger");
        } finally {
            setSubmitting(false);
        }
        
    };

    const currentQuestion = quiz.questions[currentIndex];
    const unansweredCount = quiz.questions.filter((q) => answers[q.id] === undefined).length;
    const submitArmedLabel = unansweredCount > 0 
        ? `Còn ${unansweredCount} câu chưa làm! Bấm lần nữa để nộp` 
        : "Bấm lần nữa để xác nhận nộp";

    return (
        <div className="min-h-screen w-full relative bg-[#f1f6fc] pb-20 overflow-x-hidden">
            <ToastContainer toasts={toasts} onDismiss={dismissToast} />
            {/* Overlay phong tỏa khi mất mạng kéo dài */}
            {!isOnline && quiz.mode === "exam" && !isSubmitted && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex flex-col items-center justify-center text-white px-4">
                    <div className="w-14 h-14 border-4 border-red-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                    <h2 className="text-xl font-bold text-red-500 mb-2">ĐÃ MẤT KẾT NỐI INTERNET</h2>
                    <p className="text-sm text-gray-300 text-center max-w-md">
                        Đang đồng bộ mạng... Hệ thống phòng thi an toàn sẽ tự động nộp bài nếu mất mạng liên tục: <span className="font-extrabold text-red-400">{offlineSeconds} / 15 giây</span>.
                    </p>
                </div>
            )}

            <div className="relative max-w-6xl mx-auto px-4 pt-8 z-10">
                
                {/* TIÊU ĐỀ PHÒNG THI / PHÒNG HỌC */}
                <div className="bg-white/95 backdrop-blur-md border border-purple-100 rounded-2xl p-6 shadow-sm mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <span className={`inline-block text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-md mb-2.5 shadow-sm ${
                            quiz.mode === "exam" 
                                ? "bg-purple-100 text-purple-800 border border-purple-200" 
                                : "bg-blue-100 text-blue-800 border border-blue-200"
                        }`}>
                            {quiz.mode === "exam" ? "Hệ Thống Phòng Thi Độc Lập (Exam Mode)" : "Phòng Tự Học Ôn Tập (Study Mode)"}
                        </span>
                        <h1 className="text-xl font-bold text-gray-900 leading-snug">{quiz.title}</h1>
                    </div>
                    
                    {isSubmitted ? (
                        <button
                            onClick={() => router.push("/quizzes")}
                            className="px-4 py-2 bg-white hover:bg-red-50 border border-red-200 text-red-600 text-sm font-medium rounded-xl transition-all shadow-sm"
                        >
                            Rời khỏi
                        </button>
                    ) : (
                        <ConfirmButton
                            idleLabel="Rời khỏi"
                            armedLabel="Bấm lần nữa để rời (mất tiến trình)"
                            onConfirm={() => router.push("/quizzes")}
                            className="px-4 py-2 bg-white hover:bg-red-50 border border-red-200 text-red-600 text-sm font-medium rounded-xl transition-all shadow-sm"
                            armedClassName="px-4 py-2 bg-red-600 text-white border border-red-600 text-sm font-medium rounded-xl shadow-md"
                        />
                    )}
                </div>

                {/* HIỂN THỊ KẾT QUẢ SAU KHI HOÀN THÀNH (STUDY MODE) */}
                {quiz.mode === "study" && isStudyCompleted && (
                    <div className="bg-gradient-to-r from-emerald-500 to-teal-600 border border-emerald-400 rounded-2xl p-6 shadow-md text-white mb-6">
                        <h2 className="text-lg font-bold mb-2">Bạn đã hoàn thành bài ôn tập!</h2>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs">Điểm đạt được</p>
                                <p className="text-2xl font-black">{earnedPoints}/{quiz.target_total_points}</p>
                            </div>
                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs">Tỷ lệ hoàn thành</p>
                                <p className="text-2xl font-black">{progressPercentage}%</p>
                            </div>
                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs">Số câu đúng</p>
                                <p className="text-2xl font-black">{correctCount}/{totalCount}</p>
                            </div>
                            <div className="bg-white/10 rounded-xl p-3 text-center flex items-center justify-center">
                                <span className="px-3 py-1 bg-white text-emerald-700 font-bold rounded-lg text-xs">HOÀN THÀNH</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* HIỂN THỊ KẾT QUẢ KHI NỘP THÀNH CÔNG (EXAM MODE) */}
                {quiz.mode === "exam" && isSubmitted && examResult && (
                    <div className="bg-gradient-to-r from-purple-600 to-indigo-600 border border-purple-400 rounded-2xl p-6 shadow-md text-white mb-6">
                        <h2 className="text-lg font-bold mb-1">Báo cáo kết quả bài kiểm tra chính thức</h2>
                        <p className="text-xs text-purple-100 mb-4">Hồ sơ điểm thi đã được tự động lưu trữ trên cơ sở dữ liệu hệ thống.</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs text-purple-200">Tổng điểm đạt</p>
                                <p className="text-2xl font-black">{examResult.score} / {examResult.score_scale}</p>
                            </div>
                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs text-purple-200">Tỷ lệ chính xác</p>
                                <p className="text-2xl font-black">
                                    {examResult.total_questions > 0 ? Math.round((examResult.correct_answers_count / examResult.total_questions) * 100) : 0}%
                                </p>
                            </div>
                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs text-purple-200">Số câu đúng</p>
                                <p className="text-2xl font-black">{examResult.correct_answers_count} / {examResult.total_questions}</p>
                            </div>
                            <div className="bg-white/10 rounded-xl p-3 text-center flex items-center justify-center">
                                <span className="px-3 py-1 bg-white text-purple-700 font-bold rounded-lg text-xs">ĐÃ NỘP BÀI</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* GIAO DIỆN CHIA MÀN HÌNH TÙY THEO CHẾ ĐỘ CHỌN */}
                {quiz.mode === "exam" ? (
                    
                    /* ============================================== */
                    /* GIAO DIỆN PHÒNG THI CHUYÊN NGHIỆP (EXAM MODE)  */
                    /* ============================================== */
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
                        
                        {/* CỘT LÀM BÀI: MỖI CÂU HIỂN THỊ 1 TRANG */}
                        <div className="lg:col-span-3 space-y-6">
                            {currentQuestion && (
                                <>
                                    <ExamQuestionCard
                                        index={currentIndex}
                                        questionId={currentQuestion.id}
                                        questionText={currentQuestion.question_text}
                                        options={currentQuestion.options}
                                        correctAnswer={currentQuestion.correct_answer}
                                        explanations={currentQuestion.explanations}
                                        selectedOptionId={answers[currentQuestion.id]}
                                        onSelectOption={(optId) => handleAnswerQuestion(currentQuestion.id, optId)}
                                        isSubmitted={isSubmitted}
                                        points={currentQuestion.points}
                                        hint={currentQuestion.hint}
                                    />

                                    {/* PHÍM ĐIỀU HƯỚNG DƯỚI CÂU HỎI */}
                                    <div className="bg-white/95 backdrop-blur-sm border border-purple-100 p-4 rounded-2xl shadow-sm flex flex-wrap items-center justify-between gap-3">
                                        <div className="flex gap-2">
                                            <button
                                                type="button"
                                                disabled={currentIndex === 0}
                                                onClick={() => setCurrentIndex((p) => p - 1)}
                                                className="px-4 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 rounded-xl text-xs font-bold transition disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
                                            >
                                                ← Câu trước
                                            </button>
                                            
                                            {currentIndex < quiz.questions.length - 1 ? (
                                                <button
                                                    type="button"
                                                    onClick={() => setCurrentIndex((p) => p + 1)}
                                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold shadow-sm transition cursor-pointer"
                                                >
                                                    Câu tiếp theo →
                                                </button>
                                            ) : (
                                                !isSubmitted && (
                                                    <ConfirmButton
                                                        idleLabel="Nộp bài thi"
                                                        armedLabel={submitArmedLabel}
                                                        onConfirm={doSubmitExam}
                                                        className="px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl text-xs font-bold shadow-md transition"
                                                        armedClassName="px-4 py-2 bg-amber-500 text-white rounded-xl text-xs font-bold shadow-md transition"
                                                    />
                                                )
                                            )}
                                        </div>

                                        {/* Cờ đánh dấu câu hỏi đặc biệt */}
                                        {!isSubmitted && (
                                            <div className="flex gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => setMarkedReview(p => ({ ...p, [currentQuestion.id]: !p[currentQuestion.id] }))}
                                                    className={`px-3 py-2 border rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer ${
                                                        markedReview[currentQuestion.id]
                                                            ? "bg-amber-100 border-amber-300 text-amber-800"
                                                            : "bg-white border-gray-200 text-gray-500 hover:bg-amber-50"
                                                    }`}
                                                >
                                                    <span>🚩</span>
                                                    <span>{markedReview[currentQuestion.id] ? "Gỡ cờ" : "Cần xem lại"}</span>
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => setMarkedCritical(p => ({ ...p, [currentQuestion.id]: !p[currentQuestion.id] }))}
                                                    className={`px-3 py-2 border rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer ${
                                                        markedCritical[currentQuestion.id]
                                                            ? "bg-red-100 border-red-300 text-red-800"
                                                            : "bg-white border-gray-200 text-gray-500 hover:bg-red-50"
                                                    }`}
                                                >
                                                    <span>⚠️</span>
                                                    <span>{markedCritical[currentQuestion.id] ? "Gỡ quan trọng" : "Nghi ngờ sai"}</span>
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>

                        {/* CỘT PHẢI: COMPONENT ĐIỀU HƯỚNG TÁCH BIỆT */}
                        <div className="lg:col-span-1 lg:sticky lg:top-6">
                            <ExamSidebar
                                questions={quiz.questions}
                                answers={answers}
                                markedReview={markedReview}
                                markedCritical={markedCritical}
                                currentIndex={currentIndex}
                                onSelectQuestion={(idx) => setCurrentIndex(idx)}
                                isSubmitted={isSubmitted}
                                onSubmit={doSubmitExam}
                                submitting={submitting}
                                timeLeft={timeLeft}
                                violationsCount={violations}
                            />
                        </div>

                    </div>
                ) : (
                    
                    /* ============================================== */
                    /* GIAO DIỆN ÔN TẬP CUỐN CHIẾU (STUDY MODE)       */
                    /* ============================================== */
                    <div className="max-w-4xl mx-auto space-y-6">
                        
                        {/* DANH SÁCH TOÀN BỘ CÂU HỎI */}
                        <div className="space-y-6">
                            {quiz.questions.map((q: any, idx: number) => (
                                <QuizQuestionCard
                                    key={q.id}
                                    index={idx}
                                    questionId={q.id}
                                    questionText={q.question_text}
                                    options={q.options}
                                    correctAnswer={q.correct_answer}
                                    explanations={q.explanations}
                                    selectedOptionId={answers[q.id] !== undefined ? (answers[q.id] as number) : q.user_answer} 
                                    onSelectOption={(optionId) => handleAnswerQuestion(q.id, optionId)}
                                    mode={quiz.mode}
                                />
                            ))}
                        </div>

                        {/* THANH TIẾN ĐỘ CHẾ ĐỘ HỌC */}
                        <div className="bg-white/90 backdrop-blur-md border border-blue-100 rounded-2xl p-5 shadow-sm mt-8 space-y-2.5">
                            <div className="flex items-center justify-between text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <span>{showCorrectAnswers ? "Kết quả chính xác đạt được" : "Tiến độ làm bài"}</span>
                                <span className="text-blue-600 font-extrabold">
                                    {showCorrectAnswers
                                        ? `${earnedPoints}/${quiz.target_total_points} điểm (${progressPercentage}%)`
                                        : `${answeredCount}/${totalCount} câu (${progressPercentage}%)`
                                    }
                                </span>
                            </div>
                            <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                                <div 
                                    className="h-full rounded-full transition-all duration-300 ease-out bg-blue-600"
                                    style={{ width: `${progressPercentage}%` }}
                                />
                            </div>
                        </div>

                        {/* CHÂN TRANG ĐIỀU KHIỂN CHẾ ĐỘ STUDY */}
                        <div className="mt-10 pt-6 border-t border-gray-200/60 flex justify-end gap-4">
                            <ConfirmButton
                                idleLabel="Làm lại từ đầu"
                                armedLabel="Bấm lần nữa để xóa hết & làm lại"
                                onConfirm={doResetQuiz}
                                className="px-6 py-3 bg-white hover:bg-gray-100 border border-gray-200 text-gray-600 font-bold rounded-xl text-sm transition-all shadow-sm"
                                armedClassName="px-6 py-3 bg-red-50 border border-red-200 text-red-600 font-bold rounded-xl text-sm transition-all shadow-sm"
                            />
                        </div>

                    </div>
                )}

            </div>
        </div>
    );
}