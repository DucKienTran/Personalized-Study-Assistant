"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";

import QuizRunner from "@/components/quizzes/QuizRunner";
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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Difficulty,
  ExamHistoryItem,
  GenerateQuizPayload,
  QuizItem,
  QuizMode,
  QuestionType,
  quizService,
} from "@/services/quiz.service";

interface QuizzesTabProps {
  notebookId: number;
  activeDocumentCount: number;
  onQuizCreated: () => void;
  selectedQuizId: number | null;
  onSelectQuiz: (quizId: number) => void;
  onCloseQuiz: () => void;
  onExplainQuestion: (content: string, sourceDocumentIds: number[]) => void | Promise<void>;
}

const DIFFICULTY_OPTIONS: Array<{
  value: Difficulty;
  label: string;
  description: string;
}> = [
  { value: "easy", label: "Easy", description: "Direct knowledge recall" },
  { value: "medium", label: "Medium", description: "Connect related concepts" },
  { value: "hard", label: "Hard", description: "Multi-step reasoning" },
  { value: "mixed", label: "Mixed", description: "30% easy, 50% medium, 20% hard" },
];

const QUESTION_TYPE_OPTIONS: Array<{ value: QuestionType; label: string }> = [
  { value: "multiple_choice", label: "Multiple Choice" },
  { value: "multiple_response", label: "Multiple Select" },
  { value: "true_false", label: "True / False statements" },
  { value: "fill_blank", label: "Fill Blank" },
  { value: "short_answer", label: "Short Answer" },
  { value: "essay", label: "Essay" },
];

function buildDifficultyDistribution(
  difficulty: Difficulty,
  totalQuestions: number
): GenerateQuizPayload["difficulty_distribution"] {
  if (difficulty === "easy") {
    return { easy: totalQuestions, medium: 0, hard: 0 };
  }
  if (difficulty === "medium") {
    return { easy: 0, medium: totalQuestions, hard: 0 };
  }
  if (difficulty === "hard") {
    return { easy: 0, medium: 0, hard: totalQuestions };
  }

  const easy = Math.floor(totalQuestions * 0.3);
  const hard = Math.floor(totalQuestions * 0.2);
  return {
    easy,
    medium: totalQuestions - easy - hard,
    hard,
  };
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "Unable to create the quiz. Please try again."
    );
  }
  return "Unable to create the quiz. Please try again.";
}

function getHistoryErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || "Unable to load exam history. Please try again.";
  }
  return "Unable to load exam history. Please try again.";
}

function statusLabel(quiz: QuizItem): string {
  if (quiz.derived_status === "processing") return "Generating";
  if (quiz.derived_status === "failed") return "Generation failed";
  if (quiz.derived_status === "in_progress") return "In progress";
  if (quiz.derived_status === "completed") return "Completed";
  return "Not started";
}

function statusStyle(quiz: QuizItem): string {
  if (quiz.derived_status === "completed") {
    return "border-chart-2/30 bg-chart-2/10 text-chart-2";
  }
  if (quiz.derived_status === "in_progress") {
    return "border-accent/30 bg-accent/10 text-accent";
  }
  if (quiz.derived_status === "todo") {
    return "border-chart-1/30 bg-chart-1/10 text-chart-1";
  }
  if (quiz.derived_status === "failed") {
    return "border-destructive/25 bg-destructive/5 text-destructive";
  }
  return "border-primary/20 bg-primary/5 text-primary";
}

function difficultyLabel(quiz: QuizItem): string {
  const distribution = quiz.difficulty_distribution;
  if (!distribution) return "Mixed";

  const activeLevels = ["easy", "medium", "hard"].filter(
    (level) => Number(distribution[level] ?? 0) > 0
  );
  if (activeLevels.length !== 1) return "Mixed";

  const level = activeLevels[0];
  return level.charAt(0).toUpperCase() + level.slice(1);
}

