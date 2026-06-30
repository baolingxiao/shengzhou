# Design System — Neural Pal

## Philosophy

Warm minimalist AI — calm, emotional, human-centered. Inspired by the feeling of *Her*, but fully original. No cyberpunk, neon blue, HUD overlays, or futuristic dashboards.

## Color Tokens

| Token            | Hex       | Usage                    |
| ---------------- | --------- | ------------------------ |
| `background`     | `#F8F3EA` | Page background          |
| `foreground`     | `#3D3630` | Primary text             |
| `muted`          | `#8A8279` | Secondary text           |
| `surface`        | `#F0EBE2` | Panels, inputs           |
| `border`         | `#E5DDD2` | Subtle borders           |
| `glow`           | `#FFD4A8` | Primary warm glow        |
| `glow-core`      | `#FFF5EB` | Highlight / core light   |
| `glow-warm`      | `#FFB86C` | Accent warmth            |

## Typography

- **Font:** Inter (300, 400, 500)
- **Greeting:** 36–48px, font-light, tracking-tight
- **UI title:** 18px, font-medium
- **UI body:** 14px, text-muted

## Spacing & Radius

- Panel radius: `rounded-3xl` (24px)
- Input radius: `rounded-2xl` (16px)
- Button radius: `rounded-full`

## Motion Principles

1. **Breathe, don't bounce** — scale and opacity oscillate gently
2. **Decelerate into rest** — ease-out-expo on all major transitions
3. **Layered glow** — wide ambient + tight core stroke
4. **Progressive disclosure** — orb → text → interface, never all at once

## Components

| Component        | Location                    |
| ---------------- | --------------------------- |
| `NeuralWakeup`   | Full wakeup sequence        |
| `GlowOrb`        | SVG wave/circle with glow   |
| `WakeupText`     | Greeting overlay            |
| `NeuralInterface`| Post-wakeup minimal UI      |
| `Panel`          | Soft container              |
| `Button`         | Ghost / soft variants       |

## Accessibility

- Input has associated `<label>` (sr-only)
- Focus rings use warm glow color
- Respects `prefers-reduced-motion` (future enhancement)
