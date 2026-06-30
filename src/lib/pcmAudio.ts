const SAMPLE_RATE = 16_000
const FRAME_MS = 30
const BYTES_PER_SAMPLE = 2
export const FRAME_BYTES = (SAMPLE_RATE * BYTES_PER_SAMPLE * FRAME_MS) / 1000

export function pcmFrameRms(frame: ArrayBuffer | Uint8Array): number {
  const view = frame instanceof Uint8Array ? frame : new Uint8Array(frame)
  if (view.length < 2) return 0
  let total = 0
  const count = view.length / 2
  for (let i = 0; i < view.length; i += 2) {
    const sample = view[i] | (view[i + 1] << 8)
    const signed = sample > 0x7fff ? sample - 0x10000 : sample
    total += signed * signed
  }
  return Math.sqrt(total / count)
}

export function pcmDurationSeconds(byteLength: number, sampleRate = SAMPLE_RATE): number {
  if (!byteLength) return 0
  return byteLength / (sampleRate * BYTES_PER_SAMPLE)
}

export function pcmTail(pcm: Uint8Array, maxSeconds: number, sampleRate = SAMPLE_RATE): Uint8Array {
  const maxBytes = Math.floor(maxSeconds * sampleRate * BYTES_PER_SAMPLE)
  if (pcm.length <= maxBytes) return pcm
  return pcm.slice(pcm.length - maxBytes)
}

export function pcmToWavBlob(pcm: Uint8Array, sampleRate = SAMPLE_RATE): Blob {
  const buffer = new ArrayBuffer(44 + pcm.length)
  const view = new DataView(buffer)

  const writeString = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + pcm.length, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * BYTES_PER_SAMPLE, true)
  view.setUint16(32, BYTES_PER_SAMPLE, true)
  view.setUint16(34, BYTES_PER_SAMPLE * 8, true)
  writeString(36, 'data')
  view.setUint32(40, pcm.length, true)
  new Uint8Array(buffer, 44).set(pcm)

  return new Blob([buffer], { type: 'audio/wav' })
}

export function floatToPcm16(input: Float32Array): Uint8Array {
  const out = new Uint8Array(input.length * 2)
  for (let i = 0; i < input.length; i += 1) {
    const clamped = Math.max(-1, Math.min(1, input[i] ?? 0))
    const sample = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
    const intSample = Math.round(sample)
    out[i * 2] = intSample & 0xff
    out[i * 2 + 1] = (intSample >> 8) & 0xff
  }
  return out
}

export function downsampleBuffer(
  buffer: Float32Array,
  inputRate: number,
  outputRate = SAMPLE_RATE,
): Float32Array {
  if (outputRate === inputRate) return buffer
  const ratio = inputRate / outputRate
  const length = Math.round(buffer.length / ratio)
  const result = new Float32Array(length)
  let offset = 0
  for (let i = 0; i < length; i += 1) {
    const nextOffset = Math.round((i + 1) * ratio)
    let sum = 0
    let count = 0
    for (let j = offset; j < nextOffset && j < buffer.length; j += 1) {
      sum += buffer[j] ?? 0
      count += 1
    }
    result[i] = count ? sum / count : 0
    offset = nextOffset
  }
  return result
}

export class SilenceDetector {
  private hasSpeech = false
  private lastSpeechAt = 0
  private speechStartedAt = 0
  private silenceSeconds: number
  private minSpeechSeconds: number
  private rmsThreshold: number

  constructor(
    silenceSeconds: number,
    minSpeechSeconds: number,
    rmsThreshold = 450,
  ) {
    this.silenceSeconds = silenceSeconds
    this.minSpeechSeconds = minSpeechSeconds
    this.rmsThreshold = rmsThreshold
  }

  reset() {
    this.hasSpeech = false
    this.lastSpeechAt = 0
    this.speechStartedAt = 0
  }

  feed(frame: Uint8Array, now = performance.now() / 1000): 'speech' | 'silence' | 'utterance_end' {
    const isSpeech = pcmFrameRms(frame) >= this.rmsThreshold
    if (isSpeech) {
      if (!this.hasSpeech) this.speechStartedAt = now
      this.hasSpeech = true
      this.lastSpeechAt = now
      return 'speech'
    }
    if (!this.hasSpeech) return 'silence'
    if (now - this.lastSpeechAt < this.silenceSeconds) return 'silence'
    const speechSeconds = Math.max(0, this.lastSpeechAt - this.speechStartedAt)
    if (speechSeconds < this.minSpeechSeconds) {
      this.reset()
      return 'silence'
    }
    this.reset()
    return 'utterance_end'
  }
}

export type MicSession = {
  stop: () => void
}

export async function startMicCapture(
  onFrame: (frame: Uint8Array) => void,
): Promise<MicSession> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
    },
  })

  const context = new AudioContext()
  const source = context.createMediaStreamSource(stream)
  const processor = context.createScriptProcessor(4096, 1, 1)
  const inputRate = context.sampleRate
  let pending = new Uint8Array(0)

  processor.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0)
    const downsampled = downsampleBuffer(input, inputRate, SAMPLE_RATE)
    const pcm = floatToPcm16(downsampled)
    const merged = new Uint8Array(pending.length + pcm.length)
    merged.set(pending)
    merged.set(pcm, pending.length)
    pending = merged

    while (pending.length >= FRAME_BYTES) {
      const frame = pending.slice(0, FRAME_BYTES)
      pending = pending.slice(FRAME_BYTES)
      onFrame(frame)
    }
  }

  source.connect(processor)
  processor.connect(context.destination)

  return {
    stop: () => {
      processor.disconnect()
      source.disconnect()
      stream.getTracks().forEach((track) => track.stop())
      void context.close()
    },
  }
}

export const LISTEN_PROMPT = '我在听，请说。'
