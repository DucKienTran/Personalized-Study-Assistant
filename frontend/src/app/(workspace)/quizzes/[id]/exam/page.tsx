"use client";

import { useEffect, useState, useRef, use } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import api from "@/services/api";
import QuizQuestionCard from "@/components/quizzes/QuizQuestionCard";
import ExamSidebar from "@/components/quizzes/ExamSidebar";
import { useToast, ToastContainer } from "@/components/shared/Toast";
import ConfirmButton from "@/components/shared/ConfirmButton";
import { AccessNotFound } from "@/components/shared/AccessNotFound";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

interface Option {
    id: string | number;
    option_text: string;
}

interface QuizQuestion {
    id: number;
    question_text: string;
    question_type: string;
    options: Option[] | null;
    statements?: Array<{ text: string; correct_answer?: boolean; explanation?: string }> | null;
    correct_answer: any;
    explanations: any;
    user_answer?: any;
    is_correct?: boolean | null;
    points?: number;
    hint?: string;
    awarded_points?: number | null;
    ai_feedback?: string | null;
}

interface QuizDetails {
    id: number;
    notebook_id: number;
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
    const [answers, setAnswers] = useState<Record<number, unknown>>({});
    const [submitting, setSubmitting] = useState(false);
    const [examResult, setExamResult] = useState<any>(null);
    const [accessNotFound, setAccessNotFound] = useState(false);

    // QUẢN LÝ RIÊNG CHO EXAM MODE (SINGLE-QUESTION VÀ MARKING)
    const [currentIndex, setCurrentIndex] = useState(0);
    const [markedReview, setMarkedReview] = useState<Record<number, boolean>>({});
    const [markedCritical, setMarkedCritical] = useState<Record<number, boolean>>({});
    const [showExamRules, setShowExamRules] = useState(false);

    // QUẢN LÝ BẢO MẬT & CHỐNG GIAN LẬN (PROCTORING SHIELD)
    const [violations, setViolations] = useState(0);
    const [isOnline, setIsOnline] = useState(true);
    const [offlineSeconds, setOfflineSeconds] = useState(0);
    const [timeLeft, setTimeLeft] = useState(1800); // Mặc định 30 phút

    // Sử dụng Refs để lưu dữ liệu tức thời tránh bug stale closure trong event listeners
    const answersRef = useRef(answers);
    const markedReviewRef = useRef(markedReview);
    const markedCriticalRef = useRef(markedCritical);
    const quizRef = useRef(quiz);
    const isSubmittedRef = useRef(false);
    const violationsRef = useRef(violations);
    const lastViolationAtRef = useRef(0);

    const { toasts, showToast, dismissToast } = useToast();


    useEffect(() => { answersRef.current = answers; }, [answers]);
    useEffect(() => { markedReviewRef.current = markedReview; }, [markedReview]);
    useEffect(() => { markedCriticalRef.current = markedCritical; }, [markedCritical]);
    useEffect(() => { quizRef.current = quiz; }, [quiz]);
    useEffect(() => { violationsRef.current = violations; }, [violations]);
    
    const isSubmitted = quiz?.mode === "study"
        ? (quiz.questions && Object.keys(answers).length >= quiz.questions.length)
        : examResult !== null;

    useEffect(() => { isSubmittedRef.current = isSubmitted; }, [isSubmitted]);

