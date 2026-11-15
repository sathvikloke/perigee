import { useEffect, useState } from "react";
import { ApiError, isAbortError } from "../api/client";
import { formatElapsed } from "../lib/requestState";

export function errorInfo(err: unknown): { code: string; message: string; retryable: boolean } {
  if (err instanceof ApiError) return { code: err.code, message: err.message, retryable: err.retryable };
  return { code: "UNEXPECTED", message: err instanceof Error ? err.message : String(err), retryable: true };
}

export function friendlyError(code: string): string {
  if (code === "TOKEN_EXPIRED" || code === "INVALID_TOKEN" || code === "INVALID_FRAME_TOKEN") return "This search has expired. Run it again; your notes are kept.";
  if (code === "PRESET_NOT_FOUND") return "This investigation is unavailable. Choose another from the home page.";
  if (code === "PROCESSING_FAILED") return "This observation could not be processed. Other images may still be usable.";
  if (code === "SUPERSEDED") return "Loading stopped when a newer search started. You can load this image again.";
  if (code === "NETWORK_ERROR") return "The connection was interrupted. Check your connection and try again.";
  if (code === "UPSTREAM_UNAVAILABLE" || code === "UPSTREAM_TIMEOUT") return "The data service couldn’t respond right now. Try again; your notes are kept.";
  return "The request could not be completed right now. Please try again; your notes are kept.";
}

export function ErrorBlock(props: {
  title: string;
  error: unknown;
  onRetry?: () => void;
  onUseFixture?: () => void;
}) {
  const info = errorInfo(props.error);
  return (
    <div className="error-block" role="alert">
      <p>
        <strong>{props.title}</strong>
      </p>
      <p>
        {friendlyError(info.code)}
      </p>
      <div className="actions">
        {props.onRetry && (
          <button type="button" onClick={props.onRetry}>
            Try again
          </button>
        )}
        {props.onUseFixture && (
          <button type="button" onClick={props.onUseFixture}>
            Use development fixture (not NASA data)
          </button>
        )}
      </div>
    </div>
  );
}

/** The current time, refreshed every second while `active`. */
export function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [active]);
  return now;
}

/** Elapsed time since `since` (epoch ms), ticking once a second. Not a live region. */
export function Elapsed({ since }: { since: number }) {
  const now = useNow(true);
  return <span className="counter">{formatElapsed(now - since)}</span>;
}

export type AsyncState<T> =
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "error"; error: unknown };

/** Loads `fn` whenever `deps` change; aborts the previous call; ignores stale results. */
export function useAsync<T>(fn: (signal: AbortSignal) => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });
  const [nonce, setNonce] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let live = true;
    setState({ status: "loading" });
    fn(controller.signal).then(
      (data) => live && setState({ status: "ready", data }),
      (error) => {
        if (live && !isAbortError(error)) setState({ status: "error", error });
      },
    );
    return () => {
      live = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);
  return { state, retry: () => setNonce((n) => n + 1) };
}
