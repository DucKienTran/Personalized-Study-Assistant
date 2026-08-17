"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import QuizQuestionCard from "@/components/quizzes/QuizQuestionCard";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import api from "@/services/api";
import { FeedbackTag, quizService } from "@/services/quiz.service";

interface Option {
  id: string | number;
  option_text: string;
  text?: string;
}

interface QuizQuestion {
  id: number;
  question_text: string;
  question_type: string;
  options: Option[] | null;
  statements?: Array<{ text: string; correct_answer?: boolean; explanation?: string }> | null;
  correct_answer: unknown;
  explanations: unknown;
  user_answer?: unknown;
  is_correct?: boolean | null;
  points?: number;
  hint?: string;
  mark_status?: "review" | "critical" | null;
  awarded_points?: number | null;
  ai_feedback?: string | null;
}

interface QuizDetails {
  id: number;
  title: string;
  mode: "study" | "exam";
  total_questions: number;
  target_total_points: number;
  source_document_ids: number[];
  source_documents?: Array<{ id: number; title: string }>;
  questions: QuizQuestion[];
}

interface QuizRunnerProps {
  quizId: number;
  onBack: () => void;
  onExplainQuestion?: (content: string, sourceDocumentIds: number[]) => void | Promise<void>;
}

type AnswerValue = unknown;
type Notice = { message: string; tone: "success" | "danger" };
type ReviewFilter = "all" | "review" | "critical";

const FEEDBACK_TAGS: Array<{ value: FeedbackTag; label: string }> = [
  { value: "too_hard", label: "Too difficult" },
  { value: "too_easy", label: "Too easy" },
  { value: "repetitive", label: "Repetitive questions" },
  { value: "not_relevant", label: "Not relevant" },
  { value: "too_shallow", label: "Too shallow" },
  { value: "too_long", label: "Too time-consuming" },
  { value: "too_short", label: "Too brief" },
  { value: "not_enough_source_coverage", label: "Missing source coverage" },
  { value: "hallucinated", label: "Content outside the sources" },
];

function formatScore(value: number): string {
  if (!Number.isFinite(value)) return "0";
  const rounded = Math.round((value + Number.EPSILON) * 100) / 100;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2);
}

function hasCompleteAnswer(question: QuizQuestion, answer: unknown): boolean {
  if (question.question_type === "true_false") {
    return Array.isArray(answer) && Boolean(question.statements?.length) &&
      question.statements!.every((_, index) => typeof answer[index] === "boolean");
  }
  if (question.question_type === "multiple_response") {
    return Array.isArray(answer) && answer.length > 0;
  }
  if (["fill_blank", "short_answer", "essay"].includes(question.question_type)) {
    return typeof answer === "string" && answer.trim().length > 0;
  }
  return answer !== undefined && answer !== null;
}

