# Porting original demoscene code to the browser

The original release bytes and captured runtime state are evidence. Disassembly is an interpretation to verify against those bytes. Translate the original algorithms into live JavaScript; do not replace them with a visual imitation, captured-frame playback, or recorded music.

## Reusable framework and production adapters

The framework supplies capture/provenance tools, bounded assembly navigation, explicit comparison contracts, an offline validation ladder, and a tested browser transport. Each production supplies its memory layout, loader/unpacker, clocks, algorithms, assets, and any CPU/device behavior required by its code. Do not assume a tracker, a 3D engine, mode 13h, a fixed CPU mode, channel count, frame rate, or scene structure.

Triage formats and packed assets before exporting or reading large listings. Reconstruct verified loader placement/relocation and original generated tables. Compare candidate copies of routines before translating them repeatedly. Share an engine only after verifying the layout and behavioral differences; preserve intended overflow, rounding, aliases, and self-modifying parameters.

## One full run, many offline experiments

The human operates DOSBox-X and supplies a start-to-end timeline with adequate memory, normally the starter 8 MiB at every 1–2-second snapshot. The agent audits actual mappings/readability and reuses checkpoints offline. Missing bytes in an undersized run call for a corrected full run first, not repeated point captures.

Fork a checkpoint's state, resume a bounded interval of original code in an offline reference, and run the JavaScript translation on the same real input. A sampled mid-routine state is usable without recapturing entry/return. The built-in Unicorn adapter supports specific tested integer CPU environments; unsupported FPU, paging, hardware, or other modes require verified offline adapters and remain explicitly incomplete until supported. See [validation ladder](docs/guides/validation-ladder.md).

## Compare declared behavior, with evidence

A contract declares successful boundaries, relevant registers/flags, exact output ranges, optional complete memory, ordered writes where meaningful, and justified exclusions. Missing observations, different initial states, execution limits, or unsupported operations cannot yield PASS. Small mismatching buffers identify their first differing byte. An optimized bulk implementation may have different dead temporaries/store granularity; exclusions must be justified before interpreting a result.

Validate several real checkpoints/branches, then dependent intervals, whole scenes, transitions, and the actual browser page. Scene tests may own the interrupt/tick schedule for deterministic comparison. Report that schedule explicitly: agreement under a controlled schedule is not proof of matching DOSBox or hardware timing. Test endings and inherited state, not only attractive middle frames. A passing routine is not whole-demo validation.

## Runtime and timing

Default to smooth live playback. Keep matching a slow capture’s draw/interrupt schedule as an explicit validation mode, never a frame-rate default. Recover animation time separately from draw-dependent state; a timer rate alone does not establish the draw rate. Record provisional assumptions and verify them without conflating exact capture matches with normal playback timing.

Keep presentation time, simulation updates, and drawing separate. The player adapter exposes reset, advance-to-time, and live rendering with its own geometry. Full graphics may precede sound. Use a replaceable clock based on recovered timing and preserve any music-driven visual control data even when silent. Once sound is integrated, generated audio samples provide the presentation time source; check the full audiovisual timeline and report remaining differences. No universal drift-free or frame-rate guarantee is assumed.

Use a render worker and bounded frame-buffer reuse. The template has an original-code audio worklet path; a request-driven producer worker is available when measured audio work justifies it. Profile the actual page, including queueing, garbage collection, transitions, pause, seek, and audio starvation. Fast isolated kernels do not guarantee smooth presentation.

## Original sound code

Translate the production's own replay, sequencer, mixer, synthesis, or device-control code as applicable. Recover original music/sound data without substituting a module library or generic synth. Model hardware behavior only where required and supported by evidence. Verify replay state and PCM or device-register effects, chunk invariance, loops, timing, and seeking. Explicitly distinguish translated sound-code tests from hardware-output fidelity.

## Seeking and delivery

Start with deterministic reset-and-advance. Add checkpoints only when measured seeking cost warrants them. Preserve all future-affecting memory, palette, simulation, replay/device, and FPU state where relevant; checkpoint size/spacing are production-dependent. Compare restore-and-forward execution against uninterrupted execution across scenes.

The shipped player must run translated code, not the development oracle. Browser checks exercise its real controls/canvas and compare the presented frames with independent expected frames. Infrastructure fixtures are labeled and must never masquerade as a port. Keep implementation status, evidence classes, exclusions, and unresolved differences in the handoff. Publication remains the human's decision.

## Standard final player

Step 10 follows the [canonical release player specification](docs/guides/release-player-standard.md). Use the supplied landing/player/diagnostics shell and one release/ directory. Adapt production metadata, palette and source adapters; retain layout, controls and tested behavior. Test actual timeline gestures and both entry pages, not only window.player.seek(). Include measured FPS and source-driven module diagnostics, live darkened original landing animation, complete audiovisual seeks and packaged human review. Pending tests cannot be reported as PASS. Publication remains human-owned.
