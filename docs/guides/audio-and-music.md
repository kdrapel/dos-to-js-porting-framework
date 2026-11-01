# Original sound-code translation and live output

The production's original code defines sound behavior. Translate its sequencer, replay, mixer, synthesis, and/or device-control routines and use the original sound data. Do not substitute a module-player library, a generic synthesizer, or recorded music. A recognizable MOD/S3M/XM/IT header is useful evidence about data, not permission to replace the original player.

## Recover the actual system

Determine how this production generates sound: sampled voices, FM/device registers, speaker toggles, streamed data, tracker commands, custom code, or verified silence. Recover timers, channel/voice state, sample signedness/packing/loops, pitch arithmetic, effects, and output/device settings from the original readers and code. Do not infer all sample semantics from a format name. Preserve original quirks and integer/FPU precision where they affect the result.

Where the original controls hardware voices rather than mixing PCM on the CPU, retain that control code and implement a tested device adapter for its observable writes and timing. State which aspects of the device/output are modeled and which remain unverified. The framework's worklet is an output transport, not an automatically faithful replacement for every sound card.

## Validate offline before integration

Use real full-run checkpoint state and original bytes for bounded sound-code comparisons. Declare relevant replay variables, voice positions, phases, registers/flags, PCM ranges, or device events. Test several musical phases and loop/end boundaries, not just a header or a synthetic note.

Run the translated replay with different output chunk sizes and verify identical sample/state evolution at matching times. Respect fractional tick/voice phases across calls. Where the original uses device scheduling, verify that schedule explicitly. Audio capture can provide additional evidence when already available; do not routinely request new single-point emulator experiments.

## Runtime adapter

Implement the player [audio contract](../../templates/player-template/README.md): `createAudioPort({sampleRate, resources})` returns reset, seek, and render operations. The runtime provides float PCM output buffers, pause/seek control, and sample-count presentation time. Its sample rate and number of output channels are not the original number of music voices or an assumed tracker format.

The default path runs translated code directly in an AudioWorklet. Preload immutable resources on the main thread; keep allocations and unpredictable work out of the process callback. For expensive routines, use a separately tested request-driven worker and bounded prefill queue. Measure real deadline misses and starvation before choosing that extra architecture.

Seeking must restore/replay original audio state, including loop/effect memory and device state where relevant. Never implement it by resetting only the song order or playback clock. Audio errors must remain visible instead of silently falling back to another player or guessed synthesis.

## Work order and evidence

The human may complete the full graphical sequence before sound. Keep sound pending, preserve timing-related control variables needed by visuals, and integrate through the replaceable clock later. Then check full playback, transitions, pause, seek/resume, and endings with both sound and graphics.

Infrastructure fixture samples test transport only. Original-code state equivalence, PCM equivalence, subjective listening, captured waveform comparisons, and real-hardware fidelity are separate evidence classes. Record known differences without claiming universal exactness.