    // 1. Tải thông tin bài làm / phòng thi từ API
    useEffect(() => {
        async function loadQuizData() {
            if (!Number.isInteger(quizId) || quizId <= 0) {
                setAccessNotFound(true);
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                setAccessNotFound(false);
                let res = await api.get(`/quizzes/${quizId}`);
                let quizData = res.data.data;
                if (!quizData) {
                    setAccessNotFound(true);
                    return;
                }

                if (quizData?.mode === "exam") {
                    await api.post(`/quizzes/${quizId}/attempts/start`);
                    res = await api.get(`/quizzes/${quizId}`);
                    quizData = res.data.data;
                }
                setQuiz(quizData);

                if (quizData && quizData.questions) {
                    const initialAnswers: Record<number, unknown> = {};
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
                if (axios.isAxiosError(err) && (err.response?.status === 403 || err.response?.status === 404)) {
                    setAccessNotFound(true);
                } else {
                    alert("Không thể tải thông tin phòng học.");
                }
            } finally {
                setLoading(false);
            }
        }
        void loadQuizData();
    }, [quizId, router]);

    // 2. Bộ đếm ngược thời gian làm bài (Chỉ kích hoạt ở Exam Mode)
    useEffect(() => {
        if (!quiz || quiz.mode !== "exam" || isSubmitted) return;

        const interval = setInterval(() => {
            setTimeLeft((prev) => {
                if (prev <= 1) {
                    clearInterval(interval);
                    showToast("Thời gian làm bài đã hết, đang tự động thu bài...", "warning")
                    handleAutoSubmitExam("timeout");
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
            const now = Date.now();
            if (now - lastViolationAtRef.current < 750) return;
            lastViolationAtRef.current = now;

            const nextViolations = Math.min(violationsRef.current + 1, 3);
            violationsRef.current = nextViolations;
            setViolations(nextViolations);

            if (nextViolations >= 3) {
                showToast(
                    `Exam submitted after 3 violations.\nReason: ${reason}`,
                    "danger"
                );
                handleAutoSubmitExam("auto_submit");
            } else {
                showToast(
                    `Exam rule violation ${nextViolations}/3\n${reason}`,
                    "warning"
                );
            }
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
                    showToast("Đã ngắt mạng quá 15 giây liên tục! Đang thực hiện nộp bài khẩn cấp.", "danger");                    handleAutoSubmitExam("auto_submit");
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
    const handleAutoSubmitExam = async (reason: "timeout" | "auto_submit" | "abandoned") => {
        if (isSubmittedRef.current) return;
        const currentQuiz = quizRef.current;
        if (!currentQuiz) return;

        isSubmittedRef.current = true;
        setSubmitting(true);
        try {
            const answersPayload = currentQuiz.questions.map((q) => ({
                question_id: q.id,
                user_answer: answersRef.current[q.id] !== undefined ? answersRef.current[q.id] : null,
                mark_status: markedCriticalRef.current[q.id]
                    ? "critical"
                    : markedReviewRef.current[q.id]
                      ? "review"
                      : null,
            }));

            const res = await api.post(`/quizzes/${quizId}/submit`, {
                answers: answersPayload,
                submit_reason: reason,
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
                        statements: qDetail?.statements,
                        user_answer: qDetail?.user_answer,
                        is_correct: qDetail?.is_correct,
                        awarded_points: qDetail?.awarded_points,
                        ai_feedback: qDetail?.ai_feedback,
                    };
                });
                return {
                    ...prevQuiz,
                    questions: updatedQuestions,
                };
            });

            if (reason !== "auto_submit") {
                showToast(
                    `Exam submitted successfully.\nScore: ${result.score}/${result.score_scale}`,
                    "success"
                );
            }
            router.replace(`/notebooks/${currentQuiz.notebook_id}?tab=quizzes&quizId=${quizId}`);
        } catch (err) {
            isSubmittedRef.current = false;
            console.error("Lỗi khi tự động nộp bài:", err);
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-full items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-3">
                    <span className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
                        <Icon name="progress_activity" className="animate-spin text-2xl" />
                    </span>
                    <div className="text-sm font-medium text-muted-foreground">
                        Preparing your exam room...
                    </div>
                </div>
            </div>
        );
    }

    if (accessNotFound) return <AccessNotFound />;

    if (!quiz) return null;

    const answeredCount = Object.keys(answers).length;
    const totalCount = quiz.questions?.length || 0;

    const isStudyCompleted = quiz.mode === "study" && answeredCount >= totalCount;
    const isExamSubmitted = examResult !== null;

    const correctCount = quiz.questions.filter((q) => q.is_correct).length;
    const earnedPoints = quiz.questions.reduce((sum, q) => {
        return sum + (q.awarded_points ?? (q.is_correct ? q.points ?? 0 : 0));
    }, 0);

    const showCorrectAnswers = quiz.mode === "study" || isSubmitted;
    
    const progressPercentage = showCorrectAnswers
        ? Math.round((earnedPoints / quiz.target_total_points) * 100)
        : Math.round((answeredCount / totalCount) * 100);

    // Sự kiện xử lý bấm chọn đáp án
    const handleAnswerQuestion = async (questionId: number, optionId: unknown) => {
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
                                    statements: result.statements,
                                    is_correct: result.is_correct,
                                    awarded_points: result.awarded_points,
                                    ai_feedback: result.ai_feedback,
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
            violationsRef.current = 0;
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
        if (isSubmittedRef.current) return;

        const unanswered = quiz.questions.filter((q) => answers[q.id] === undefined).length;
        let confirmMsg = "Bạn có chắc muốn nộp bài thi ngay?";
        if (unanswered > 0) {
            confirmMsg = `Cảnh báo: Bạn còn ${unanswered} câu chưa chọn đáp án. Bạn vẫn muốn nộp bài chứ?`;
        }
       
        isSubmittedRef.current = true;
        try {
            setSubmitting(true);
            const answersPayload = quiz.questions.map((q) => ({
                question_id: q.id,
                user_answer: answers[q.id] !== undefined ? answers[q.id] : null,
                mark_status: markedCritical[q.id]
                    ? "critical"
                    : markedReview[q.id]
                      ? "review"
                      : null,
            }));

            const res = await api.post(`/quizzes/${quizId}/submit`, {
                answers: answersPayload,
                submit_reason: "manual",
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
                            statements: qDetail?.statements,
                            user_answer: qDetail?.user_answer,
                            is_correct: qDetail?.is_correct,
                            awarded_points: qDetail?.awarded_points,
                            ai_feedback: qDetail?.ai_feedback,
                        };
                    }),
                };
            });
            
            router.replace(`/notebooks/${quiz.notebook_id}?tab=quizzes&quizId=${quizId}`);
        } catch (err) {
            isSubmittedRef.current = false;
            console.error("Lỗi khi nộp bài:", err);
            showToast("Nộp bài thi thất bại. Vui lòng thử lại.", "danger");
        } finally {
            setSubmitting(false);
        }
        
    };

    const currentQuestion = quiz.questions[currentIndex];
    const unansweredCount = quiz.questions.filter((q) => answers[q.id] === undefined).length;
    const submitArmedLabel = unansweredCount > 0 
        ? `${unansweredCount} unanswered. Click again to submit`
        : "Click again to confirm submission";

    return (
        <div className="relative min-h-full w-full overflow-x-hidden bg-background pb-16">
            <ToastContainer toasts={toasts} onDismiss={dismissToast} />
            {/* Overlay phong tỏa khi mất mạng kéo dài */}
            {!isOnline && quiz.mode === "exam" && !isSubmitted && (
                <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-foreground/90 px-4 text-background backdrop-blur-md">
                    <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-destructive/20 text-destructive">
                        <Icon name="wifi_off" className="text-3xl" />
                    </span>
                    <h2 className="font-heading text-xl font-semibold">Connection interrupted</h2>
                    <p className="mt-2 max-w-md text-center text-sm leading-6 text-background/70">
                        Reconnecting now. The exam will be submitted automatically after <span className="font-semibold text-background">{offlineSeconds} / 15 seconds</span> offline.
                    </p>
                </div>
            )}

            <div className="relative z-10 mx-auto max-w-6xl px-4 pt-6 sm:px-6 sm:pt-8">
                
                {/* TIÊU ĐỀ PHÒNG THI / PHÒNG HỌC */}
                <header className="mb-6 flex flex-col justify-between gap-4 rounded-xl border border-border/80 bg-card p-5 shadow-xs sm:p-6 md:flex-row md:items-center">
                    <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-accent/10 px-2.5 py-1 text-[11px] font-medium text-accent">
                                <Icon name="assignment" className="text-sm" />
                                Exam mode
                            </span>
                            {!isSubmitted && (
                                <button
                                    type="button"
                                    onClick={() => setShowExamRules(true)}
                                    className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/5 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                                >
                                    <Icon name="shield_lock" className="text-sm text-primary" />
                                    Focused session
                                </button>
                            )}
                        </div>
                        <h1 className="mt-3 break-words pb-0.5 font-heading text-xl font-semibold leading-[1.35] text-foreground sm:text-2xl">
                            {quiz.title}
                        </h1>
                    </div>
                    
                    {isSubmitted ? (
                        <button
                            onClick={() => router.push(`/notebooks/${quiz.notebook_id}?tab=quizzes`)}
                            className="inline-flex h-9 items-center justify-center rounded-md border border-border bg-background px-3 text-sm font-medium text-muted-foreground transition-colors hover:border-destructive/30 hover:bg-destructive/10 hover:text-destructive active:bg-destructive/20"
                        >
                            Leave exam
                        </button>
                    ) : (
                        <ConfirmButton
                            idleLabel="Leave exam"
                            armedLabel="Click again to submit & leave"
                            onConfirm={() => handleAutoSubmitExam("abandoned")}
                            className="inline-flex h-9 items-center justify-center rounded-md border border-border bg-background px-3 text-sm font-medium text-muted-foreground transition-colors hover:border-destructive/30 hover:bg-destructive/10 hover:text-destructive active:bg-destructive/20"
                            armedClassName="inline-flex h-9 items-center justify-center rounded-md border border-destructive/30 bg-destructive/10 px-3 text-sm font-medium text-destructive transition-colors hover:bg-destructive/20"
                        />
                    )}
                </header>

                {/* HIỂN THỊ KẾT QUẢ SAU KHI HOÀN THÀNH (STUDY MODE) */}
                {quiz.mode === "study" && isStudyCompleted && (
                    <div className="mb-6 rounded-xl border border-primary/20 bg-primary/10 p-6 text-foreground shadow-xs">
                        <h2 className="font-heading text-lg font-semibold">Study session completed</h2>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                            <div className="rounded-[10px] border border-border/70 bg-card p-3 text-center">
                                <p className="text-xs text-muted-foreground">Score</p>
                                <p className="text-2xl font-black">{earnedPoints}/{quiz.target_total_points}</p>
                            </div>
                            <div className="rounded-[10px] border border-border/70 bg-card p-3 text-center">
                                <p className="text-xs text-muted-foreground">Accuracy</p>
                                <p className="text-2xl font-black">{progressPercentage}%</p>
                            </div>
                            <div className="rounded-[10px] border border-border/70 bg-card p-3 text-center">
                                <p className="text-xs text-muted-foreground">Correct</p>
                                <p className="text-2xl font-black">{correctCount}/{totalCount}</p>
                            </div>
                            <div className="flex items-center justify-center rounded-[10px] border border-border/70 bg-card p-3 text-center">
                                <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">Completed</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* HIỂN THỊ KẾT QUẢ KHI NỘP THÀNH CÔNG (EXAM MODE) */}
                {quiz.mode === "exam" && isSubmitted && examResult && (
                    <div className="mb-6 rounded-xl border border-primary/20 bg-primary/10 p-6 text-foreground shadow-xs">
                        <h2 className="font-heading text-lg font-semibold">Exam submitted</h2>
                        <p className="mb-4 mt-1 text-xs text-muted-foreground">Your result has been saved successfully.</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="rounded-[10px] border border-border/70 bg-card p-3 text-center">
                                <p className="text-xs text-muted-foreground">Score</p>
                                <p className="text-2xl font-black">{examResult.score} / {examResult.score_scale}</p>
                            </div>
                            <div className="rounded-[10px] border border-border/70 bg-card p-3 text-center">
                                <p className="text-xs text-muted-foreground">Accuracy</p>
                                <p className="text-2xl font-black">
                                    {examResult.total_questions > 0 ? Math.round((examResult.correct_answers_count / examResult.total_questions) * 100) : 0}%
                                </p>
                            </div>
                            <div className="rounded-[10px] border border-border/70 bg-card p-3 text-center">
                                <p className="text-xs text-muted-foreground">Correct</p>
                                <p className="text-2xl font-black">{examResult.correct_answers_count} / {examResult.total_questions}</p>
                            </div>
                            <div className="flex items-center justify-center rounded-[10px] border border-border/70 bg-card p-3 text-center">
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                                    <Icon name="check_circle" className="text-sm" /> Submitted
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* GIAO DIỆN CHIA MÀN HÌNH TÙY THEO CHẾ ĐỘ CHỌN */}
                {quiz.mode === "exam" ? (
                    
                    /* ============================================== */
                    /* GIAO DIỆN PHÒNG THI CHUYÊN NGHIỆP (EXAM MODE)  */
                    /* ============================================== */
                    <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
                        
                        {/* CỘT LÀM BÀI: MỖI CÂU HIỂN THỊ 1 TRANG */}
                        <div className="order-last min-w-0 space-y-4 lg:order-none">
                            {currentQuestion && (
                                <>
                                    <QuizQuestionCard
                                        index={currentIndex}
                                        questionId={currentQuestion.id}
                                        questionText={currentQuestion.question_text}
                                        questionType={currentQuestion.question_type}
                                        options={currentQuestion.options}
                                        statements={currentQuestion.statements}
                                        correctAnswer={currentQuestion.correct_answer}
                                        explanations={currentQuestion.explanations}
                                        selectedOptionId={answers[currentQuestion.id]}
                                        onSelectOption={(optId) => handleAnswerQuestion(currentQuestion.id, optId)}
                                        onChangeAnswer={
                                            ["fill_blank", "short_answer", "essay"].includes(currentQuestion.question_type)
                                                ? (answer) => setAnswers((current) => ({ ...current, [currentQuestion.id]: answer }))
                                                : undefined
                                        }
                                        mode="exam"
                                        points={currentQuestion.points}
                                        awardedPoints={currentQuestion.awarded_points}
                                        isCorrect={currentQuestion.is_correct}
                                        aiFeedback={currentQuestion.ai_feedback}
                                        allowAnswerChanges
                                        readOnly={isSubmitted}
                                    />

                                    {/* PHÍM ĐIỀU HƯỚNG DƯỚI CÂU HỎI */}
                                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/80 bg-card p-4 shadow-xs">
                                        <div className="flex gap-2">
                                            <Button
                                                variant="outline"
                                                disabled={currentIndex === 0}
                                                onClick={() => setCurrentIndex((p) => p - 1)}
                                                className="text-xs"
                                            >
                                                <Icon name="arrow_back" className="text-base" />
                                                Previous
                                            </Button>
                                            
                                            {currentIndex < quiz.questions.length - 1 ? (
                                                <Button
                                                    onClick={() => setCurrentIndex((p) => p + 1)}
                                                >
                                                    Next
                                                    <Icon name="arrow_forward" className="text-base" />
                                                </Button>
                                            ) : (
                                                !isSubmitted && (
                                                    <ConfirmButton
                                                        idleLabel="Submit exam"
                                                        armedLabel={submitArmedLabel}
                                                        onConfirm={doSubmitExam}
                                                        className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-[var(--primary-hover)]"
                                                        armedClassName="inline-flex h-9 items-center justify-center rounded-md bg-accent px-3 text-sm font-medium text-accent-foreground transition-colors"
                                                    />
                                                )
                                            )}
                                        </div>

                                        {/* Cờ đánh dấu câu hỏi đặc biệt */}
                                        {!isSubmitted && (
                                            <div className="flex gap-2">
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => {
                                                        const nextValue = !markedReview[currentQuestion.id];
                                                        setMarkedReview((current) => ({
                                                            ...current,
                                                            [currentQuestion.id]: nextValue,
                                                        }));
                                                        if (nextValue) {
                                                            setMarkedCritical((current) => ({
                                                                ...current,
                                                                [currentQuestion.id]: false,
                                                            }));
                                                        }
                                                    }}
                                                    className={`text-xs ${
                                                        markedReview[currentQuestion.id]
                                                            ? "border-chart-1/30 bg-chart-1/10 text-chart-1 hover:bg-chart-1/15"
                                                            : ""
                                                    }`}
                                                >
                                                    <Icon name="flag" className="text-base" />
                                                    <span>{markedReview[currentQuestion.id] ? "Unmark review" : "Mark for review"}</span>
                                                </Button>
                                                <Button
                                                    variant={markedCritical[currentQuestion.id] ? "destructive" : "outline"}
                                                    size="sm"
                                                    onClick={() => {
                                                        const nextValue = !markedCritical[currentQuestion.id];
                                                        setMarkedCritical((current) => ({
                                                            ...current,
                                                            [currentQuestion.id]: nextValue,
                                                        }));
                                                        if (nextValue) {
                                                            setMarkedReview((current) => ({
                                                                ...current,
                                                                [currentQuestion.id]: false,
                                                            }));
                                                        }
                                                    }}
                                                    className="text-xs"
                                                >
                                                    <Icon name="priority_high" className="text-base" />
                                                    <span>{markedCritical[currentQuestion.id] ? "Unmark critical" : "Mark critical"}</span>
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>

                        {/* CỘT PHẢI: COMPONENT ĐIỀU HƯỚNG TÁCH BIỆT */}
                        <div className="order-first lg:order-none lg:sticky lg:top-6">
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
                                    questionType={q.question_type}
                                    options={q.options}
                                    statements={q.statements}
                                    correctAnswer={q.correct_answer}
                                    explanations={q.explanations}
                                    selectedOptionId={answers[q.id] !== undefined ? answers[q.id] : q.user_answer}
                                    onSelectOption={(optionId) => handleAnswerQuestion(q.id, optionId)}
                                    onChangeAnswer={
                                        quiz.mode === "study" && ["multiple_response", "true_false"].includes(q.question_type)
                                            ? (answer) => setAnswers((current) => ({ ...current, [q.id]: answer }))
                                            : undefined
                                    }
                                    mode={quiz.mode}
                                    awardedPoints={q.awarded_points}
                                    isCorrect={q.is_correct}
                                    aiFeedback={q.ai_feedback}
                                    allowAnswerChanges={["multiple_response", "true_false"].includes(q.question_type)}
                                />
                            ))}
                        </div>

                        {/* THANH TIẾN ĐỘ CHẾ ĐỘ HỌC */}
                        <div className="mt-8 space-y-2.5 rounded-xl border border-border/80 bg-card p-5 shadow-xs">
                            <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
                                <span>{showCorrectAnswers ? "Current result" : "Answer progress"}</span>
                                <span className="font-medium text-primary">
                                    {showCorrectAnswers
                                        ? `${earnedPoints}/${quiz.target_total_points} points (${progressPercentage}%)`
                                        : `${answeredCount}/${totalCount} questions (${progressPercentage}%)`
                                    }
                                </span>
                            </div>
                            <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                                <div 
                                    className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
                                    style={{ width: `${progressPercentage}%` }}
                                />
                            </div>
                        </div>

                        {/* CHÂN TRANG ĐIỀU KHIỂN CHẾ ĐỘ STUDY */}
                        <div className="mt-10 flex justify-end gap-4 border-t border-border/70 pt-6">
                            <ConfirmButton
                                idleLabel="Start over"
                                armedLabel="Click again to reset progress"
                                onConfirm={doResetQuiz}
                                className="inline-flex h-9 items-center justify-center rounded-md border border-border bg-background px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                                armedClassName="inline-flex h-9 items-center justify-center rounded-md border border-destructive/30 bg-destructive/10 px-3 text-sm font-medium text-destructive transition-colors hover:bg-destructive/20"
                            />
                        </div>

                    </div>
                )}

            </div>

            <Dialog open={showExamRules} onOpenChange={setShowExamRules}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-lg">
                            <Icon name="shield_lock" className="text-xl text-primary" />
                            Exam rules
                        </DialogTitle>
                        <DialogDescription className="leading-5">
                            Stay focused in this exam window until you submit.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3 text-sm text-foreground">
                        <p className="flex items-start gap-2.5">
                            <Icon name="tab_inactive" className="mt-0.5 text-base text-accent" />
                            Do not switch tabs, leave the exam, or use split-screen mode.
                        </p>
                        <p className="flex items-start gap-2.5">
                            <Icon name="warning" className="mt-0.5 text-base text-destructive" />
                            The exam is submitted automatically after three violations.
                        </p>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
