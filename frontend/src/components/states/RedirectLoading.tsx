import { ProgressActivityIcon } from "@/components/shared/icons";
import { AuthShell } from "@/components/auth/AuthShell";
import { Card, CardContent } from "@/components/ui/card";

export default function RedirectLoading({
  message = "Processing... please wait a moment.",
}: {
  message?: string;
}) {
  return (
    <AuthShell>
      <Card className="border border-border bg-card text-center shadow-[0_24px_70px_-38px_var(--primary-shadow)] ring-0">
        <CardContent className="flex select-none flex-col items-center gap-5 py-8">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <ProgressActivityIcon
              size={28}
              className="animate-spin text-primary"
              style={{ animationDuration: "1.4s" }}
            />
          </div>
          <p className="text-sm font-medium text-muted-foreground">{message}</p>
        </CardContent>
      </Card>
    </AuthShell>
  );
}
