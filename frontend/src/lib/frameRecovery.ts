import { ApiError, isAbortError } from "../api/client";

const RETRY_DELAYS = [900, 2200];

function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(new DOMException("Aborted", "AbortError"));
    const abort = () => { clearTimeout(timer); reject(new DOMException("Aborted", "AbortError")); };
    const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, ms);
    signal.addEventListener("abort", abort, { once: true });
  });
}

/** Only transient network/upstream failures retry; release the concurrency slot between attempts. */
export async function recoverFrame<T>(operation: () => Promise<T>, signal: AbortSignal, onRetry: (attempt: number) => void): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    try {
      const value = await operation();
      if (signal.aborted) throw new DOMException("Aborted", "AbortError");
      return value;
    }
    catch (error) {
      if (signal.aborted) throw new DOMException("Aborted", "AbortError");
      if (isAbortError(error) || !(error instanceof ApiError) || !error.retryable ||
          ["TOKEN_EXPIRED", "INVALID_TOKEN", "INVALID_FRAME_TOKEN", "PROCESSING_FAILED", "UNSUPPORTED_DATA"].includes(error.code) || attempt >= RETRY_DELAYS.length) throw error;
      onRetry(attempt + 1);
      await wait(RETRY_DELAYS[attempt] + Math.floor(Math.random() * 200), signal);
    }
  }
}
