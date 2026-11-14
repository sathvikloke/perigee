/// <reference types="vite/client" />

declare const __APP_VERSION__: string;

interface ImportMetaEnv {
  /** Optional public API origin for a split deployment. Not a secret. */
  readonly VITE_API_BASE?: string;
  /** "1" starts the app in development-fixture mode. */
  readonly VITE_USE_FIXTURES?: string;
}
