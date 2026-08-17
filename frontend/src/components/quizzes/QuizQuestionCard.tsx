"use client";

import { useEffect, useRef, useState } from "react";

import { Icon } from "@/components/shared/icons";

interface Option {
  id: string | number;
  option_text: string;
}

interface Statement {
  text: string;
  correct_answer?: boolean;
  explanation?: string;
}

interface QuestionProps {
  index: number;
  questionId: number;
  questionText: string;
  questionType: string;
  options?: Option[] | null;
  statements?: Statement[] | null;
  correctAnswer: unknown;
  explanations: unknown;
  selectedOptionId: unknown;
  onSelectOption: (answer: unknown) => void;
  onChangeAnswer?: (answer: unknown) => void;
  mode: "study" | "exam";
  points?: number;
  awardedPoints?: number | null;
  isCorrect?: boolean | null;
  aiFeedback?: string | null;
  hint?: string;
  isSaving?: boolean;
  readOnly?: boolean;
  allowAnswerChanges?: boolean;
  markStatus?: "review" | "critical" | null;
  onExplain?: () => void | Promise<void>;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isVietnameseQuestion(value: string): boolean {
  return /[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i.test(value) ||
    /\b(câu|đáp án|không|đúng|sai|hãy|trình bày|phân tích)\b/i.test(value);
}

function formatPointValue(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Math.round(value * 100) / 100);
}

function matchesOption(value: unknown, option: Option): boolean {
  if (value === undefined || value === null) return false;
  if (Number(value) === Number(option.id)) return true;

  const optionText = option.option_text.trim();
  const valueText = String(value).trim();
  const labelPattern = new RegExp(`^${escapeRegExp(valueText)}\\s*[.\\-:]`, "i");
  return labelPattern.test(optionText) || optionText.toLowerCase() === valueText.toLowerCase();
}

function getOptionExplanation(explanations: unknown, option: Option): string | null {
  if (!explanations) return null;
  if (typeof explanations === "string") return explanations;
  if (typeof explanations !== "object") return null;

  const explanationMap = explanations as Record<string, string>;
  const optionLabel = option.option_text.match(/^([^\.\-:]+)\s*[\.\-:]/)?.[1]?.trim();
  const candidates = [String(option.id), optionLabel, option.option_text].filter(
    (candidate): candidate is string => Boolean(candidate)
  );
  for (const candidate of candidates) {
    const key = Object.keys(explanationMap).find(
      (item) => item.toLowerCase() === candidate.toLowerCase()
    );
    if (key) return explanationMap[key];
  }
  return null;
}

function TextAnswer({
  value,
  multiline,
  readOnly,
  placeholder,
  onCommit,
  submitLabel,
  onValueChange,
}: {
  value: unknown;
  multiline: boolean;
  readOnly: boolean;
  placeholder: string;
  onCommit: (value: string) => void;
  submitLabel?: string;
  onValueChange?: (value: string) => void;
}) {
  const [draft, setDraft] = useState(String(value ?? ""));

  useEffect(() => setDraft(String(value ?? "")), [value]);

  const classes =
    "w-full rounded-[10px] border border-border bg-background px-3 py-2.5 text-sm text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-default disabled:bg-muted/30";
  if (multiline) {
    return (
      <div>
        <textarea
          value={draft}
          onChange={(event) => {
            setDraft(event.target.value);
            onValueChange?.(event.target.value);
          }}
          disabled={readOnly}
          rows={6}
          placeholder={placeholder}
          className={`${classes} resize-y`}
        />
        {submitLabel && (
          <button
            type="button"
            disabled={readOnly || !draft.trim()}
            onClick={() => onCommit(draft)}
            className="mt-3 inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-transform active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100"
          >
            {submitLabel}
          </button>
        )}
      </div>
    );
  }
  return (
    <input
      value={draft}
      onChange={(event) => {
        setDraft(event.target.value);
        onValueChange?.(event.target.value);
      }}
      onBlur={() => draft.trim() && onCommit(draft)}
      onKeyDown={(event) => {
        if (event.key === "Enter") event.currentTarget.blur();
      }}
      disabled={readOnly}
      placeholder={placeholder}
      className={classes}
    />
  );
}

export default function QuizQuestionCard({
  index,
  questionId,
  questionText,
  questionType,
  options,
  statements,
  correctAnswer,
  explanations,
  selectedOptionId,
  onSelectOption,
  onChangeAnswer,
  mode,
  points,
  awardedPoints,
  isCorrect,
  aiFeedback,
  hint,
  isSaving = false,
  readOnly = false,
  allowAnswerChanges = false,
  markStatus,
  onExplain,
}: QuestionProps) {
  const [showHint, setShowHint] = useState(false);
  const [hintDirection, setHintDirection] = useState<"up" | "down">("down");
  const [isExplaining, setIsExplaining] = useState(false);
  const hintButtonRef = useRef<HTMLButtonElement>(null);
  const hintContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showHint) return;
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!hintContainerRef.current?.contains(event.target as Node)) {
        setShowHint(false);
      }
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => document.removeEventListener("pointerdown", closeOnOutsideClick);
  }, [showHint]);
  const selectedValues = Array.isArray(selectedOptionId) ? selectedOptionId : [];
  const hasResult =
    correctAnswer !== undefined &&
    correctAnswer !== null &&
    (awardedPoints !== undefined && awardedPoints !== null ||
      isCorrect !== undefined && isCorrect !== null ||
      readOnly);
  const isTextQuestion = ["fill_blank", "short_answer", "essay"].includes(questionType);
  const isAnswered = isTextQuestion
    ? String(selectedOptionId ?? "").trim().length > 0
    : questionType === "true_false"
      ? Boolean(statements?.length) && statements!.every((_, i) => typeof selectedValues[i] === "boolean")
      : questionType === "multiple_response"
        ? selectedValues.length > 0
        : selectedOptionId !== undefined && selectedOptionId !== null;
  const isGroupedQuestion = ["multiple_response", "true_false"].includes(questionType);
  const controlsDisabled =
    readOnly ||
    isSaving ||
    (mode === "study" && isGroupedQuestion && hasResult) ||
    (!allowAnswerChanges && isAnswered);

  const renderChoiceOptions = () => (
    <div
      className="mt-5 grid gap-2.5"
      role={questionType === "multiple_response" ? "group" : "radiogroup"}
      aria-label={`Question ${index + 1}`}
    >
      {options?.map((option) => {
        const isMultiple = questionType === "multiple_response";
        const isSelected = isMultiple
          ? selectedValues.some((value) => matchesOption(value, option))
          : matchesOption(selectedOptionId, option);
        const isCorrect = Array.isArray(correctAnswer)
          ? correctAnswer.some((answer) => matchesOption(answer, option))
          : matchesOption(correctAnswer, option);
        let style = "border-border bg-background hover:border-primary/50 hover:bg-primary/5";
        let marker = "border-border text-muted-foreground";
        if (hasResult && isSelected && isCorrect) {
          style = "border-chart-2/50 bg-chart-2/10";
          marker = "border-chart-2 bg-chart-2 text-white";
        } else if (hasResult && isSelected) {
          style = "border-chart-5/50 bg-chart-5/10";
          marker = "border-chart-5 bg-chart-5 text-white";
        } else if (hasResult && isCorrect) {
          if (questionType === "multiple_response") {
            marker = "border-chart-2 text-chart-2";
          } else {
            style = "border-chart-2/50 bg-chart-2/10";
            marker = "border-chart-2 bg-chart-2 text-white";
          }
        } else if (isSelected) {
          style = "border-primary/50 bg-primary/10";
          marker = "border-primary bg-primary text-primary-foreground";
        }
        const inlineExplanation =
          hasResult && (isCorrect || isSelected)
            ? getOptionExplanation(explanations, option)
            : null;

        return (
          <button
            key={option.id}
            type="button"
            role={isMultiple ? "checkbox" : "radio"}
            aria-checked={isSelected}
            disabled={controlsDisabled}
            onClick={() => {
              if (!isMultiple) return onSelectOption(option.id);
              (onChangeAnswer ?? onSelectOption)(
                isSelected
                  ? selectedValues.filter((value) => !matchesOption(value, option))
                  : [...selectedValues, option.id]
              );
            }}
            className={`min-h-12 rounded-[10px] border px-4 py-3 text-left text-sm leading-6 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:cursor-default disabled:opacity-100 ${style}`}
          >
            <span className="flex items-center gap-3">
              <span className={`flex h-5 w-5 shrink-0 items-center justify-center border text-[11px] ${isMultiple ? "rounded" : "rounded-full"} ${marker}`}>
                {hasResult && (isSelected || isCorrect) ? (
                  <Icon name={hasResult && isSelected && !isCorrect ? "close" : "check"} className="text-sm" />
                ) : isSelected ? (
                  <span className={`${isMultiple ? "h-2.5 w-2.5 rounded-sm" : "h-1.5 w-1.5 rounded-full"} bg-current`} />
                ) : null}
              </span>
              <span>{option.option_text}</span>
            </span>
            {inlineExplanation && (
              <span className="mt-3 block border-t border-border/60 pt-3 text-xs leading-5">
                {inlineExplanation}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );

  const renderTrueFalse = () => (
    statements?.length === 1 ? (
      <div className="mt-5 rounded-[10px] border border-border bg-background px-4 py-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-sm leading-6">{statements[0].text}</p>
            {hasResult && statements[0].explanation && (
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                {statements[0].explanation}
              </p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-6" role="radiogroup" aria-label={statements[0].text}>
            {[true, false].map((value) => {
              const selected = selectedValues[0] === value;
              const correct = statements[0].correct_answer ?? (Array.isArray(correctAnswer) ? correctAnswer[0] : undefined);
              const correctChoice = hasResult && correct === value;
              return (
                <button
                  key={String(value)}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  disabled={readOnly || isSaving || (mode === "study" && hasResult)}
                  onClick={() => (onChangeAnswer ?? onSelectOption)([value])}
                  className={`inline-flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                    correctChoice
                      ? "bg-chart-2/10 text-chart-2"
                      : selected && hasResult
                        ? "bg-chart-5/10 text-chart-5"
                        : "text-foreground"
                  }`}
                >
                  <span className={`flex h-5 w-5 items-center justify-center rounded-full border ${
                    selected ? "border-primary bg-primary text-primary-foreground" : "border-border"
                  }`}>
                    {hasResult && (selected || correctChoice) ? (
                      <Icon name={selected && hasResult && !correctChoice ? "close" : "check"} className="text-sm" />
                    ) : selected ? <span className="h-1.5 w-1.5 rounded-full bg-current" /> : null}
                  </span>
                  {value ? "True" : "False"}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    ) : (
    <div className="mt-5 overflow-x-auto rounded-[10px] border border-border">
      <table className="w-full min-w-[520px] border-collapse text-sm">
        <thead className="bg-muted/50 text-xs text-muted-foreground">
          <tr><th className="px-4 py-3 text-left font-medium">Statement</th><th className="w-20 text-center font-medium">True</th><th className="w-20 text-center font-medium">False</th></tr>
        </thead>
        <tbody>
          {statements?.map((statement, statementIndex) => {
            const selected = selectedValues[statementIndex];
            const correct = statement.correct_answer ?? (Array.isArray(correctAnswer) ? correctAnswer[statementIndex] : undefined);
            return (
              <tr key={`${questionId}-${statementIndex}`} className="border-t border-border align-middle">
                <td className="px-4 py-3 leading-6">
                  <span>{statement.text}</span>
                  {hasResult && statement.explanation && (
                    <p className="mt-1 text-xs text-muted-foreground">{statement.explanation}</p>
                  )}
                </td>
                {[true, false].map((value) => {
                  const chosen = selected === value;
                  const correctCell = hasResult && correct === value;
                  return (
                    <td key={String(value)} className={`px-2 py-3 text-center ${correctCell ? "bg-chart-2/10" : chosen && hasResult ? "bg-chart-5/10" : ""}`}>
                      <button
                        type="button"
                        role="radio"
                        aria-label={`${statement.text}: ${value ? "True" : "False"}`}
                        aria-checked={chosen}
                        disabled={readOnly || isSaving || (mode === "study" && hasResult)}
                        onClick={() => {
                          const next = [...selectedValues];
                          next[statementIndex] = value;
                          (onChangeAnswer ?? onSelectOption)(next);
                        }}
                        className={`mx-auto flex h-6 w-6 items-center justify-center rounded-full border ${chosen ? "border-primary bg-primary text-primary-foreground" : "border-border"}`}
                      >
                        {hasResult && (chosen || correctCell) ? (
                          <Icon name={chosen && !correctCell ? "close" : "check"} className="text-sm" />
                        ) : chosen ? <span className="h-1.5 w-1.5 rounded-full bg-current" /> : null}
                      </button>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
    )
  );

  const blankParts = questionText.split(/\[blank\]/i);

  return (
    <article data-question-id={questionId} className="rounded-xl border border-border/80 bg-card p-5 shadow-xs sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-medium text-muted-foreground">
            <span className="rounded-full bg-primary/10 px-2.5 py-1 text-primary">Question {index + 1}</span>
            {points !== undefined && (
              awardedPoints !== undefined && awardedPoints !== null ? (
                awardedPoints === points ? (
                  <span className="text-chart-2">{formatPointValue(awardedPoints)}/{formatPointValue(points)} points</span>
                ) : (
                  <span>
                    <span className="text-destructive">{formatPointValue(awardedPoints)}</span>
                    <span className="text-chart-2">/{formatPointValue(points)} points</span>
                  </span>
                )
              ) : (
                <span>{formatPointValue(points)} points</span>
              )
            )}
            {markStatus && <span className="rounded-full bg-muted px-2 py-0.5 capitalize">{markStatus}</span>}
            {isSaving && <span className="inline-flex items-center gap-1"><Icon name="progress_activity" className="animate-spin text-sm" />Grading answer</span>}
          </div>
          {questionType !== "fill_blank" && <h2 className="mt-3 text-base font-medium leading-7">{questionText}</h2>}
        </div>
        {hint && (
          <div ref={hintContainerRef} className="relative shrink-0">
            <button
              ref={hintButtonRef}
              type="button"
              onClick={() => {
                if (!showHint) {
                  const rect = hintButtonRef.current?.getBoundingClientRect();
                  if (rect) {
                    const below = window.innerHeight - rect.bottom;
                    setHintDirection(below < 190 && rect.top > below ? "up" : "down");
                  }
                }
                setShowHint((value) => !value);
              }}
              aria-label={showHint ? "Hide hint" : "Show hint"}
              aria-expanded={showHint}
              className={`flex h-9 w-9 items-center justify-center rounded-full border transition-[color,background-color,border-color,transform] duration-200 hover:border-amber-300 hover:bg-amber-50 hover:text-amber-600 active:scale-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/40 ${
                showHint
                  ? "border-amber-300 bg-amber-50 text-amber-600"
                  : "border-border bg-background text-muted-foreground"
              }`}
            >
              <Icon name="lightbulb" className="text-lg" />
            </button>
            {showHint && (
              <div
                className={`absolute right-0 z-30 w-72 rounded-[10px] border border-amber-200 bg-popover p-4 text-xs leading-5 shadow-lg animate-in fade-in zoom-in-95 ${
                  hintDirection === "up"
                    ? "bottom-11 slide-in-from-bottom-1"
                    : "top-11 slide-in-from-top-1"
                }`}
              >
                <div className="mb-2 flex items-center gap-1.5 font-medium text-amber-600">
                  <Icon name="lightbulb" className="text-base" />
                  Hint
                </div>
                {hint}
              </div>
            )}
          </div>
        )}
      </div>

      {["multiple_choice", "multiple_response"].includes(questionType) && renderChoiceOptions()}
      {questionType === "true_false" && renderTrueFalse()}
      {mode === "study" && ["multiple_response", "true_false"].includes(questionType) && !readOnly && (
        <button
          type="button"
          disabled={hasResult || isSaving}
          onClick={() => onSelectOption(selectedOptionId ?? [])}
          className="mt-4 inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-transform active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100"
        >
          Check answer
        </button>
      )}
      {questionType === "fill_blank" && (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-base leading-8">
          <span>{blankParts[0]}</span>
          <span className="min-w-48 flex-1"><TextAnswer value={selectedOptionId} multiline={false} readOnly={readOnly || isSaving} placeholder="Type the missing text" onCommit={onSelectOption} onValueChange={mode === "exam" ? onChangeAnswer as ((value: string) => void) | undefined : undefined} /></span>
          <span>{blankParts.slice(1).join("[blank]")}</span>
        </div>
      )}
      {questionType === "short_answer" && <div className="mt-5"><TextAnswer value={selectedOptionId} multiline={false} readOnly={readOnly || isSaving} placeholder="Type your answer" onCommit={onSelectOption} onValueChange={mode === "exam" ? onChangeAnswer as ((value: string) => void) | undefined : undefined} /></div>}
      {questionType === "essay" && <div className="mt-5"><TextAnswer value={selectedOptionId} multiline readOnly={readOnly || isSaving || hasResult} placeholder={isVietnameseQuestion(questionText) ? "Nhập bài làm của bạn" : "Write your answer"} submitLabel={mode === "study" ? (isVietnameseQuestion(questionText) ? "Nộp bài" : "Submit answer") : undefined} onValueChange={mode === "exam" ? onChangeAnswer as ((value: string) => void) | undefined : undefined} onCommit={onSelectOption} /></div>}

      {isAnswered && hasResult && isTextQuestion && (
        <div className="mt-4 rounded-[8px] border border-border bg-muted/30 p-3 text-xs leading-5">
          {questionType === "essay" ? (
            <><p className="font-medium">{isVietnameseQuestion(questionText) ? "Tiêu chí chấm" : "Rubric"}</p><ul className="mt-1 list-disc space-y-1 pl-5">{(Array.isArray(correctAnswer) ? correctAnswer : []).map((point) => <li key={String(point)}>{String(point)}</li>)}</ul></>
          ) : <p><span className="font-medium">Accepted answer: </span>{Array.isArray(correctAnswer) ? correctAnswer.join(" / ") : String(correctAnswer)}</p>}
          {aiFeedback && <p className="mt-2 border-t border-border pt-2">{aiFeedback}</p>}
          {typeof explanations === "object" && explanations !== null && (explanations as Record<string, string>).general && <p className="mt-2">{(explanations as Record<string, string>).general}</p>}
        </div>
      )}

      {onExplain && <footer className="mt-5 border-t border-border/70 pt-4"><button type="button" disabled={isExplaining} onClick={async () => { setIsExplaining(true); try { await onExplain(); } finally { setIsExplaining(false); } }} className="inline-flex items-center gap-1.5 rounded-[8px] border border-border px-3 py-2 text-xs font-medium text-muted-foreground transition-[color,background-color,border-color,transform] hover:border-primary/40 hover:bg-primary/5 hover:text-primary active:scale-95 disabled:cursor-wait disabled:opacity-70 disabled:active:scale-100"><Icon name="forum" className="text-base" />{isExplaining && <Icon name="progress_activity" className="animate-spin text-sm" />}Explain</button></footer>}
    </article>
  );
}
