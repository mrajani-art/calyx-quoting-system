export class QuoteError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "QuoteError";
    this.status = status;
  }
}

export function getUserFriendlyError(err: unknown): string {
  if (err instanceof QuoteError) {
    switch (true) {
      case err.status === 422:
        return "Some configuration options appear invalid. Please review your selections and try again.";
      case err.status === 429:
        return "Too many requests. Please wait a moment and try again.";
      case err.status >= 500:
        return "Our pricing service is temporarily unavailable. Please try again in a few minutes.";
      default:
        return err.message || "Something went wrong. Please try again.";
    }
  }
  if (err instanceof TypeError && err.message.includes("fetch")) {
    return "Unable to connect. Please check your internet connection and try again.";
  }
  return "Something went wrong. Please try again.";
}
