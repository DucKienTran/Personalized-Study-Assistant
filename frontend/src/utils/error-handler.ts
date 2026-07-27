interface ValidationErrorItem {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

interface ApiErrorResponse {
  response?: {
    status?: number;
    data?: {
      detail?: string | ValidationErrorItem[];
    };
  };
}

/**
 * Parses unknown error objects and extracts user-friendly message strings.
 * Respects FastAPI 422 detail arrays with field-level prefix context.
 */
export function parseApiError(
  err: unknown,
  fallbackMessage: string = "An unexpected error occurred. Please try again."
): string {
  if (typeof err !== "object" || err === null) {
    return fallbackMessage;
  }

  const apiErr = err as ApiErrorResponse;

  if (!apiErr.response) {
    return "Network error. Please check your internet connection.";
  }

  const detail = apiErr.response.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const firstErr = detail[0];
    if (firstErr?.msg) {
      const fieldName = firstErr.loc?.[1] ? `${firstErr.loc[1]}: ` : "";
      return `${fieldName}${firstErr.msg}`;
    }
  }

  switch (apiErr.response.status) {
    case 401:
      return "Invalid email or password.";
    case 422:
      return "Validation failed. Please check your inputs.";
    case 429:
      return "Too many requests. Please try again later.";
    case 500:
      return "Internal server error. Please try again later.";
    default:
      return fallbackMessage;
  }
}