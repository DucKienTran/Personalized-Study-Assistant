import api from "./api";

interface ApiResponse<T> {
  status: string;
  message?: string;
  data: T;
}

export type FlashcardRating = "again" | "hard" | "good" | "easy";
export type FlashcardLearningState = "new" | "learning" | "review" | "relearning";
export type FlashcardGenerationStatus = "manual" | "processing" | "completed" | "failed";
export type FlashcardSessionStatus = "active" | "completed" | "abandoned";

export interface FlashcardItem {
  id: number;
  deck_id: number;
  front: string;
  back: string;
  source_document_id?: number | null;
  source_chunk_id?: string | null;
  source_metadata?: Record<string, unknown> | null;
  position: number;
  is_suspended: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface FlashcardDeckItem {
  id: number;
  notebook_id: number;
  user_id: number;
  title: string;
  description?: string | null;
  generation_status: FlashcardGenerationStatus;
  source_document_ids: number[];
  card_count: number;
  suspended_card_count: number;
  created_at: string;
  updated_at?: string | null;
  error_message?: string | null;
}

export interface FlashcardDeckDetail extends FlashcardDeckItem {
  cards: FlashcardItem[];
}

export interface FlashcardNotebookAnalytics {
  notebook_id: number;
  deck_count: number;
  card_count: number;
  total_reviews: number;
  rating_counts: Record<FlashcardRating, number>;
  success_rate: number;
  total_review_time_ms: number;
  average_review_time_ms: number;
}

export interface CreateDeckPayload {
  notebook_id: number;
  title: string;
  description?: string | null;
}

export interface UpdateDeckPayload {
  title?: string;
  description?: string | null;
}

export interface CreateFlashcardPayload {
  front: string;
  back: string;
  source_document_id?: number | null;
  source_chunk_id?: string | null;
  source_metadata?: Record<string, unknown> | null;
  position?: number | null;
}

export interface UpdateFlashcardPayload {
  front?: string;
  back?: string;
  position?: number | null;
}

export interface GenerateFlashcardsPayload {
  notebook_id: number;
  title: string;
  description?: string | null;
  total_cards: number;
  custom_instruction?: string | null;
}

export interface FlashcardStudyOverview {
  deck_id: number;
  total_cards: number;
  new_count: number;
  learning_count: number;
  review_due_count: number;
  relearning_count: number;
  suspended_count: number;
  due_now_count: number;
}

export interface FlashcardSessionCard {
  card_id: number;
  queue_type: FlashcardLearningState;
  queue_position: number;
  available_at: string;
  review_count: number;
  completed: boolean;
  card: FlashcardItem;
}

export interface FlashcardStudySession {
  id: number;
  deck_id: number;
  user_id: number;
  status: FlashcardSessionStatus;
  started_at: string;
  completed_at?: string | null;
  new_cards_count: number;
  review_cards_count: number;
  reviewed_count: number;
  current_card?: FlashcardSessionCard | null;
  remaining_new: number;
  remaining_learning: number;
  remaining_review: number;
  remaining_relearning: number;
  next_available_at?: string | null;
}

export interface FlashcardReviewResult {
  reviewed_card_id: number;
  rating: FlashcardRating;
  state_before: FlashcardLearningState;
  state_after: FlashcardLearningState;
  next_due?: string | null;
  current_card?: FlashcardSessionCard | null;
  next_available_at?: string | null;
  remaining_new: number;
  remaining_learning: number;
  remaining_review: number;
  remaining_relearning: number;
  session_completed: boolean;
}

export const flashcardService = {
  async listDecks(notebookId?: number) {
    const res = await api.get<ApiResponse<FlashcardDeckItem[]>>(
      "/flashcard-decks",
      {
        params:
          notebookId === undefined ? undefined : { notebook_id: notebookId },
      }
    );
    return res.data.data;
  },

  async getNotebookAnalytics(notebookId: number) {
    const res = await api.get<ApiResponse<FlashcardNotebookAnalytics>>(
      `/flashcard-decks/notebooks/${notebookId}/analytics`
    );
    return res.data.data;
  },

  async getDeck(deckId: number) {
    const res = await api.get<ApiResponse<FlashcardDeckDetail>>(
      `/flashcard-decks/${deckId}`
    );
    return res.data.data;
  },

  async createDeck(payload: CreateDeckPayload) {
    const res = await api.post<ApiResponse<FlashcardDeckItem>>(
      "/flashcard-decks",
      payload
    );
    return res.data.data;
  },

  async updateDeck(deckId: number, payload: UpdateDeckPayload) {
    const res = await api.patch<ApiResponse<FlashcardDeckItem>>(
      `/flashcard-decks/${deckId}`,
      payload
    );
    return res.data.data;
  },

  async deleteDeck(deckId: number) {
    await api.delete<ApiResponse<null>>(`/flashcard-decks/${deckId}`);
  },

  async createCard(deckId: number, payload: CreateFlashcardPayload) {
    const res = await api.post<ApiResponse<FlashcardItem>>(
      `/flashcard-decks/${deckId}/cards`,
      payload
    );
    return res.data.data;
  },

  async updateCard(cardId: number, payload: UpdateFlashcardPayload) {
    const res = await api.patch<ApiResponse<FlashcardItem>>(
      `/flashcards/${cardId}`,
      payload
    );
    return res.data.data;
  },

  async deleteCard(cardId: number) {
    await api.delete<ApiResponse<null>>(`/flashcards/${cardId}`);
  },

  async suspendCard(cardId: number) {
    const res = await api.post<ApiResponse<FlashcardItem>>(
      `/flashcards/${cardId}/suspend`
    );
    return res.data.data;
  },

  async unsuspendCard(cardId: number) {
    const res = await api.post<ApiResponse<FlashcardItem>>(
      `/flashcards/${cardId}/unsuspend`
    );
    return res.data.data;
  },

  async getStudyOverview(deckId: number) {
    const res = await api.get<ApiResponse<FlashcardStudyOverview>>(
      `/flashcard-decks/${deckId}/study-overview`
    );
    return res.data.data;
  },

  async startSession(
    deckId: number,
    payload: {
      new_card_limit?: number | null;
      review_card_limit?: number | null;
    } = {}
  ) {
    const res = await api.post<ApiResponse<FlashcardStudySession>>(
      `/flashcard-decks/${deckId}/sessions`,
      payload
    );
    return res.data.data;
  },

  async getSession(sessionId: number) {
    const res = await api.get<ApiResponse<FlashcardStudySession>>(
      `/flashcard-sessions/${sessionId}`
    );
    return res.data.data;
  },

  async review(
    sessionId: number,
    payload: {
      card_id: number;
      rating: FlashcardRating;
      response_time_ms?: number | null;
    }
  ) {
    const res = await api.post<ApiResponse<FlashcardReviewResult>>(
      `/flashcard-sessions/${sessionId}/review`,
      payload
    );
    return res.data.data;
  },

  async completeSession(sessionId: number) {
    const res = await api.post<ApiResponse<FlashcardStudySession>>(
      `/flashcard-sessions/${sessionId}/complete`
    );
    return res.data.data;
  },

  async abandonSession(sessionId: number) {
    const res = await api.post<ApiResponse<FlashcardStudySession>>(
      `/flashcard-sessions/${sessionId}/abandon`
    );
    return res.data.data;
  },

  async generate(payload: GenerateFlashcardsPayload) {
    const res = await api.post<ApiResponse<FlashcardDeckItem>>(
      "/flashcard-decks/generate",
      payload
    );
    return res.data.data;
  },

  async listProcessing() {
    const res = await api.get<ApiResponse<FlashcardDeckItem[]>>(
      "/flashcard-decks/processing"
    );
    return res.data.data;
  },
};
