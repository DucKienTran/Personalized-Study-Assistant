export function AuthBackgroundPattern() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className="absolute -left-24 top-24 h-72 w-72 rounded-full border border-primary-foreground/10" />
      <div className="absolute -left-8 top-40 h-72 w-72 rounded-full border border-primary-foreground/10" />
      <div className="absolute bottom-20 right-[-7rem] h-80 w-80 rounded-full bg-primary-foreground/5" />
      <div className="absolute right-16 top-0 h-32 w-px bg-primary-foreground/10" />
      <div className="absolute right-12 top-32 h-1 w-9 bg-accent" />
    </div>
  );
}
