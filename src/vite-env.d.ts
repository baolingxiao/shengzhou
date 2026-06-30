/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

declare const __APP_VERSION__: string

interface ImportMetaEnv {
  readonly VITE_APP_CHANNEL: string
  readonly VITE_ENABLE_REALTIME_VOICE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
