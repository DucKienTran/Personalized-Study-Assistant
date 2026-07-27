"use client";

import { useCallback, useEffect, useState } from "react";
import { chatService } from "@/services/chat.service";
import { ConversationSummary } from "@/types/chat";

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const list = await chatService.listConversations();
      setConversations(list);
    } catch {
      // sidebar list failing shouldn't block the chat itself
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const rename = useCallback(
    async (id: number, title: string) => {
        await chatService.renameConversation(id, title);
        await refresh();
    },
    [refresh]
    );

    const remove = useCallback(
    async (id: number) => {
        await chatService.deleteConversation(id);
        await refresh();
    },
    [refresh]
    );

    return { conversations, isLoading, refresh, rename, remove };
}