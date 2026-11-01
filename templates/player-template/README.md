# Player runtime contract

This is a working transport and adapter interface, not a pretranslated production. The default `app/port.mjs` fails with a clear unconfigured-port message. It never substitutes a procedural effect for a missing port.

Run `node server.mjs` or the Windows launcher after copying this directory to `player/`. The explicit `/?fixture=1` URL (or `/?fixture=visual` for silent development) exercises a synthetic infrastructure fixture, clearly labeled “not a demo port.” It is for framework tests only; remove examples/tests and disable that fixture route in a release. It is never evidence that an original production is reproduced.

## Production adapter

Implement `app/port.mjs` and import the production's translated routines/data from it:

```javascript
export const metadata = {
  title: 'Recovered production title',
  duration: measuredDuration,
  displayAspect: recoveredAspect,
  audio: 'pending', // visuals first; later 'original-code', or 'none' if verified silent
  audioChannels: outputChannels,
  provenance: originalCodeEvidence,
};
export async function createVideoPort() { /* return the contract below */ }
// The template derives audio metadata and re-exports its resource loader from audio-port.mjs.
```

Use explicit `duration: null` for an open-ended/interactive production; the transport does not invent a natural ending or finite timeline scrubber. A finite capture window is not proof of an original natural end. The adapter owns looping or interactive progression.

The video port implements:

- `reset()`: restore its own authentic startup state.
- `advanceTo(seconds)`: advance translated simulation to the requested time using recovered timing. Repeating the same target must not advance it again. Preserve logical feedback/draw-dependent updates here, even when their images are not presented. An assumed logical draw cadence must be documented separately from the timer; neither comes from screenshot spacing or slow emulator rasterization.
- `render()`: return `{width, height, rgba}` with live `Uint8Array`/`Uint8ClampedArray` pixels for the current state. Repeated redraws must not advance feedback, simulation, or timers. Scratch-buffer work is allowed if redraws remain observationally equivalent. The runtime does not assume a resolution, palette precision, display aspect, scene count, CPU mode, or 3D pipeline.
- Optional `seek(seconds)`: restore a verified complete checkpoint and simulate forward. If absent, the runtime resets and advances translated code. No captured screenshot or recording is used.

`runtime/port-runner.mjs` provides this transport plus `SceneSequence` for optional scene composition. A scene factory receives the preceding translated scene's `handoff()` output. Its `reset()` must restore that inherited startup state. Preserve relevant buffers, palettes, feedback, timers, or any other shared state; never silently replace a transition with a fresh captured screen. The production may implement its own continuous dispatcher instead of discrete scenes.

Simulation/rendering are separated. `PlaybackClock` handles pause/resume and time-source changes; the main thread sends presentation targets, and the worker keeps a bounded reusable frame-buffer pool. Seek epochs reject stale frames/messages. The browser exposes `window.player.snapshot()` from the actual canvas, with geometry and a SHA-256 digest; it also exposes pause, seek, start/stop, and measured worker/frame timings for acceptance tests.

The default player is smooth playback, not a replay of draw-completion timestamps from a slow emulator. Capture-schedule matching belongs in an explicitly selected validation configuration/adapter. Compare it separately; matching that mode does not establish the normal playback draw rate. Keep a timing note with the recovered timer/music clock, draw-dependent update model, presentation policy, and evidence or provisional assumptions. See [timing guidance](../../docs/guides/sync-and-timing.md).

## Original-code audio

Implement sound in the separate `app/audio-port.mjs`, keeping its top-level imports safe for AudioWorklet (no graphics, DOM, or main-thread-only API initialization). Its metadata supplies the video adapter’s audio status/channels/provenance. If `metadata.audio` is `original-code`, implement `createAudioPort({sampleRate, resources})` there with `reset()`, `seek(seconds)`, and `render(channels, frames)`. Rendering fills the supplied float PCM channels, returns the number of frames generated, and maintains the original replay state across calls. The requested output sample rate is a presentation parameter; recover original pitch, timer, synthesis, and mixer semantics from the original code. PCM output channels are not the number of music voices.