function isVietnamese(value: string): boolean {
  return /[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i.test(value) ||
    /\b(câu|đáp án|không|đúng|sai|hãy|tại sao|như thế nào)\b/i.test(value);
}

function answerText(question: QuizQuestion, value: unknown): string {
  if (question.question_type === "true_false" && Array.isArray(value)) {
    return value
      .map((answer, index) => {
        if (typeof answer !== "boolean") return null;
        const statement = question.statements?.[index]?.text ?? `Statement ${index + 1}`;
        return `${statement}: ${answer ? "Đúng" : "Sai"}`;
      })
      .filter(Boolean)
      .join("; ");
  }

  const values = Array.isArray(value) ? value : [value];
  return values
    .filter((answer) => answer !== undefined && answer !== null)
    .map((answer) => {
      const normalized = String(answer).trim().toLowerCase();
      const option = question.options?.find((item) => {
        const optionId = String(item.id).trim().toLowerCase();
        const optionText = item.option_text.trim().toLowerCase();
        return optionId === normalized || optionText === normalized || optionText.startsWith(`${normalized}.`) || optionText.startsWith(`${normalized}:`);
      });
      return option?.text ?? option?.option_text.replace(/^\s*[A-Z]\s*[.\-:]\s*/i, "") ?? String(answer);
    })
    .join(", ");
}

function buildExplainPrompt(question: QuizQuestion): string {
  const selectedAnswer = answerText(question, question.user_answer);
  const correctAnswer = answerText(question, question.correct_answer);
  const correct = question.is_correct === true;

  if (isVietnamese(question.question_text)) {
    return `Tôi đang làm một bài kiểm tra về tài liệu này và nhận được câu hỏi: "${question.question_text}"

Tôi đã chọn câu trả lời: "${selectedAnswer || "Chưa chọn câu trả lời"}".

${correct
  ? `Câu trả lời đó đúng. Câu trả lời đúng là "${correctAnswer}".`
  : `Câu trả lời đó không đúng. Câu trả lời đúng là "${correctAnswer}".`}

Hãy giúp tôi hiểu ${correct ? "vì sao câu trả lời này đúng" : "vì sao câu trả lời của tôi không đúng"}, dựa trên các tài liệu nguồn của notebook.`;
  }

  return `I am taking a quiz about this material and received the question: "${question.question_text}"

I selected: "${selectedAnswer || "No answer selected"}".

${correct
  ? `That answer is correct. The correct answer is "${correctAnswer}".`
  : `That answer is incorrect. The correct answer is "${correctAnswer}".`}

Please help me understand ${correct ? "why this answer is correct" : "why my answer is incorrect"}, using the notebook source materials.`;
}

export default function QuizRunner({
  quizId,
  onBack,
  onExplainQuestion,
}: QuizRunnerProps) {
  const router = useRouter();

  const [quiz, setQuiz] = useState<QuizDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [answers, setAnswers] = useState<Record<number, AnswerValue>>({});
  const [savingQuestionId, setSavingQuestionId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [examResult, setExamResult] = useState<any>(null);
  const [showResetDialog, setShowResetDialog] = useState(false);
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [feedbackTags, setFeedbackTags] = useState<FeedbackTag[]>([]);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [reviewFilter, setReviewFilter] = useState<ReviewFilter>("all");

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 3000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    async function loadQuizData() {
      if (!Number.isFinite(quizId) || quizId <= 0) {
        setPageError("This quiz link is invalid.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setPageError(null);
        const response = await api.get(`/quizzes/${quizId}`);
        let quizData = response.data.data;

        if (quizData?.mode === "study") {
          await api.post(`/quizzes/${quizId}/attempts/start`);
          const orderedResponse = await api.get(`/quizzes/${quizId}`);
          quizData = orderedResponse.data.data;
        }

        if (quizData?.mode === "exam") {
          try {
            const attemptsResponse = await api.get(`/quizzes/${quizId}/attempts`);
            const attempts: any[] = attemptsResponse.data.data || [];
            const latestCompleted = attempts
              .filter((attempt) => attempt.attempt_status === "completed")
              .sort((left, right) => {
                const rightTime = Date.parse(right.submitted_at ?? right.created_at);
                const leftTime = Date.parse(left.submitted_at ?? left.created_at);
                return rightTime - leftTime;
              })[0];

            if (latestCompleted) {
              const detailResponse = await api.get(
                `/quiz-attempts/${latestCompleted.id}`
              );
              const detail = detailResponse.data.data;

              quizData = {
                ...quizData,
                questions: detail.questions.map((question: any) => ({
                  id: question.question_id,
                  question_text: question.question_text,
                  question_type: question.question_type,
                  options: question.options,
                  correct_answer: question.correct_answer,
                  explanations: question.explanations,
                  statements: question.statements,
                  points: question.points,
                  user_answer: question.user_answer,
                  is_correct: question.is_correct,
                  mark_status: question.mark_status,
                  awarded_points: question.awarded_points,
                  ai_feedback: question.ai_feedback,
                })),
              };

              setExamResult({ score: detail.score, attempt_id: detail.id });
            }
          } catch (attemptError) {
            console.error("Failed to load the latest exam attempt:", attemptError);
          }
        }

        setQuiz(quizData);

        const initialAnswers: Record<number, AnswerValue> = {};
        quizData?.questions?.forEach((question: QuizQuestion) => {
          if (question.user_answer !== null && question.user_answer !== undefined) {
            initialAnswers[question.id] = question.user_answer;
          }
        });
        setAnswers(initialAnswers);
      } catch (error) {
        console.error("Failed to load quiz:", error);
        setPageError("We could not load this quiz. Please try again.");
      } finally {
        setLoading(false);
      }
    }

    loadQuizData();
  }, [quizId, reloadKey]);

  if (loading) {
    return (
      <div className="h-full overflow-y-auto bg-background px-4 py-6 sm:px-8">
        <div className="mx-auto max-w-4xl space-y-5">
          <Skeleton className="h-9 w-40" />
          <div className="rounded-xl border border-border bg-card p-6">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="mt-4 h-8 w-2/3" />
            <Skeleton className="mt-5 h-2 w-full" />
          </div>
          {[0, 1].map((item) => (
            <div key={item} className="rounded-xl border border-border bg-card p-6">
              <Skeleton className="h-5 w-20" />
              <Skeleton className="mt-4 h-6 w-4/5" />
              <div className="mt-5 space-y-3">
                {[0, 1, 2, 3].map((option) => (
                  <Skeleton key={option} className="h-12 w-full" />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (pageError || !quiz) {
    return (
      <div className="flex h-full items-center justify-center bg-background p-6">
        <div className="w-full max-w-md rounded-xl border border-border bg-card p-8 text-center shadow-xs">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <Icon name="error_outline" className="text-2xl" />
          </span>
          <h1 className="mt-4 font-heading text-lg font-semibold">Quiz unavailable</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{pageError}</p>
          <div className="mt-6 flex justify-center gap-2">
            <Button variant="outline" onClick={onBack}>
              <Icon name="arrow_back" className="text-base" />
              Go back
            </Button>
            <Button onClick={() => setReloadKey((current) => current + 1)}>Try again</Button>
          </div>
        </div>
      </div>
    );
  }

  const answeredCount = quiz.questions.filter((question) =>
    quiz.mode === "study"
      ? question.awarded_points !== undefined && question.awarded_points !== null
      : hasCompleteAnswer(question, answers[question.id] ?? question.user_answer)
  ).length;
  const totalCount = quiz.questions?.length || 0;
  const isStudyCompleted =
    quiz.mode === "study" && totalCount > 0 && answeredCount >= totalCount;
  const isExamSubmitted = examResult !== null;
  const isSubmitted = quiz.mode === "study" ? isStudyCompleted : isExamSubmitted;
  const correctCount = quiz.questions.filter((question) => question.is_correct).length;
  const earnedPoints = quiz.questions.reduce(
    (sum, question) => sum + (question.awarded_points ?? (question.is_correct ? question.points ?? 0 : 0)),
    0
  );
  const showCorrectAnswers = quiz.mode === "study" || isSubmitted;
  const progressPercentage = Math.max(
    0,
    Math.min(
      100,
      showCorrectAnswers
        ? Math.round((earnedPoints / Math.max(quiz.target_total_points, 1)) * 100)
        : Math.round((answeredCount / Math.max(totalCount, 1)) * 100)
    )
  );
  const completionPercentage = Math.max(
    0,
    Math.min(100, Math.round((answeredCount / Math.max(totalCount, 1)) * 100))
  );

  const handleAnswerQuestion = async (
    questionId: number,
    optionId: AnswerValue
  ) => {
    const nextAnswers = { ...answers, [questionId]: optionId };
    setAnswers(nextAnswers);

    const nextAnsweredCount =
      hasCompleteAnswer(
        quiz.questions.find((question) => question.id === questionId)!,
        answers[questionId]
      )
        ? answeredCount
        : answeredCount + 1;

    if (quiz.mode !== "study") return;

    try {
      setSavingQuestionId(questionId);
      const response = await api.post(
        `/quizzes/${quizId}/questions/${questionId}/answer`,
        { user_answer: optionId }
      );
      const result = response.data.data;

      setQuiz((currentQuiz) => {
        if (!currentQuiz) return null;
        return {
          ...currentQuiz,
          questions: currentQuiz.questions.map((question) =>
            question.id === questionId
              ? {
                  ...question,
                  user_answer: optionId,
                  correct_answer: result.correct_answer,
                  explanations: result.explanations,
                  statements: result.statements,
                  is_correct: result.is_correct,
                  awarded_points: result.awarded_points,
                  ai_feedback: result.ai_feedback,
                }
              : question
          ),
        };
      });

      if (nextAnsweredCount === totalCount) {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    } catch (error) {
      console.error("Failed to save answer:", error);
      setAnswers((currentAnswers) => {
        const rollback = { ...currentAnswers };
        delete rollback[questionId];
        return rollback;
      });
      setNotice({
        message: "Your answer could not be saved. Please try again.",
        tone: "danger",
      });
    } finally {
      setSavingQuestionId(null);
    }
  };

  const handleResetQuiz = async () => {
    try {
      if (quiz.mode === "exam") {
        router.push(`/quizzes/${quizId}/exam`);
        return;
      }

      await api.delete(`/quizzes/${quizId}/progress`);
      setAnswers({});
      setExamResult(null);
      setQuiz((currentQuiz) => {
        if (!currentQuiz) return null;
        return {
          ...currentQuiz,
          questions: currentQuiz.questions.map((question) => ({
            ...question,
            user_answer: null,
            correct_answer: null,
            explanations: null,
            is_correct: null,
          })),
        };
      });
      setShowResetDialog(false);
      window.scrollTo({ top: 0, behavior: "smooth" });
      setNotice({ message: "Quiz progress has been reset.", tone: "success" });
      setReloadKey((current) => current + 1);
    } catch (error) {
      console.error("Failed to reset quiz:", error);
      setNotice({ message: "Quiz progress could not be reset.", tone: "danger" });
    }
  };

  const handleSubmitExam = async () => {
    const unanswered = quiz.questions.filter(
      (question) => !hasCompleteAnswer(question, answers[question.id])
    ).length;
    const confirmation = unanswered > 0
      ? `You still have ${unanswered} unanswered questions. Submit anyway?`
      : "Submit this exam now?";

    if (!window.confirm(confirmation)) return;

    try {
      setSubmitting(true);
      const answersPayload = quiz.questions.map((question) => ({
        question_id: question.id,
        user_answer: answers[question.id] ?? null,
      }));
      const response = await api.post(`/quizzes/${quizId}/submit`, {
        answers: answersPayload,
        submit_reason: "manual",
      });
      const result = response.data.data;
      setExamResult(result);
      setQuiz((currentQuiz) => {
        if (!currentQuiz) return null;
        return {
          ...currentQuiz,
          questions: currentQuiz.questions.map((question) => {
            const detail = result.details.find(
              (item: any) => item.question_id === question.id
            );
            return {
              ...question,
              correct_answer: detail?.correct_answer,
              explanations: detail?.explanations,
              statements: detail?.statements,
              user_answer: detail?.user_answer,
              is_correct: detail?.is_correct,
              awarded_points: detail?.awarded_points,
              ai_feedback: detail?.ai_feedback,
            };
          }),
        };
      });
      window.scrollTo({ top: 0, behavior: "smooth" });
      setNotice({ message: "Exam submitted successfully.", tone: "success" });
    } catch (error) {
      console.error("Failed to submit exam:", error);
      setNotice({ message: "The exam could not be submitted.", tone: "danger" });
    } finally {
      setSubmitting(false);
    }
  };

  const toggleFeedbackTag = (tag: FeedbackTag) => {
    setFeedbackTags((currentTags) =>
      currentTags.includes(tag)
        ? currentTags.filter((currentTag) => currentTag !== tag)
        : [...currentTags, tag]
    );
  };

  const handleSubmitFeedback = async () => {
    try {
      setSubmittingFeedback(true);
      setFeedbackError(null);
      await quizService.submitFeedback(quizId, {
        tags: feedbackTags,
        comment: feedbackComment.trim() || undefined,
      });
      setShowFeedbackDialog(false);
      setFeedbackTags([]);
      setFeedbackComment("");
      setNotice({ message: "Thank you for your feedback.", tone: "success" });
    } catch (error) {
      console.error("Failed to submit quiz feedback:", error);
      setFeedbackError("Feedback could not be sent. Please try again.");
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const hasFeedbackInput =
    feedbackTags.length > 0 || feedbackComment.trim().length > 0;
  const sourceDocuments = quiz.source_documents?.length
    ? quiz.source_documents
    : (quiz.source_document_ids || []).map((id) => ({
        id,
        title: `Source ${id}`,
      }));
  const indexedQuestions = quiz.questions.map((question, index) => ({
    question,
    index,
  }));
  const visibleQuestions =
    quiz.mode === "exam" && isSubmitted && reviewFilter !== "all"
      ? indexedQuestions.filter(
          ({ question }) => question.mark_status === reviewFilter
        )
      : indexedQuestions;

  return (
    <div className="h-full w-full min-w-0 overflow-y-scroll bg-background [scrollbar-gutter:stable]">
      {notice && (
        <div
          role="status"
          className={`fixed left-1/2 top-24 z-50 flex -translate-x-1/2 items-center gap-2.5 rounded-[10px] border bg-card px-5 py-3.5 text-sm font-medium shadow-lg ${
            notice.tone === "success"
              ? "border-chart-2/40 text-chart-2"
              : "border-destructive/30 text-destructive"
          }`}
        >
          <Icon
            name={notice.tone === "success" ? "check_circle" : "error_outline"}
            className="text-lg"
          />
          <span className="text-foreground">{notice.message}</span>
        </div>
      )}

      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-8">
        <header
          className={`overflow-hidden rounded-xl border bg-card shadow-xs ${
            isSubmitted
              ? "border-chart-2/30"
              : "border-border/80"
          }`}
        >
          <div className="p-5 sm:p-6">
          <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${
                    isSubmitted
                      ? "bg-chart-2/10 text-chart-2"
                      : "bg-primary/10 text-primary"
                  }`}
                >
                  <Icon
                    name={
                      isSubmitted
                        ? "check_circle"
                        : quiz.mode === "study"
                          ? "school"
                          : "assignment"
                    }
                    className="text-sm"
                  />
                  {isSubmitted
                    ? quiz.mode === "exam"
                      ? "Exam Completed"
                      : "Study Session Complete"
                    : quiz.mode === "study"
                      ? "Study mode"
                      : "Exam mode"}
                </span>

                <DropdownMenu>
                  <DropdownMenuTrigger
                    className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-[11px] font-medium text-muted-foreground outline-none transition-colors hover:border-primary/40 hover:text-foreground data-popup-open:border-primary/40 data-popup-open:text-foreground"
                    aria-label={`View ${sourceDocuments.length} quiz sources`}
                  >
                    <Icon name="library_books" className="text-sm" />
                    View {sourceDocuments.length} {sourceDocuments.length === 1 ? "source" : "sources"}
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    side="bottom"
                    align="start"
                    sideOffset={6}
                    className="w-64"
                  >
                    <DropdownMenuGroup>
                      <DropdownMenuLabel>Sources used for this quiz</DropdownMenuLabel>
                      {sourceDocuments.length > 0 ? (
                        sourceDocuments.map((document) => (
                          <DropdownMenuItem
                            key={document.id}
                            disabled
                            className="gap-1.5 px-2 py-1 text-[10px] opacity-100"
                          >
                            <Icon
                              name="picture_as_pdf"
                              className="text-[11px] text-muted-foreground"
                            />
                            <span className="truncate">{document.title}</span>
                          </DropdownMenuItem>
                        ))
                      ) : (
                        <DropdownMenuItem disabled className="text-xs opacity-100">
                          No source information available
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuGroup>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <h1 className="mt-3 break-words pb-0.5 font-heading text-xl font-semibold leading-[1.35] text-foreground sm:text-2xl">
                {quiz.title}
              </h1>
              {isSubmitted && (
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  {quiz.mode === "exam"
                    ? "Review your submitted answers and the explanations below."
                    : "Review the explanations below or start again for more practice."}
                </p>
              )}
            </div>
            <div className="rounded-[10px] border border-border bg-secondary/35 px-4 py-3 text-right">
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                Current score
              </p>
              <p className="mt-1 font-heading text-lg font-semibold text-foreground">
                {formatScore(earnedPoints)}/{formatScore(quiz.target_total_points)}
              </p>
            </div>
          </div>
          </div>

          {isSubmitted && (
            <div className="grid grid-cols-2 divide-x divide-border border-t border-chart-2/20 bg-chart-2/5 px-3 py-4 text-center sm:px-6">
              <div>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Accuracy</p>
                <p className="mt-1 font-heading text-lg font-semibold">{progressPercentage}%</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Correct</p>
                <p className="mt-1 font-heading text-lg font-semibold">
                  {correctCount}/{totalCount}
                </p>
              </div>
            </div>
          )}
        </header>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex h-8 items-center gap-1.5 rounded-[8px] px-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
          >
            <Icon name="arrow_back" className="text-base" />
            Back to list
          </button>

          {quiz.mode === "exam" && isSubmitted && (
            <div className="ml-auto flex flex-wrap justify-end gap-1">
              {(
                [
                  { value: "all", label: "All" },
                  { value: "review", label: "Reviewed", icon: "flag" },
                  { value: "critical", label: "Critical", icon: "priority_high" },
                ] as Array<{ value: ReviewFilter; label: string; icon?: string }>
              ).map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setReviewFilter(option.value)}
                  className={`inline-flex h-8 items-center rounded-full border px-3 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 ${
                    reviewFilter === option.value
                      ? `border-border/80 bg-card shadow-xs ${
                          option.value === "review"
                            ? "text-chart-1"
                            : option.value === "critical"
                              ? "text-destructive"
                              : "text-foreground"
                        }`
                      : `border-transparent bg-transparent ${
                          option.value === "review"
                            ? "text-chart-1 hover:bg-chart-1/5"
                            : option.value === "critical"
                              ? "text-destructive hover:bg-destructive/5"
                              : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                        }`
                  }`}
                >
                  {option.icon && (
                    <Icon
                      name={option.icon}
                      className={`text-sm ${
                        option.value === "critical" ? "mr-0.5" : "mr-1"
                      }`}
                    />
                  )}
                  {option.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <main className="mt-5 space-y-4">
          {quiz.questions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card p-10 text-center">
              <Icon name="quiz" className="text-3xl text-muted-foreground" />
              <h2 className="mt-3 font-heading text-base font-semibold">No questions available</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                This quiz does not contain any questions yet.
              </p>
            </div>
          ) : visibleQuestions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card p-10 text-center">
              <Icon name="search_off" className="text-3xl text-muted-foreground" />
              <h2 className="mt-3 font-heading text-base font-semibold">
                No questions in this filter
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Choose another filter to continue reviewing.
              </p>
            </div>
          ) : (
            visibleQuestions.map(({ question, index }) => (
              <QuizQuestionCard
                key={question.id}
                index={index}
                questionId={question.id}
                questionText={question.question_text}
                questionType={question.question_type}
                options={question.options}
                statements={question.statements}
                correctAnswer={question.correct_answer}
                explanations={question.explanations}
                selectedOptionId={answers[question.id] ?? question.user_answer}
                onSelectOption={(optionId) =>
                  handleAnswerQuestion(question.id, optionId)
                }
                onChangeAnswer={
                  (quiz.mode === "study" && ["multiple_response", "true_false"].includes(question.question_type)) ||
                  (quiz.mode === "exam" && ["fill_blank", "short_answer", "essay"].includes(question.question_type))
                    ? (answer) => setAnswers((current) => ({ ...current, [question.id]: answer }))
                    : undefined
                }
                mode={quiz.mode}
                points={question.points}
                awardedPoints={question.awarded_points}
                isCorrect={question.is_correct}
                aiFeedback={question.ai_feedback}
                hint={question.hint}
                markStatus={question.mark_status}
                isSaving={savingQuestionId === question.id}
                readOnly={quiz.mode === "exam" && isSubmitted}
                allowAnswerChanges={
                  quiz.mode === "exam" ||
                  ["multiple_response", "true_false"].includes(question.question_type)
                }
                onExplain={
                  onExplainQuestion &&
                  ((quiz.mode === "study" &&
                    (question.awarded_points !== undefined && question.awarded_points !== null ||
                      question.is_correct !== undefined && question.is_correct !== null)) ||
                    (quiz.mode === "exam" && isSubmitted)) &&
                  question.correct_answer !== undefined &&
                  question.correct_answer !== null
                    ? () =>
                        onExplainQuestion(
                          buildExplainPrompt(question),
                          quiz.source_document_ids || []
                        )
                    : undefined
                }
              />
            ))
          )}
        </main>

        <div className="sticky bottom-0 z-20 mt-6 rounded-xl border border-border/80 bg-card/95 p-4 shadow-lg backdrop-blur-sm">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="w-full sm:max-w-lg sm:flex-1">
              <p className="text-xs font-medium text-foreground">
                {answeredCount}/{totalCount} questions answered
              </p>
              <div
                className="mt-2 h-2 overflow-hidden rounded-full bg-secondary"
                role="progressbar"
                aria-label="Quiz completion"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={completionPercentage}
              >
                <div
                  className="h-full rounded-full bg-primary transition-[width] duration-300"
                  style={{ width: `${completionPercentage}%` }}
                />
              </div>
            </div>
            <div className="flex gap-2">
              {(quiz.mode === "study" || isExamSubmitted) && (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setFeedbackError(null);
                    setShowFeedbackDialog(true);
                  }}
                >
                  <Icon name="rate_review" className="text-base" />
                  Feedback
                </Button>
              )}
              {(quiz.mode === "study" || (quiz.mode === "exam" && isSubmitted)) && (
                <Button variant="outline" onClick={() => setShowResetDialog(true)}>
                  <Icon name="restart_alt" className="text-base" />
                  Start over
                </Button>
              )}
              {quiz.mode === "exam" && !isSubmitted && (
                <Button onClick={handleSubmitExam} disabled={submitting}>
                  {submitting && (
                    <Icon name="progress_activity" className="animate-spin text-base" />
                  )}
                  {submitting ? "Submitting..." : "Submit exam"}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <Dialog open={showResetDialog} onOpenChange={setShowResetDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-lg">Start this quiz over?</DialogTitle>
            <DialogDescription>
              {quiz.mode === "exam"
                ? "Your submitted attempt will remain in your history. A new exam attempt will be started."
                : "Your saved study progress for this attempt will be cleared. This action cannot be undone."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowResetDialog(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleResetQuiz}>
              {quiz.mode === "exam" ? "Restart exam" : "Reset progress"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showFeedbackDialog} onOpenChange={setShowFeedbackDialog}>
        <DialogContent className="gap-0 overflow-hidden p-0 sm:max-w-lg">
          <DialogHeader className="border-b border-border px-6 py-5">
            <DialogTitle className="text-base">Share feedback</DialogTitle>
          </DialogHeader>

          <div className="space-y-5 px-6 py-5">
            <fieldset className="space-y-3">
              <legend className="text-xs font-medium text-foreground">
                What could be improved?
              </legend>
              <div className="flex flex-wrap gap-2">
                {FEEDBACK_TAGS.map((tag) => {
                  const selected = feedbackTags.includes(tag.value);
                  return (
                    <button
                      key={tag.value}
                      type="button"
                      role="checkbox"
                      aria-checked={selected}
                      onClick={() => toggleFeedbackTag(tag.value)}
                      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 ${
                        selected
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border bg-transparent text-muted-foreground hover:border-primary/50 hover:text-foreground"
                      }`}
                    >
                      {selected && <Icon name="check" className="text-sm" />}
                      {tag.label}
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <div className="space-y-2">
              <Textarea
                id="quiz-feedback-comment"
                value={feedbackComment}
                onChange={(event) => setFeedbackComment(event.target.value)}
                maxLength={1000}
                placeholder="Share details (optional)"
                className="min-h-28 resize-none"
                aria-label="Additional feedback details"
              />
              <p className="text-right text-[10px] text-muted-foreground">
                {feedbackComment.length}/1000
              </p>
            </div>

            {feedbackError && (
              <div className="flex items-center gap-2 rounded-[8px] border border-destructive/25 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                <Icon name="error_outline" className="text-base" />
                {feedbackError}
              </div>
            )}
          </div>

          <DialogFooter className="items-center border-t border-border bg-secondary/20 px-6 py-4 sm:justify-between">
            <p className="max-w-xs text-[10px] leading-4 text-muted-foreground">
              Your feedback helps personalize the difficulty and style of future quizzes.
            </p>
            <Button
              onClick={handleSubmitFeedback}
              disabled={submittingFeedback || !hasFeedbackInput}
            >
              {submittingFeedback && (
                <Icon name="progress_activity" className="animate-spin text-base" />
              )}
              {submittingFeedback ? "Sending..." : "Send feedback"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
