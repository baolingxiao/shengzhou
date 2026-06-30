/** OpenAI Realtime Voice Chat 功能开关（Vite 环境变量） */
export const REALTIME_VOICE_ENABLED =
  import.meta.env.VITE_ENABLE_REALTIME_VOICE === 'true'

/** 浏览器直连 OpenAI Realtime WebRTC（GA） */
export const OPENAI_REALTIME_CALLS_URL =
  'https://api.openai.com/v1/realtime/calls'
