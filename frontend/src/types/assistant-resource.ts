export type AssistantResourceType =
  | "summary"
  | "mindmap"
  | "quiz"
  | "flashcards";

export interface AssistantResource {
  resourceType: AssistantResourceType;
  resourceId: string;
  title: string;
  notebookId: number;
  metadata?: Record<string, unknown>;
}
