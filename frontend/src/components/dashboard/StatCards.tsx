// components/dashboard/StatCards.tsx
import { Icon } from "@/components/shared/icons";

interface StatsProps {
  stats: {
    notebook_count: number;
    document_count: number;
    message_count: number;
    quiz_count: number;
  };
}

export function StatCards({ stats }: StatsProps) {
  const items = [
    { label: "Notebooks", value: stats.notebook_count, icon: "auto_stories" },
    { label: "Documents", value: stats.document_count, icon: "description" },
    { label: "Messages", value: stats.message_count, icon: "chat_bubble_outline" },
    { label: "Quizzes", value: stats.quiz_count, icon: "draw" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
      {items.map((item, idx) => (
        <div
          key={idx}
          className="rounded-xl border border-border bg-card p-4 shadow-xs transition-all duration-200 hover:shadow-md lg:p-5"
        >
          <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-xl bg-muted text-base text-foreground lg:mb-4 lg:h-9 lg:w-9 lg:text-lg">
            <Icon name={item.icon} />
          </div>
          <div className="font-heading text-2xl font-bold tracking-tight text-foreground lg:text-3xl">
            {item.value}
          </div>
          <div className="mt-1 text-xs font-medium text-muted-foreground">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