function normalizeSearchText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

function formatQuizDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatScore(value: number | null): string {
  if (value === null) return "No score";
  return `${Math.round((value + Number.EPSILON) * 100) / 100} points`;
}

function getQuestionCountError(value: string): string | null {
  if (!value.trim()) return "Number of questions is required.";
  if (!/^\d+$/.test(value)) return "Enter a whole number from 1 to 50.";

  const questionCount = Number(value);
  if (questionCount < 1 || questionCount > 50) {
    return "Enter a whole number from 1 to 50.";
  }
  return null;
}

function getPositiveIntegerError(value: string, label: string): string | null {
  if (!value.trim()) return `${label} is required.`;
  if (!/^\d+$/.test(value) || Number(value) < 1) {
    return `${label} must be a positive whole number.`;
  }
  return null;
}

function getPositiveDecimalError(value: string, label: string): string | null {
  if (!value.trim()) return `${label} is required.`;
  if (!/^\d+(\.\d{1,2})?$/.test(value) || Number(value) <= 0) {
    return `${label} must be positive with at most two decimal places.`;
  }
  return null;
}

export function QuizzesTab({
  notebookId,
  activeDocumentCount,
  onQuizCreated,
  selectedQuizId,
  onSelectQuiz,
  onCloseQuiz,
  onExplainQuestion,
}: QuizzesTabProps) {
  const router = useRouter();
  const [quizzes, setQuizzes] = useState<QuizItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [quizMode, setQuizMode] = useState<QuizMode>("study");
  const [questionTypes, setQuestionTypes] = useState<QuestionType[]>(["multiple_choice"]);
  const [totalQuestions, setTotalQuestions] = useState("10");
  const [timeLimitMinutes, setTimeLimitMinutes] = useState("30");
  const [targetTotalPoints, setTargetTotalPoints] = useState("100");
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [customInstruction, setCustomInstruction] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [isSearchPending, setIsSearchPending] = useState(false);
  const [deletingQuizId, setDeletingQuizId] = useState<number | null>(null);
  const [pendingExam, setPendingExam] = useState<QuizItem | null>(null);
  const [showExamHistory, setShowExamHistory] = useState(false);
  const [examHistory, setExamHistory] = useState<ExamHistoryItem[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedAttemptId, setSelectedAttemptId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    quizService
      .listQuizzes(notebookId)
      .then((data) => {
        if (!cancelled) setQuizzes(data);
      })
      .catch((loadError) => {
        if (!cancelled) setError(getErrorMessage(loadError));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [notebookId]);

  const hasProcessingQuiz = quizzes.some(
    (quiz) => quiz.generation_status === "processing"
  );

  useEffect(() => {
    if (!hasProcessingQuiz) return;

    const timer = window.setInterval(() => {
      quizService
        .listQuizzes(notebookId)
        .then(setQuizzes)
        .catch(() => undefined);
    }, 3000);

    return () => window.clearInterval(timer);
  }, [hasProcessingQuiz, notebookId]);

  useEffect(() => {
    if (searchInput === searchKeyword) {
      setIsSearchPending(false);
      return;
    }

    setIsSearchPending(true);
    const timer = window.setTimeout(() => {
      setSearchKeyword(searchInput);
      setIsSearchPending(false);
    }, 180);

    return () => window.clearTimeout(timer);
  }, [searchInput, searchKeyword]);

  const normalizedKeyword = normalizeSearchText(searchKeyword.trim());
  const filteredQuizzes = normalizedKeyword
    ? quizzes.filter((quiz) =>
        normalizeSearchText(quiz.title).includes(normalizedKeyword)
      )
    : quizzes;
  const filteredHistory = normalizedKeyword
    ? examHistory.filter((item) =>
        normalizeSearchText(item.title).includes(normalizedKeyword)
      )
    : examHistory;

  const questionCountError = getQuestionCountError(totalQuestions);
  const timeLimitError =
    quizMode === "exam"
      ? getPositiveIntegerError(timeLimitMinutes, "Time limit")
      : null;
  const targetPointsFormatError =
    quizMode === "exam"
      ? getPositiveDecimalError(targetTotalPoints, "Total points")
      : null;
  const targetPointsError =
    targetPointsFormatError ||
    (quizMode === "exam" &&
    !questionCountError &&
    Number(targetTotalPoints) < Number(totalQuestions) * 0.01
      ? "Total points must allow at least 0.01 point per question."
      : null);
  const configurationError =
    questionCountError || timeLimitError || targetPointsError ||
    (questionTypes.length === 0 ? "Select at least one question type." : null);
  const hasActiveDocuments = activeDocumentCount > 0;
  const noActiveDocumentsHint =
    "Please select at least one document to generate a quiz";

  const handleDialogOpenChange = (open: boolean) => {
    setIsDialogOpen(open);
    if (!open) setCustomInstruction("");
  };

  const handleGenerate = async () => {
    if (activeDocumentCount === 0 || configurationError) return;

    const questionCount = Number(totalQuestions);

    try {
      setIsGenerating(true);
      setError(null);
      await quizService.generate({
        notebook_id: notebookId,
        generation_strategy: "manual",
        question_types: questionTypes,
        difficulty_distribution: buildDifficultyDistribution(
          difficulty,
          questionCount
        ),
        total_questions: questionCount,
        target_total_points:
          quizMode === "exam" ? Number(targetTotalPoints) : 100,
        mode: quizMode,
        time_limit_minutes:
          quizMode === "exam" ? Number(timeLimitMinutes) : undefined,
        custom_instruction: customInstruction.trim() || null,
      });

      onQuizCreated();
      setQuizzes(await quizService.listQuizzes(notebookId));
      handleDialogOpenChange(false);
    } catch (generateError) {
      setError(getErrorMessage(generateError));
    } finally {
      setIsGenerating(false);
    }
  };

  const openDialog = () => {
    setError(null);
    handleDialogOpenChange(true);
  };

  const handleDeleteQuiz = async (quiz: QuizItem) => {
    if (!window.confirm(`Delete "${quiz.title}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeletingQuizId(quiz.id);
      setError(null);
      await quizService.delete(quiz.id);
      setQuizzes((current) => current.filter((item) => item.id !== quiz.id));
    } catch (deleteError) {
      setError(getErrorMessage(deleteError));
    } finally {
      setDeletingQuizId(null);
    }
  };

  const handleOpenQuiz = (quiz: QuizItem) => {
    if (quiz.mode === "exam" && quiz.derived_status === "todo") {
      setPendingExam(quiz);
      return;
    }

    if (quiz.mode === "exam" && quiz.derived_status === "in_progress") {
      router.push(`/quizzes/${quiz.id}/exam`);
      return;
    }

    onSelectQuiz(quiz.id);
  };

  const openExamHistory = async () => {
    setShowExamHistory(true);
    setSearchInput("");
    setSearchKeyword("");
    setIsHistoryLoading(true);
    setHistoryError(null);
    try {
      setExamHistory(await quizService.listExamHistory(notebookId));
    } catch (loadError) {
      setHistoryError(getHistoryErrorMessage(loadError));
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleOpenHistoryItem = (item: ExamHistoryItem) => {
    setSelectedAttemptId(item.attempt_id);
    onSelectQuiz(item.id);
  };

  if (selectedQuizId !== null) {
    return (
      <QuizRunner
        key={selectedQuizId}
        quizId={selectedQuizId}
        attemptId={selectedAttemptId}
        onExplainQuestion={onExplainQuestion}
        onBack={() => {
            onCloseQuiz();
            setSelectedAttemptId(null);
          quizService.listQuizzes(notebookId).then(setQuizzes).catch(() => undefined);
        }}
      />
    );
  }

  return (
    <div className="relative flex h-full flex-1 flex-col overflow-hidden bg-background">
      <div className="flex shrink-0 items-center gap-2 border-b border-border/60 bg-card/40 px-6 py-2.5">
        <div className="relative min-w-0 flex-1">
          <Icon
            name="search"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-base text-muted-foreground"
          />
          <Input
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={showExamHistory ? "Search exam history..." : "Search quizzes..."}
            className="h-8 w-full pl-9 pr-9 text-xs"
            aria-label={showExamHistory ? "Search exam history" : "Search quizzes"}
          />
          {isSearchPending && (
            <Icon
              name="progress_activity"
              className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-sm text-muted-foreground"
            />
          )}
        </div>

        {!showExamHistory && <Button
          type="button"
          variant="secondary"
          size="icon-sm"
          className="rounded-[8px]"
          title="Exam history"
          aria-label="Exam history"
          onClick={openExamHistory}
        >
          <Icon name="history" className="text-base" />
        </Button>}

        {!showExamHistory && <span
          className="inline-flex"
          title={hasActiveDocuments ? undefined : noActiveDocumentsHint}
        >
          <Button
            size="sm"
            className="rounded-[8px] text-xs"
            disabled={!hasActiveDocuments}
            onClick={openDialog}
          >
            <Icon name="add" className="text-base" />
            Create Quiz
          </Button>
        </span>}
      </div>

      {error && !isDialogOpen && (
        <div className="mx-6 mt-4 flex items-center gap-2 rounded-[8px] border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          <Icon name="error_outline" className="text-base" />
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        {showExamHistory && (
          <div className="mb-5 flex items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              title="Back to quizzes"
              aria-label="Back to quizzes"
              onClick={() => {
                setShowExamHistory(false);
                setSearchInput("");
                setSearchKeyword("");
              }}
            >
              <Icon name="arrow_back" className="text-base" />
            </Button>
            <h2 className="font-heading text-lg font-semibold">Exam History</h2>
          </div>
        )}
        {showExamHistory && isHistoryLoading ? (
          <div className="flex h-full min-h-80 items-center justify-center gap-2 text-xs text-muted-foreground">
            <Icon name="progress_activity" className="animate-spin text-lg" />
            Loading exam history...
          </div>
        ) : showExamHistory && historyError ? (
          <div className="rounded-[8px] border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            {historyError}
          </div>
        ) : showExamHistory && examHistory.length === 0 ? (
          <div className="flex h-full min-h-80 flex-col items-center justify-center text-center">
            <Icon name="history" className="text-3xl text-muted-foreground" />
            <h3 className="mt-3 font-heading text-lg font-semibold">No exam history yet</h3>
            <p className="mt-2 text-xs text-muted-foreground">Completed exams will appear here.</p>
          </div>
        ) : isLoading ? (
          <div className="flex h-full min-h-80 items-center justify-center gap-2 text-xs text-muted-foreground">
            <Icon name="progress_activity" className="animate-spin text-lg" />
            Loading quizzes...
          </div>
        ) : quizzes.length === 0 ? (
          <div className="flex h-full min-h-80 flex-col items-center justify-center text-center">
            <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Icon name="quiz" className="text-3xl" />
            </span>
            <h3 className="font-heading text-lg font-semibold text-foreground">
              No quizzes yet
            </h3>
            <p className="mt-2 max-w-sm text-xs leading-5 text-muted-foreground">
              Create a quiz to practice with questions from your active documents.
            </p>
            <span
              className="mt-5 inline-flex"
              title={hasActiveDocuments ? undefined : noActiveDocumentsHint}
            >
              <Button
                size="sm"
                className="rounded-[8px] text-xs"
                disabled={!hasActiveDocuments}
                onClick={openDialog}
              >
                <Icon name="add" className="text-base" />
                Create Quiz
              </Button>
            </span>
          </div>
        ) : (
          <div className="relative w-full">
            {isSearchPending && (
              <div className="pointer-events-none absolute inset-0 z-10 rounded-xl bg-background/35" />
            )}

            {(showExamHistory ? filteredHistory : filteredQuizzes).length === 0 ? (
              <div className="rounded-xl border border-dashed border-border bg-card px-6 py-12 text-center">
                <Icon name="search_off" className="text-3xl text-muted-foreground" />
                <p className="mt-3 text-sm font-medium text-foreground">
                  {showExamHistory
                    ? "No exam history matches your search"
                    : "No quizzes match your search"}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {(showExamHistory ? filteredHistory : filteredQuizzes).map((quiz) => {
                  const historyItem = showExamHistory ? quiz as ExamHistoryItem : null;
                  const canOpen = ["todo", "in_progress", "completed"].includes(
                    quiz.derived_status
                  );
                  const isPending = quiz.derived_status === "processing";
                  const isDeleting = deletingQuizId === quiz.id;

                  return (
                    <div
                      key={historyItem ? historyItem.attempt_id : quiz.id}
                      className={`group rounded-[10px] border border-border/80 bg-card p-4 shadow-2xs transition-[border-color,box-shadow] ${
                        canOpen ? "hover:border-primary/40 hover:shadow-xs" : ""
                      } ${isPending ? "opacity-65" : ""}`}
                    >
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          disabled={!canOpen || isDeleting}
                          onClick={() => historyItem ? handleOpenHistoryItem(historyItem) : handleOpenQuiz(quiz)}
                          className="flex min-w-0 flex-1 items-center gap-4 text-left disabled:cursor-default"
                          aria-label={canOpen ? `Open ${quiz.title}` : undefined}
                        >
                      <span
                        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[8px] ${
                          quiz.mode === "exam"
                            ? "bg-[#a05a4a]/10 text-[#8c4e40]"
                            : "bg-[#8a8175]/12 text-[#6f675e]"
                        }`}
                        title={quiz.mode === "exam" ? "Exam" : "Study"}
                        aria-label={quiz.mode === "exam" ? "Exam quiz" : "Study quiz"}
                      >
                           <Icon
                              name={quiz.mode === "exam" ? "edit_document" : "history_edu"}
                              size={quiz.mode === "exam" ? 18 : 23}
                           />
                      </span>
                      <div className="min-w-0 flex-1">
                         <h4 className="truncate py-px text-sm font-semibold leading-[1.5] text-foreground">
                          {quiz.title}
                        </h4>
                        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                          <span>{quiz.total_questions} questions</span>
                          <span aria-hidden>·</span>
                          {historyItem ? (
                            <>
                              <span>{formatQuizDate(historyItem.submitted_at ?? historyItem.created_at)}</span>
                              <span aria-hidden>·</span>
                              <span>{formatScore(historyItem.score)}</span>
                            </>
                          ) : (
                            <>
                              <span>{difficultyLabel(quiz)}</span>
                              <span aria-hidden>·</span>
                              <span>{formatQuizDate(quiz.created_at)}</span>
                            </>
                          )}
                        </div>
                        {quiz.error_message && (
                          <p className="mt-2 line-clamp-1 text-[11px] text-destructive">
                            {quiz.error_message}
                          </p>
                        )}
                      </div>
                        </button>

                        {!historyItem && <div className="flex shrink-0 items-center gap-1.5">
                          <DropdownMenu>
                            <DropdownMenuTrigger
                              disabled={isDeleting}
                              className="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded-md text-muted-foreground opacity-0 outline-none transition hover:bg-secondary focus-visible:opacity-100 group-hover:opacity-100 data-popup-open:bg-secondary data-popup-open:opacity-100 disabled:cursor-not-allowed disabled:opacity-50"
                              title="More options"
                              aria-label={`More options for ${quiz.title}`}
                            >
                              <Icon
                                name={isDeleting ? "progress_activity" : "more_vert"}
                                className={`text-base ${isDeleting ? "animate-spin" : ""}`}
                              />
                            </DropdownMenuTrigger>
                            <DropdownMenuContent
                              side="top"
                              align="end"
                              sideOffset={6}
                              className="w-32 min-w-0 p-0.5"
                            >
                              <DropdownMenuItem
                                variant="destructive"
                                onClick={() => handleDeleteQuiz(quiz)}
                                className="cursor-pointer gap-1.5 px-1.5 py-0.5 text-[11px]"
                              >
                                <Icon name="delete" className="text-[11px]" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>

                          <span
                            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium ${statusStyle(quiz)}`}
                          >
                            {isPending && (
                              <Icon name="progress_activity" className="animate-spin text-xs" />
                            )}
                            {statusLabel(quiz)}
                          </span>
                        </div>}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      <Dialog open={isDialogOpen} onOpenChange={handleDialogOpenChange}>
        <DialogContent className="gap-0 p-0 sm:max-w-xl">
          <DialogHeader className="border-b border-border px-6 py-5">
            <DialogTitle className="text-base">Create a quiz</DialogTitle>
          </DialogHeader>

          <div className="max-h-[70vh] space-y-5 overflow-y-auto px-6 py-5">
            <div>
              <fieldset className="space-y-2">
                <legend className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Mode
                </legend>
                <div className="grid grid-cols-2 gap-2">
                  {(["study", "exam"] as QuizMode[]).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setQuizMode(mode)}
                      className={`rounded-[8px] border px-3 py-2.5 text-left text-xs font-medium capitalize transition-colors ${
                        quizMode === mode
                          ? "border-primary bg-primary/5 text-primary"
                          : "border-border bg-card text-foreground hover:border-primary/40"
                      }`}
                      aria-pressed={quizMode === mode}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </fieldset>
            </div>

            <fieldset className="space-y-2">
              <legend className="text-xs font-medium">Question types</legend>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {QUESTION_TYPE_OPTIONS.map((option) => {
                  const selected = questionTypes.includes(option.value);
                  return (
                    <button
                      key={option.value}
                      type="button"
                      role="checkbox"
                      aria-checked={selected}
                      onClick={() => setQuestionTypes((current) =>
                        selected
                          ? current.filter((type) => type !== option.value)
                          : [...current, option.value]
                      )}
                      className={`rounded-[8px] border px-3 py-2 text-left text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-45 ${
                        selected ? "border-primary bg-primary/5 text-primary" : "border-border bg-card"
                      }`}
                    >
                      <span className="inline-flex items-center gap-2">
                        <Icon name={selected ? "check_box" : "check_box_outline_blank"} className="text-base" />
                        {option.label}
                      </span>
                    </button>
                  );
                })}
              </div>
              {questionTypes.length === 0 && <p className="text-[11px] text-destructive">Select at least one question type.</p>}
            </fieldset>

            {quizMode === "exam" && (
              <div className="grid gap-4 rounded-[10px] border border-accent/25 bg-accent/5 p-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label htmlFor="quiz-time-limit" className="text-xs font-medium">
                    Time limit (minutes)
                  </label>
                  <Input
                    id="quiz-time-limit"
                    type="number"
                    min={1}
                    step={1}
                    value={timeLimitMinutes}
                    onChange={(event) => setTimeLimitMinutes(event.target.value)}
                    aria-invalid={Boolean(timeLimitError)}
                    className="h-9 text-sm"
                  />
                  {timeLimitError && (
                    <p className="text-[11px] text-destructive">{timeLimitError}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <label htmlFor="quiz-target-points" className="text-xs font-medium">
                    Total points
                  </label>
                  <Input
                    id="quiz-target-points"
                    type="number"
                    min={0.01}
                    step={0.01}
                    value={targetTotalPoints}
                    onChange={(event) => setTargetTotalPoints(event.target.value)}
                    aria-invalid={Boolean(targetPointsError)}
                    className="h-9 text-sm"
                  />
                  {targetPointsError && (
                    <p className="text-[11px] text-destructive">{targetPointsError}</p>
                  )}
                </div>
              </div>
            )}

            <div className="space-y-2">
              <label htmlFor="quiz-question-count" className="text-xs font-medium">
                Number of questions
              </label>
              <Input
                id="quiz-question-count"
                type="text"
                inputMode="numeric"
                value={totalQuestions}
                onChange={(event) => setTotalQuestions(event.target.value)}
                aria-invalid={Boolean(questionCountError)}
                aria-describedby={questionCountError ? "quiz-question-count-error" : undefined}
                className="h-9 text-sm"
              />
              {questionCountError ? (
                <p id="quiz-question-count-error" className="text-[11px] text-destructive">
                  {questionCountError}
                </p>
              ) : (
                <p className="text-[11px] text-muted-foreground">
                  Choose between 1 and 50 questions.
                </p>
              )}
            </div>

            <fieldset className="space-y-2">
              <legend className="text-xs font-medium">Difficulty</legend>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {DIFFICULTY_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setDifficulty(option.value)}
                    className={`rounded-[8px] border px-3 py-2.5 text-left transition-colors ${
                      difficulty === option.value
                        ? "border-primary bg-primary/5 text-primary"
                        : "border-border bg-card text-foreground hover:border-primary/40"
                    }`}
                  >
                    <span className="block text-xs font-medium">{option.label}</span>
                    <span className="mt-1 block text-[10px] leading-4 text-muted-foreground">
                      {option.description}
                    </span>
                  </button>
                ))}
              </div>
            </fieldset>

            <div className="space-y-2">
              <label htmlFor="quiz-personal-instructions" className="text-xs font-medium">
                Personal instructions
              </label>
              <Textarea
                id="quiz-personal-instructions"
                value={customInstruction}
                onChange={(event) => setCustomInstruction(event.target.value)}
                placeholder="e.g., Focus on Chapter 3, make questions extra detailed..."
                className="min-h-20 resize-none text-xs"
              />
              <p className="text-[11px] text-muted-foreground">
                Optional instructions override conflicting quiz settings.
              </p>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-[8px] border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                <Icon name="error_outline" className="mt-0.5 text-base" />
                <span>{error}</span>
              </div>
            )}
          </div>

          <DialogFooter className="border-t border-border bg-secondary/20 px-6 py-4">
            <Button
              variant="outline"
              onClick={() => handleDialogOpenChange(false)}
              disabled={isGenerating}
            >
              Cancel
            </Button>
            <span
              className="inline-flex"
              title={hasActiveDocuments ? undefined : noActiveDocumentsHint}
            >
              <Button
                onClick={handleGenerate}
                disabled={isGenerating || !hasActiveDocuments || Boolean(configurationError)}
              >
                {isGenerating ? (
                  <Icon name="progress_activity" className="animate-spin text-base" />
                ) : (
                  <Icon name="auto_awesome" className="text-base" />
                )}
                {isGenerating ? "Creating..." : "Create Quiz"}
              </Button>
            </span>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={pendingExam !== null}
        onOpenChange={(open) => {
          if (!open) setPendingExam(null);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg">Start this exam?</DialogTitle>
            <DialogDescription className="leading-5">
              You are about to begin <span className="font-medium text-foreground">{pendingExam?.title}</span>.
              {pendingExam?.time_limit_minutes
                ? ` You will have ${pendingExam.time_limit_minutes} minutes.`
                : ""}
              {" "}The session cannot be paused once it starts.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingExam(null)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!pendingExam) return;
                const examId = pendingExam.id;
                setPendingExam(null);
                router.push(`/quizzes/${examId}/exam`);
              }}
            >
              <Icon name="play_arrow" className="text-base" />
              Start exam
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
