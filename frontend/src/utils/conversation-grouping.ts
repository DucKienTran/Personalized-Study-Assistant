import { ConversationSummary } from "@/types/chat";

export interface ConversationGroup {
  label: string;
  conversations: ConversationSummary[];
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export function groupConversationsByDate(
  conversations: ConversationSummary[]
): ConversationGroup[] {
  const today = startOfDay(new Date());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const sevenDaysAgo = new Date(today);
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

  const buckets: Record<string, ConversationSummary[]> = {
    "Today": [],
    "Yesterday": [],
    "Last 7 Days": [],
    "Older": [],
  };

  for (const conv of conversations) {
    const updated = startOfDay(new Date(conv.updatedAt));

    if (updated.getTime() === today.getTime()) {
      buckets["Today"].push(conv);
    } else if (updated.getTime() === yesterday.getTime()) {
      buckets["Yesterday"].push(conv);
    } else if (updated.getTime() > sevenDaysAgo.getTime()) {
      buckets["Last 7 Days"].push(conv);
    } else {
      buckets["Older"].push(conv);
    }
  }

  return Object.entries(buckets)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, conversations: items }));
}