Optional `loadAudioResources()` runs on the main thread before worklet initialization and supplies immutable decoded data via `resources`. Avoid network/file loading in the real-time process callback. The default worklet statically imports the audio adapter, independently of the graphics adapter, because dynamic module import is not available in the audio worklet environment. Heavy translated code can use the optional request-driven `audio-worker.mjs` producer with a production-tested bounded queue; the default runs the translated mixer directly in the worklet. Measure deadline misses before changing architecture.

Only translated original sequencer/replay/mixer/synthesis/device-control code is permitted. No module-player libraries, generic replacement synth, recorded soundtrack, or standard-format shortcut. Hardware-based sound needs a tested device adapter driven by the original code; a tracker is only one possible source. Silent productions and visuals-first development work without audio. Preserve any original music-driven visual control behavior independently of whether sound is audible.

The audio clock advances with generated output samples; pause outputs silence without advancing replay state. Seeking invokes the translated audio adapter's own state restoration/replay. Audio errors are surfaced instead of silently replacing the soundtrack. Transport tests do not establish original mixer or hardware fidelity.

## Checks

```powershell
node --test tests/runtime.test.mjs
node tests/browser.mjs
```

`tests/cadence-check.mjs` exports `checkPresentationSchedules(createVideoPort, metadata, {times})` for agent-selected logical times across an effect/transition. It compares frames under representative presentation request rates, repeated redraws, and repeated same-time advances. The rates are test schedules, not proposed original tick/draw rates. A PASS does not prove the chosen logical draw model or all hidden state is correct; add explicit state/sequence contracts for that. A high RAF count alone is not evidence that the displayed animation actually changes smoothly.

The browser check uses installed Chrome/Chromium/Edge (`CHROME` may name an executable), a local server, and a disposable headless profile. It tests the real canvas, actual audio production, pause, paused/backward seek, a near-ending frame, and resume against independently rendered fixture frames. The test output explicitly limits the result to infrastructure.

For a real port, generate expected frame digests independently from the verified renderer, include transition/ending cases, and run:

```powershell
node tests/browser.mjs --url http://127.0.0.1:1997/ --expectations expected-frames.json
```

The expectations file contains `{"frames":[{"time":2.5,"sha256":"actual-digest"}]}`. The digest is `frameDigest()` from `runtime/port-runner.mjs`: little-endian width/height followed by exact RGBA bytes. Paths, times, and digests are prepared by the agent, not filled in by the human. This is browser integration evidence, separate from comparison against original captures or controlled-schedule execution.

Record full-run performance on the actual port: frame intervals, advance/render p95/max, allocations, stalls, and transition/seek cost. The fixture's measurements are not a performance guarantee. Use checkpoints only when measured replay cost justifies them; size and spacing depend on the production and all future-affecting state must be restored.

### Shell configuration and packaging

Populate metadata.group, releaseInfo, credits:[{role,name}], links:{pouet,github}, palette:{accent,text}, and landing:{start,end,drawRate} with production evidence. The landing animation uses the same original video adapter in an independent worker; its time range and cadence belong to that production. The default remains unconfigured and fails clearly.

Audio diagnostics() returns original cursor/device state without altering replay output. Optional video-adapter loadDiagnosticsResources() returns normalized display-only module rows (see the standard). The shared module grid never renders audio or guesses tracker time. Prove PCM/state is unchanged by diagnostics reads.

Run node player/build-release.mjs from the project root. It uses one sibling release/ directory, keeps development fixtures disabled via app/release-mode.mjs, and creates root/player entry pages, server and hash manifest. Audit stale/unused production assets before acceptance; the builder is not a semantic dependency analyzer. Test the final artifact, not a development URL. Browser --output release/browser-acceptance.json writes scoped machine-readable results. Actual slider gestures are covered; complete the remaining standard checklist and record skipped cases explicitly. Use a recovered duration:null for open-ended ports, with disabled absolute timeline and no invented ending.
