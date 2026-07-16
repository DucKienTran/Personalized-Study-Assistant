"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import api from "@/services/api";
import QuizQuestionCard from "@/components/quizzes/QuizQuestionCard";

interface Option {
    id: String;
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
    is_correct?: boolean | null; // Đã sửa đổi cho phép nhận null để tránh lỗi gán kiểu dữ liệu
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
    const [answers, setAnswers] = useState<Record<number, number>>({});
    const [submitting, setSubmitting] = useState(false);
    const [examResult, setExamResult] = useState<any>(null);

    useEffect(() => {
        async function loadQuizData() {
            try {
                setLoading(true);
                const res = await api.get(`/quizzes/${quizId}`);
                let quizData = res.data.data;

                // Exam đã hoàn thành: get_quiz_for_rendering KHÔNG overlay user_answer/is_correct
                // (chỉ overlay cho study) -> phải lấy toàn bộ câu hỏi + đáp án từ QuizAttempt mới nhất.
                if (quizData?.mode === "exam") {
                    try {
                        const attemptsRes = await api.get(`/quizzes/${quizId}/attempts`);
                        const attempts: any[] = attemptsRes.data.data || [];
                        const latestCompleted = attempts
                            .filter((a) => a.attempt_status === "completed")
                            .sort((a, b) => b.id - a.id)[0];

                        if (latestCompleted) {
                            const detailRes = await api.get(`/quiz-attempts/${latestCompleted.id}`);
                            const detail = detailRes.data.data;

                            // Nguồn dữ liệu câu hỏi giờ là attempt detail, KHÔNG dùng questions từ
                            // /quizzes/{id} nữa (tránh trộn 2 nguồn không đồng bộ). Chuẩn hoá field
                            // question_id -> id cho khớp interface QuizQuestion đang dùng trong file này.
                            quizData = {
                                ...quizData,
                                questions: detail.questions.map((d: any) => ({
                                    id: d.question_id,
                                    question_text: d.question_text,
                                    question_type: d.question_type,
                                    options: d.options, // cần backend đã vá get_attempt_detail trả kèm field này
                                    correct_answer: d.correct_answer,
                                    explanations: d.explanations,
                                    points: d.points,
                                    user_answer: d.user_answer,
                                    is_correct: d.is_correct,
                                })),
                            };

                            setExamResult({ score: detail.score, attempt_id: detail.id });
                        }
                    } catch (attemptErr) {
                        console.error("Không tải được kết quả lần làm bài thi:", attemptErr);
                    }
                }

                setQuiz(quizData);

                if (quizData && quizData.questions) {
                    const initialAnswers: Record<number, number> = {};

                    quizData.questions.forEach((q: any) => {
                        if (q.user_answer !== null && q.user_answer !== undefined) {
                            initialAnswers[q.id] = q.user_answer;
                        }
                    });

                    setAnswers(initialAnswers);
                }
            } catch (err) {
                console.error("Lỗi khi tải chi tiết bài làm:", err);
                alert("Không thể tải thông tin bài học.");
                router.push("/quizzes");
            } finally {
                setLoading(false);
            }
        }
        if (quizId) loadQuizData();
    }, [quizId, router]);

    if (loading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-[#eef6ff]">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    <div className="text-sm font-semibold text-blue-600 animate-pulse">
                        Đang chuẩn bị phòng học tập...
                    </div>
                </div>
            </div>
        );
    }

    if (!quiz) return null;

    const answeredCount = Object.keys(answers).length;
    const totalCount = quiz.questions?.length || 0;

    const isStudyCompleted =
        quiz.mode === "study" &&
        answeredCount >= totalCount;

    const isExamSubmitted =
        examResult !== null;

    const isSubmitted =
        quiz.mode === "study"
            ? isStudyCompleted
            : isExamSubmitted;

    const correctCount = quiz.questions.filter(
        (q) => q.is_correct
    ).length;

    const earnedPoints = quiz.questions.reduce((sum, q) => {
        if (q.is_correct) {
            return sum + (q.points ?? 0);
        }
        return sum;
    }, 0);

