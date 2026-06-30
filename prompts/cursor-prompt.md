# Cursor Prompt — Neural Pal Wakeup

Copy this when starting a new Cursor session on this project:

---

You are working on **Neural Pal Wakeup** — a React + Motion cinematic AI boot animation.

**Stack:** Vite, React 19, TypeScript, Motion, SVG, Flubber, Tailwind v4

**Key files:**
- `src/components/boot/NeuralWakeup.tsx` — timeline orchestrator
- `src/components/boot/GlowOrb.tsx` — SVG wave/circle
- `src/motion/timing.ts` — phase timeline
- `src/motion/paths.ts` — SVG paths for morphing

**Rules:**
- Keep components under 250 lines
- Use easing `[0.22, 1, 0.36, 1]` for major transitions
- No cyberpunk / neon / HUD aesthetics
- Flubber for path morphing only during collapse phase
- Do not add Remotion unless explicitly asked

**Timeline:** wave breathe (0–1.2s) → morph (1.2–3.8s) → circle breathe (3.8–4.8s) → text (4.8–5.8s) → interface (5.8–7.0s)

Read `docs/motion-spec.md` and `docs/design-system.md` before making animation changes.

---
