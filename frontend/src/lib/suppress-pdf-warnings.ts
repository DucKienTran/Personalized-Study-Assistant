const SUPPRESSOR_KEY = "__learningAidPdfWarningSuppressorInstalled";

type SuppressorWindow = Window & {
  [SUPPRESSOR_KEY]?: boolean;
};

if (typeof window !== "undefined") {
  const suppressorWindow = window as SuppressorWindow;

  if (!suppressorWindow[SUPPRESSOR_KEY]) {
    suppressorWindow[SUPPRESSOR_KEY] = true;

    const isTargetError = (args: unknown[]): boolean =>
      args.some((argument) => {
        if (!argument) return false;
        const candidate = argument as { message?: string; stack?: string };
        const value =
          typeof argument === "string"
            ? argument
            : candidate.message || candidate.stack || String(argument);
        return (
          value.includes("AbortException") ||
          value.includes("TextLayer task cancelled") ||
          value.includes("TextLayer.useCallback[onRenderError]")
        );
      });

    const originalConsoleError = console.error;
    console.error = (...args: unknown[]) => {
      if (isTargetError(args)) return;
      originalConsoleError.apply(console, args);
    };

    const originalConsoleWarn = console.warn;
    console.warn = (...args: unknown[]) => {
      if (isTargetError(args)) return;
      originalConsoleWarn.apply(console, args);
    };

    window.addEventListener(
      "unhandledrejection",
      (event: PromiseRejectionEvent) => {
        const reason = event.reason as { name?: string; message?: string } | null;
        if (
          reason?.name === "AbortException" ||
          reason?.message?.includes("TextLayer task cancelled") ||
          reason?.message?.includes("cancelled")
        ) {
          event.stopImmediatePropagation();
          event.preventDefault();
        }
      },
      true
    );
  }
}
