"use client";

import { use, useCallback, useState } from "react";
import { useRouter } from "next/navigation";

import QuizRunner from "@/components/quizzes/QuizRunner";

interface Props {
  params: Promise<{ id: string }>;
}

export default function QuizDoingPage({ params }: Props) {
  const router = useRouter();
  const { id } = use(params);
  const quizId = Number(id);
  const [notebookId, setNotebookId] = useState<number | null>(null);
  const handleBackToList = useCallback(() => {
    if (notebookId !== null) {
      router.push(`/notebooks/${notebookId}?tab=quizzes`);
    }
  }, [notebookId, router]);

  return (
    <QuizRunner
      quizId={quizId}
      onBack={handleBackToList}
      onNotebookIdResolved={setNotebookId}
    />
  );
}
