/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the FastAPI backend. Local dev falls back to
   * http://127.0.0.1:8000 if this isn't set (see api/client.ts). Set
   * at build time for CLOUD MODE - a public value, never a secret. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
