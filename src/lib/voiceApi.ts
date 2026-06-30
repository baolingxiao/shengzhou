export type VoiceStatus = {
  stt_available: boolean
  stt_provider: string
  stt_model: string
  stt_reason: string
  tts_available: boolean
  tts_reason: string
  wake_phrases: string[]
  silence_seconds: number
  min_speech_seconds: number
  wake_timeout_seconds: number
  followup_seconds: number
  wake_max_seconds: number
  wake_stt_max_seconds: number
  wake_silence_seconds: number
}

export type SttResult = {
  text: string
  wake_phrase: string | null
  cleaned_text: string
  is_wake_only: boolean
}

export type TtsChunk = {
  index: number
  audio_base64: string
  mime_type: string
}

import { getActiveTraceId, patchClientTrace, traceHeaders } from './executionTrace'

const API_BASE = '/api'

export async function fetchVoiceStatus(): Promise<VoiceStatus> {
  const resp = await fetch(`${API_BASE}/voice/status`)
  if (!resp.ok) {
    throw new Error(`语音服务不可用 (${resp.status})`)
  }
  return resp.json() as Promise<VoiceStatus>
}

export async function transcribeAudio(
  wavBlob: Blob,
  purpose: 'wake' | 'utterance' = 'utterance',
): Promise<SttResult> {
  const form = new FormData()
  form.append('audio', wavBlob, 'utterance.wav')
  form.append('purpose', purpose)
  const resp = await fetch(`${API_BASE}/voice/stt`, {
    method: 'POST',
    body: form,
  })
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = (await resp.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail || `语音识别失败 (${resp.status})`)
  }
  return resp.json() as Promise<SttResult>
}

export async function synthesizeSpeech(text: string, traceId?: string | null): Promise<TtsChunk[]> {
  const resolvedTraceId = traceId ?? getActiveTraceId()
  const resp = await fetch(`${API_BASE}/voice/tts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...traceHeaders(resolvedTraceId),
    },
    body: JSON.stringify({
      text,
      trace_id: resolvedTraceId ?? undefined,
    }),
  })
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = (await resp.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail || `语音合成失败 (${resp.status})`)
  }
  const payload = (await resp.json()) as { chunks: TtsChunk[]; trace_id?: string }
  if (payload.trace_id) {
    console.log('[TRACE]', payload.trace_id, 'tts_ready')
  }
  return payload.chunks ?? []
}

export function playTtsChunks(
  chunks: TtsChunk[],
  traceId?: string | null,
): Promise<void> {
  const resolvedTraceId = traceId ?? getActiveTraceId()
  return new Promise((resolve, reject) => {
    if (!chunks.length) {
      resolve()
      return
    }
    const ordered = [...chunks].sort((a, b) => a.index - b.index)
    let index = 0
    const audio = new Audio()

    const playNext = () => {
      if (index >= ordered.length) {
        if (resolvedTraceId) {
          void patchClientTrace({
            trace_id: resolvedTraceId,
            pipeline: { frontend: { tts_triggered: true } },
          })
        }
        resolve()
        return
      }
      const chunk = ordered[index]
      const chunkIndex = chunk.index
      const playStart = new Date().toISOString()
      index += 1
      audio.src = `data:${chunk.mime_type};base64,${chunk.audio_base64}`
      audio.onloadedmetadata = () => {
        const durationMs = Number.isFinite(audio.duration)
          ? Math.round(audio.duration * 1000)
          : 0
        if (resolvedTraceId) {
          void patchClientTrace({
            trace_id: resolvedTraceId,
            tts: {
              enabled: true,
              chunks: [
                {
                  index: chunkIndex,
                  audio_duration_ms: durationMs,
                  played: false,
                  play_start_at: playStart,
                },
              ],
            },
          })
        }
      }
      audio.onended = () => {
        if (resolvedTraceId) {
          void patchClientTrace({
            trace_id: resolvedTraceId,
            tts: {
              chunks: [
                {
                  index: chunkIndex,
                  played: true,
                  play_end_at: new Date().toISOString(),
                },
              ],
            },
          })
        }
        playNext()
      }
      audio.onerror = () => reject(new Error('TTS 播放失败'))
      void audio.play().catch(reject)
    }

    playNext()
  })
}
