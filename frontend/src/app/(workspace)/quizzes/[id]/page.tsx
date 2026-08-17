"use client";

import { use } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import QuizRunner from "@/components/quizzes/QuizRunner";

interface Props {
  params: Promise<{ id: string }>;
}

export default function QuizDoingPage({ params }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { id } = use(params);
  const quizId = Number(id);
  const notebookId = Number(searchParams.get("notebookId"));
  const returnPath = Number.isFinite(notebookId) && notebookId > 0
    ? `/notebooks/${notebookId}?tab=quizzes`
    : "/quizzes";

  return (
    <QuizRunner
      quizId={quizId}
      onBack={() => router.push(returnPath)}
    />
  );
}
