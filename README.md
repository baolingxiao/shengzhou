# Neural Pal Wakeup

A production-quality React motion project featuring a cinematic AI OS wakeup animation — warm, minimal, and human-centered.

## Quick Start

```bash
npm install
npm run dev
```

Open [http://localhost:5190](http://localhost:5190) to watch the wakeup sequence.

> Default dev port is **5190** (configured in `vite.config.ts`). If it's busy, Vite will try the next available port automatically.

## Scripts

| Command           | Description              |
| ----------------- | ------------------------ |
| `npm run dev`     | Start development server |
| `npm run build`   | Type-check and build     |
| `npm run preview` | Preview production build |
| `npm run lint`    | Run ESLint               |

## Tech Stack

- **Vite** — fast dev/build tooling
- **React 19 + TypeScript** — component architecture
- **Motion** — animation orchestration
- **SVG + Flubber** — organic path morphing
- **Tailwind CSS v4** — design tokens and layout

## Project Structure

```
src/
  app/              App entry
  components/
    boot/           Wakeup animation components
    ui/             Reusable UI primitives
  motion/           Paths, timing, springs, morph hook
  styles/           Global CSS + Tailwind theme
  lib/              Utilities (cn)
docs/               Motion spec + design system
prompts/            Cursor / vibe prompts
```

## Animation Timeline

| Time    | Phase                              |
| ------- | ---------------------------------- |
| 0–1.2s  | Organic wave breathes              |
| 1.2–3.8s| Wave collapses, morphs to circle   |
| 3.8–4.8s| Circle stabilizes with breathing   |
| 4.8–5.8s| “Hello, Jin.” fades in             |
| 5.8–7.0s| Minimal AI interface appears       |

## Reusable Component

```tsx
import { NeuralWakeup } from './components/boot/NeuralWakeup'

<NeuralWakeup userName="Jin" onComplete={() => console.log('Ready')} />
```

## Repository

[github.com/baolingxiao/Neural_Pal_wakeup](https://github.com/baolingxiao/Neural_Pal_wakeup.git)

## License

MIT