    const showCorrectAnswers = quiz.mode === "study" || isSubmitted;
    const progressValue = showCorrectAnswers
        ? earnedPoints
        : answeredCount;
    const progressPercentage = showCorrectAnswers
        ? Math.round(
            (earnedPoints / quiz.target_total_points) * 100
        )
        : Math.round(
            (answeredCount / totalCount) * 100
        );    
    const handleAnswerQuestion = async (
        questionId: number,
        optionId: number
    ) => {
        const nextAnswers = {
            ...answers,
            [questionId]: optionId,
        };

        setAnswers(nextAnswers);

        const nextAnsweredCount =
            answers[questionId] !== undefined
                ? answeredCount
                : answeredCount + 1;

        if (quiz.mode === "study") {
            try {
                const res = await api.post(
                    `/quizzes/${quizId}/questions/${questionId}/answer`,
                    {
                        user_answer: optionId,
                    }
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

                if (nextAnsweredCount === totalCount) {
                    window.scrollTo({
                        top: 0,
                        behavior: "smooth",
                    });
                }
            } catch (err) {
                console.error(err);

                setAnswers((prev) => {
                    const rollback = { ...prev };
                    delete rollback[questionId];
                    return rollback;
                });

                alert("Không thể lưu đáp án.");
            }

            return;
        }

        // Exam mode chưa submit
    };

    const handleResetQuiz = async () => {
        if (!confirm("Bạn có chắc chắn muốn làm lại từ đầu không?")) {
            return;
        }

        try {
            // Exam: không xóa lịch sử, chỉ sang trang thi mới
            if (quiz.mode === "exam") {
                router.push(`/quizzes/${quizId}/exam`);
                return;
            }

            // Study: xóa progress rồi reset tại chỗ
            await api.delete(`/quizzes/${quizId}/progress`);

            setAnswers({});
            setExamResult(null);

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

            window.scrollTo({
                top: 0,
                behavior: "smooth",
            });
        } catch (err) {
            console.error("Lỗi khi làm mới tiến trình:", err);
            alert("Không thể làm sạch dữ liệu cũ.");
        }
    };



    const handleSubmitExam = async () => {
        const unanswered = quiz.questions.filter((q) => answers[q.id] === undefined).length;
        let confirmMsg = "Bạn có chắc chắn muốn nộp bài thi không?";
        if (unanswered > 0) {
            confirmMsg = `Bạn vẫn còn ${unanswered} câu chưa trả lời. Bạn có chắc chắn muốn nộp bài thi không?`;
        }

        if (confirm(confirmMsg)) {
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
                alert(`Nộp bài thành công! Điểm số của bạn: ${result.score}/${result.score_scale}`);

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
                window.scrollTo({ top: 0, behavior: "smooth" });
            } catch (err) {
                console.error("Lỗi khi nộp bài kiểm tra:", err);
                alert("Không thể nộp bài thi. Vui lòng thử lại.");
            } finally {
                setSubmitting(false);
            }
        }
    };

