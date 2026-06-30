# Motion Spec — Neural Pal Wakeup

## Overview

A 7-second cinematic sequence that transitions from an organic glowing wave to a stable orb, greeting text, and minimal AI interface.

## Easing

All primary transitions use cubic-bezier **`[0.22, 1, 0.36, 1]`** — smooth deceleration without bounce or elasticity.

## Phases

### 1. Wave Breathing (0.0s → 1.2s)

- **Path:** `WAVE_PATH` — asymmetric organic ring
- **Scale:** 0.98 ↔ 1.02
- **Opacity:** 0.75 ↔ 1.0
- **Glow blur:** subtle pulse via filter opacity
- **Cycle duration:** 2.4s (overlapping start)

### 2. Collapse & Morph (1.2s → 3.8s)

- **Duration:** 2.6s
- **Interpolator:** Flubber dual-stage morph
  - Stage A: `WAVE_PATH` → `WAVE_COLLAPSED_PATH` (first 50%)
  - Stage B: `WAVE_COLLAPSED_PATH` → `CIRCLE_PATH` (second 50%)
- **No bounce.** Single easing curve across full progress.

### 3. Circle Breathing (3.8s → 4.8s)

- **Path:** `CIRCLE_PATH` — perfect circle (60px radius)
- Same breathing parameters as wave phase

### 4. Text Reveal (4.8s → 5.8s)

- **Copy:** “Hello, Jin.”
- **Motion:** opacity 0→1, translateY 12px→0
- **Duration:** 1.0s

### 5. Interface Reveal (5.8s → 7.0s)

- Orb fades to 35% opacity, scales to 0.92
- Panel slides up with soft glow
- Status orb breathes independently

## SVG Details

| Property      | Value                          |
| ------------- | ------------------------------ |
| ViewBox       | 400 × 400                      |
| Stroke width  | 6px core, 12px ambient         |
| Gradient      | `#FFF5EB` → `#FFD4A8` → `#FFB86C` |
| Filters       | Gaussian blur glow layers      |

## File Map

| File                    | Role                        |
| ----------------------- | --------------------------- |
| `motion/timing.ts`      | Timeline constants + phases |
| `motion/paths.ts`       | SVG path definitions        |
| `motion/usePathMorph.ts`| Flubber interpolation hook  |
| `motion/springs.ts`     | Shared transition configs   |
| `boot/NeuralWakeup.tsx` | Master orchestrator         |
| `boot/GlowOrb.tsx`      | SVG rendering + breathing   |

## Future (Remotion)

This spec is designed to port cleanly to Remotion compositions. Do not implement Remotion until explicitly requested.
