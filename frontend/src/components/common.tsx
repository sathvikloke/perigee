import { useEffect, useState } from "react";
import { ApiError, isAbortError } from "../api/client";

export function errorInfo(err: unknown): { code: string; message: string; retryable: boolean } {
  if (err instanceof ApiError) return { code: err.code, message: err.message, retryable: err.retryable };
  return { code: "UNEXPECTED", message: err instanceof Error ? err.message : String(err), retryable: true };
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
        {info.message} <span className="mono muted">({info.code})</span>
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