    return (
        <div className="min-h-screen w-full relative bg-[#eef6ff] pb-20 overflow-x-hidden">
            <div className="relative max-w-4xl mx-auto px-4 pt-8 flex flex-col z-10">
                
                {/* KHỐI HEADER TRANG LÀM BÀI */}
                <div className="bg-white/90 backdrop-blur-md border border-blue-100 rounded-2xl p-6 shadow-sm mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <span className={`inline-block text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-md mb-2.5 shadow-sm ${
                            quiz.mode === "exam" 
                                ? "bg-purple-100 text-purple-800 border border-purple-200" 
                                : "bg-blue-100 text-blue-800 border border-blue-200"
                        }`}>
                            {quiz.mode === "exam" ? "Chế độ thi cử (Exam Mode)" : "Chế độ ôn tập (Study Mode)"}
                        </span>
                        <h1 className="text-xl font-bold text-gray-900 leading-snug">{quiz.title}</h1>
                    </div>
                    
                    <button
                        type="button"
                        onClick={() => { 
                            if(confirm("Bạn muốn quay lại danh sách? Tiến trình chưa lưu hoàn chỉnh có thể bị mất.")) {
                                router.push("/quizzes"); 
                            }
                        }}
                        className="px-4 py-2 bg-white hover:bg-red-50 border border-red-200 hover:border-red-300 text-red-600 hover:text-red-700 text-sm font-medium rounded-xl transition-all duration-150 transform active:scale-95 whitespace-nowrap shadow-sm"
                    >
                        Rời khỏi
                    </button>
                </div>

                {/* KHỐI KẾT QUẢ THI CỬ */}
                {quiz.mode === "study" && isStudyCompleted && (
                    <div className="bg-gradient-to-r from-emerald-500 to-teal-600 border border-emerald-400 rounded-2xl p-6 shadow-md text-white mb-6">
                        <h2 className="text-lg font-bold mb-2">
                            Bạn đã hoàn thành bài ôn tập
                        </h2>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">

                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs">Điểm đạt được</p>
                                <p className="text-2xl font-black">
                                    {earnedPoints}/{quiz.target_total_points}
                                </p>
                            </div>

                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs">Tỷ lệ điểm</p>
                                <p className="text-2xl font-black">
                                    {progressPercentage}%
                                </p>
                            </div>

                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs">Số câu đúng</p>
                                <p className="text-2xl font-black">
                                    {correctCount}/{totalCount}
                                </p>
                            </div>

                            <div className="bg-white/10 rounded-xl p-3 text-center">
                                <p className="text-xs">Trạng thái</p>
                                <p className="text-sm font-bold mt-1">
                                    COMPLETED
                                </p>
                            </div>

                        </div>
                    </div>
                )}

                {/* DANH SÁCH CÂU HỎI */}
                <div className="space-y-6 flex-1">
                    {quiz.questions.map((q: any, idx: number) => (
                        <QuizQuestionCard
                            key={q.id}
                            index={idx}
                            questionId={q.id}
                            questionText={q.question_text}
                            options={q.options}
                            correctAnswer={q.correct_answer}
                            explanations={q.explanations}
                            selectedOptionId={answers[q.id] !== undefined ? answers[q.id] : q.user_answer} 
                            onSelectOption={(optionId) => handleAnswerQuestion(q.id, optionId)}
                            mode={quiz.mode}
                            points={q.points}
                            hint={q.hint}
                        />
                    ))}
                </div>

                {/* THANH TIẾN ĐỘ */}
                <div className="bg-white/90 backdrop-blur-md border border-blue-100 rounded-2xl p-5 shadow-sm mt-8 space-y-2.5">
                    <div className="flex items-center justify-between text-xs font-bold text-gray-500 uppercase tracking-wider">
                        <span>{showCorrectAnswers ? "Kết quả chính xác đạt được" : "Tiến độ làm bài"}</span>
                        <span className={quiz.mode === "exam" && !isSubmitted ? "text-purple-600 font-extrabold" : "text-blue-600 font-extrabold"}>
                            {showCorrectAnswers
                                ? `${earnedPoints}/${quiz.target_total_points} điểm (${progressPercentage}%)`
                                : `${answeredCount}/${totalCount} câu (${progressPercentage}%)`
                            }
                        </span>
                    </div>
                    <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                        <div 
                            className={`h-full rounded-full transition-all duration-300 ease-out ${
                                quiz.mode === "exam" && !isSubmitted ? "bg-purple-600" : "bg-blue-600"
                            }`}
                            style={{ width: `${progressPercentage}%` }}
                        />
                    </div>
                    {showCorrectAnswers && (
                        <p className="text-[11px] text-gray-500 italic mt-1">
                            * Hệ thống chỉ tính những câu trả lời có kết quả ĐÚNG. Những câu làm sai hoặc chưa làm không được tính vào thanh kết quả này.
                        </p>
                    )}
                </div>

                {/* CHÂN TRANG */}
                <div className="mt-10 pt-6 border-t border-gray-200/60 flex justify-end gap-4">
                    {(quiz.mode === "study" || (quiz.mode === "exam" && isSubmitted)) && (
                        <button
                            type="button"
                            onClick={handleResetQuiz}
                            className="px-6 py-3 bg-white hover:bg-gray-100 border border-gray-200 text-gray-600 font-bold rounded-xl text-sm transition-all duration-150 transform active:scale-95 shadow-sm hover:shadow"
                        >
                            Làm lại từ đầu
                        </button>
                    )}

                    {quiz.mode === "exam" && !isSubmitted && (
                        <button
                            type="button"
                            onClick={handleSubmitExam}
                            disabled={submitting}
                            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-bold rounded-xl text-sm transition-all duration-150 transform active:scale-95 shadow-md disabled:opacity-50"
                        >
                            {submitting ? "Đang chấm bài..." : "Nộp bài thi"}
                        </button>
                    )}
                </div>

            </div>
        </div>
    );
}