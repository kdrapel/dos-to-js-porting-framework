# Playback timing, simulation, and capture validation

The normal player should produce smooth live animation from the recovered original clocks. Screenshot cadence and slow emulator draw completions are validation observations, not an automatic playback schedule. Fixed CPU cycles can make the original rasterizer spend a long time drawing while timer interrupts continue to advance animation.

## Keep three time domains separate

| Domain | Recover from | What it controls |
| --- | --- | --- |
| Animation/music simulation | Original counters, timers, replay state, scripts and calibrations | Logical motion, transitions and sound progression |
| Draw-dependent simulation | Original frame counters, feedback, accumulation and update order | State that changes when a logical draw/update occurs |
| Presentation | Browser display requests and current media position | Which already-computed logical state is shown |

A timer frequency does not imply a draw frequency. Do not choose a fixed draw limit merely by dividing the timer rate, measuring screenshot gaps, or copying the duration of a slow emulator draw. Some clocks vary by scene or tempo; do not prescribe a universal rate.

Record a short timing note for each relevant effect: clock/counter source, observed calibration, draw-dependent state, chosen logical update policy, presentation policy, and evidence. Label each value recovered, measured, or provisional. A provisional rate can support ongoing smooth visual development, but remains an explicit verification task and is not evidence of the original draw rate.

## Two purposes, two schedules

**Normal playback** advances original algorithms to current media time and presents the latest state at the display's pace. It is the default. Render intermediate states from the translated code rather than holding captured pictures until the next sampled draw completion.

**Capture-matching validation** reproduces an explicitly recorded or controlled draw/interrupt schedule to compare a particular reference state. Keep it opt-in in a validation driver/configuration. Matching its pixels does not establish that its slow draw schedule is suitable for normal playback. A capture mode must not silently become the player default because it produces convenient exact matches.

Compare both evidence classes separately. Use justified logical counters and operation boundaries to align comparisons when wall-time snapshots contain frames assembled over a slow draw. Preserve original arithmetic and quirks; do not invent screenshot blending, motion interpolation, or hidden duration corrections to force a match.

## Stateful drawing is simulation

Feedback, trails, palette accumulation, per-frame physics and counters can depend on logical draw/update count. Keep those operations in the simulation at an evidence-backed cadence. Merely rendering them more often changes the effect; merely dropping them while catching up also changes the effect.

`advanceTo(T)` must execute the updates needed to reach T, including required intermediate feedback rasterization even when those pictures are not presented. Repeating the same target must not advance state again. `render()` presents the current state and repeated redraws must be observationally equivalent. It may rebuild scratch buffers; it must not increment timers, feed another iteration into an effect, or advance musical state.

A port may combine internal rasterization and feedback updates as its original algorithm requires, but public presentation requests must remain independent. Compare relevant state as well as pictures when a latent difference can affect later frames.

## Silent development and sound integration

Full visual development may precede audible replay. Use a replaceable presentation clock and recover music-driven control values as needed without requiring the full sound pipeline first.

After original-code audio is integrated, use soundtrack/media position derived from output samples and its seek/pause origin. Mixing ahead is not the same as hearing that audio; account for queue/output latency separately. `AudioContext.currentTime` since context creation is not automatically the production's song position after startup, pause or seek.

Keep simulation, drawing, and display refresh independent. Advance logical state to current media position and present the latest result. If performance falls behind, omit obsolete presentations while preserving required simulation/feedback updates. Never slow original sound to accommodate graphics. On tab return or after a seek, catch up using the same logical model and reject stale frames by request epoch.

## Required checks

- Compare equal logical times across different presentation request schedules; repeated same-time advance/redraws must not alter the result. The player template's `tests/cadence-check.mjs` provides a bounded frame-level property check; its test rates are not original timing defaults.
- Check intermediate motion between capture timestamps, where the original algorithms establish that motion should occur. A high RAF/render count can still display one held picture repeatedly; measure changing pictures or relevant animation counters when evaluating an animated effect.
- Verify draw-dependent state, transitions, ending conditions and sound anchors under the chosen logical model. Use existing full-run snapshots and static/offline timing analysis before considering more human captures.
- Compare capture-mode matches separately from smooth playback and document why their outputs may differ under different interrupt/draw schedules. Neither controlled-schedule equivalence nor smooth appearance proves original wall-time behavior.
- Review actual browser frame intervals, queueing, advance/render cost, stalls and seek behavior. Match output rate/latency requirements to the original production and host; there is no universal buffering delay or drift-free performance guarantee.
