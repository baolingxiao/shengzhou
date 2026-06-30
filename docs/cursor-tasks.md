# Cursor Tasks — Neural Pal Wakeup

## Completed

- [x] Vite + React + TypeScript scaffold
- [x] Tailwind CSS v4 with design tokens
- [x] Motion system (timing, paths, springs, morph hook)
- [x] GlowOrb with SVG filters and breathing
- [x] Flubber path morph wave → circle
- [x] WakeupText fade-in
- [x] NeuralInterface minimal post-wakeup UI
- [x] Documentation and prompts

## Future Enhancements

- [ ] `prefers-reduced-motion` fallback (skip morph, instant circle)
- [ ] Replay button after sequence completes
- [ ] Configurable greeting name via URL param
- [ ] Remotion composition export
- [ ] Storybook stories for boot components
- [ ] Unit tests for `phaseAtTime` and morph hook

## How to Extend

1. **New paths** — add to `src/motion/paths.ts`, wire in `GlowOrb`
2. **Timing changes** — edit `src/motion/timing.ts` only
3. **New UI states** — extend `WakeupPhase` union + `NeuralWakeup` orchestrator
