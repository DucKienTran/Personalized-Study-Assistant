import { APP_CONFIG } from "@/constants/app";
import { AutoStoriesIcon } from "@/components/shared/icons";
import { AuthBackgroundPattern } from "@/components/auth/AuthBackgroundPattern";

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-background lg:grid lg:grid-cols-[minmax(22rem,0.85fr)_minmax(32rem,1.15fr)]">
      <aside className="relative hidden min-h-screen overflow-hidden bg-primary px-12 py-10 text-primary-foreground lg:flex lg:flex-col lg:justify-between xl:px-16 xl:py-14">
        <AuthBackgroundPattern />

        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-primary-foreground/15 bg-primary-foreground/10">
            <AutoStoriesIcon size={24} />
          </div>
          <span className="font-heading text-xl font-medium tracking-tight">
            {APP_CONFIG.NAME}
          </span>
        </div>

        <div className="relative z-10 max-w-md space-y-7">
          <div className="h-1 w-12 bg-accent" />
          <h1 className="font-heading text-4xl leading-tight font-medium text-balance xl:text-5xl">
            A quieter place to think, learn, and remember.
          </h1>
          <p className="max-w-sm text-sm leading-7 text-primary-foreground/70">
            Bring your notes, questions, and study rituals together in one
            thoughtful learning space.
          </p>
        </div>

        <p className="relative z-10 text-xs font-medium tracking-[0.2em] text-primary-foreground/55 uppercase">
          Read / Question / Remember
        </p>
      </aside>

      <section className="relative flex min-h-screen items-center justify-center overflow-y-auto px-5 py-8 sm:px-10 sm:py-12 lg:px-14 xl:px-20">
        <div className="absolute inset-x-0 top-0 h-1 bg-accent lg:hidden" />
        <div className="w-full max-w-lg">
          <div className="mb-8 flex items-center justify-center gap-2.5 text-primary lg:hidden">
            <AutoStoriesIcon size={24} />
            <span className="font-heading text-xl font-medium tracking-tight">
              {APP_CONFIG.NAME}
            </span>
          </div>
          {children}
        </div>
      </section>
    </main>
  );
}
