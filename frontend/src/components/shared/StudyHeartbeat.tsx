"use client";

import { useStudyHeartbeat } from "@/hooks/useStudyHeartbeat";

export function StudyHeartbeat() {
  useStudyHeartbeat(true);
  return null;
}
