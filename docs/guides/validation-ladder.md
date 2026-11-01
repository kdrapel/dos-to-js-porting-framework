# Validation from original bytes to the actual player

The framework supplies contracts, capture readers, batch execution, and a player transport. Each production supplies its original algorithms, layout, clock, and any required CPU/device adapters. No fixed scene count, instruction set mode, framebuffer geometry, sound format, or tracker channel count is assumed by the player interface.

## Start with a small executable model

Run `python tools/oracle/binary_triage.py original` to inventory formats, hashes, entry metadata, and candidate packed/music signatures. Signatures are hypotheses. Verify decompression, relocation, initialized data, and overlay placement against captured bytes. Extract original assets and reconstruct generated tables with original algorithms; do not replace live rendering with captured pictures.

Use the assembly index for bounded navigation. Compare suspected engine copies with:

```powershell
python tools/asm_index/compare_routines.py --db oracle/current.sqlite --left routine_a --right routine_b
```

The agent discovers database/symbol names. Normalized similarity finds candidates; inspect the raw differences and verify each variant. A changed shift, rounding instruction, segment base, or overlapping buffer may be part of the intended effect. Parameterize verified layouts/variants in a shared engine instead of repeatedly translating copies. Retain address comments until tests pass.

## Five scales of evidence

| Stage | Required exercise | Useful failure location |
| --- | --- | --- |
| Routine | Real inputs across several suitable full-run checkpoints, including different branches/phases | First register, output range, or byte difference |
| Interval | Multiple dependent updates from the same state, without resetting between updates | First divergent simulation tick/operation |
| Scene | Setup, intermediate state, palettes, buffers, ending/fade under a declared schedule | First failing frame and scene state |
| Transition | Predecessor end state passed to the successor; compare uninterrupted and restored/replayed progression | First inherited state mismatch |
| Browser | The real page's canvas and transport versus independently produced expected frames; actual audio output, pause/seek/resume/ending | First page time/frame, runtime error, or transport failure |

One routine pass does not prove a scene, and matching a Node renderer does not prove the browser presents it. Expose deterministic presentation time and frame digests in the actual player. When a scene differs, add bounded operation checks (polygon, span, palette step, simulation update) where appropriate to that production. These are offline diagnostics, not extra manual capture requests.

## Full-run corpus and comparison contracts

Capture one complete run with adequate memory, normally the starter 8 MiB every 1–2 seconds. Keep it immutable. Use `replay_suite.py --list-checkpoints` to see which checkpoints have usable memory. Resume mid-routine states offline where appropriate; do not require a live CALL/return pair. The capture reader excludes partial/unreadable memory, verifies aliases, preserves gaps, and can fork independent working memory.

Copy the comparison-contract and replay-suite templates to new working paths. The agent fills them from evidence; the human does not supply capture IDs or addresses. Required output ranges must cover the routine's observable effects, not merely a convenient sample. Declare live registers/flags and justified exclusions before interpreting differences. An optimized typed-array implementation need not reproduce dead CPU temporaries or the same store granularity; ordered writes are appropriate only when that order is an observable contract requirement and both instruments represent it consistently.

```powershell
python tools/oracle/replay_suite.py --session oracle/extract/SESSION --list-checkpoints
python tools/oracle/replay_suite.py --session oracle/extract/SESSION --plan oracle/replay-suite.json --output oracle/new-suite-results
python tools/oracle/differential_compare.py --contract oracle/comparison-contract.json --reference oracle/reference.json --js oracle/javascript.json
```

Paths here are illustrative agent inputs, not placeholders for the human to fill. Suite output must be new and outside immutable captures and originals. Cases may declare `routine`, `interval`, `scene`, `transition`, or `browser` stages. Missing required stages, required observations, input identity, complete ordered-write digests, or successful endpoints yield `INSUFFICIENT_EVIDENCE`, not PASS. Differences with sufficient evidence yield FAIL; only declared matching checks yield PASS. Exit codes are 2, 1, and 0 respectively. Small output ranges include diagnostic bytes so a mismatch identifies its first address.

For interval/scene debugging, drivers can emit JSONL report streams with matching `sample` markers (for example tick, frame, and polygon/span/update). `sequence_compare.py` compares them incrementally and reports the first divergent sample/byte rather than loading the whole trace into context. Optional `--expected-samples` and `--final-tick` assert planned coverage and detect two equally truncated streams. A batch case with `sequence: true` uses explicit reference/JavaScript commands; whole-scene/transition stream cases require `expected_samples` and `final_tick`. Supply the original measured/controlled schedule, not a universal frame rate. These are agent-prepared checks, not extra user captures.

The JavaScript driver receives an input manifest and writes its report using `tools/oracle/report.mjs`. It gets original inputs, not reference outputs. The helper verifies input-file hashes, forks memory, maintains aliases, and hashes all observed writes rather than a truncated preview. Large bulk stores intentionally cannot claim instruction-level write equivalence.

## CPU, devices, and timing limits

The built-in Unicorn adapter supports bounded integer intervals in conventional real-mode 16-bit or captured GDT-based protected-mode 32-bit execution. It rejects uncaptured reads/fetches, paging, LDT/unreal-mode state, and unsupported hardware/x87/vector operations. It does not invent descriptor bases, FPU registers, device reads, or zero-filled heap data. Boundary counters and write digests describe Unicorn hook observations, not proof of hardware instruction retirement.

Other environments use explicit offline Python/Node `reference_command` drivers in the same suite protocol. The input includes captured machine/auxiliary-state paths and hashes; those drivers must restore and independently test required state. Unsupported adapters leave a case incomplete; they are an agent implementation task, not automatic justification for another human capture. CPU adapter regressions cover known machine-code behavior; production-specific hardware adapters need their own reference checks.

For scene tests, the driver may control timer/interrupt delivery to make both executions deterministic. Record that schedule and the covered state. This proves agreement under that schedule, not exact DOSBox or hardware timing. Keep such tests separate from checks against the observed full-run timeline. Any measured duration adjustment belongs in explicit timing data with provenance, not hidden algorithm changes.

Capture-matching validation must not become the default playback scheduler. A low-cycle emulator can complete draws much more slowly than the recovered animation clock. In normal playback, compute live intermediate states from original algorithms and keep timer, draw-dependent simulation, and presentation policies distinct. Align reference comparisons by justified logical counters/state rather than forcing every smooth frame onto a sparse wall-time capture. Record provisional draw-rate assumptions and verify them from existing code/corpus; a timer frequency alone does not establish a draw rate. Check feedback and other frame-dependent effects under the declared logical model, and ensure redraw count/monitor refresh do not change it. See [timing guidance](sync-and-timing.md).

## Sound uses the original code

Translate and verify the production's own sequencer, replay, mixer, synthesis, and/or device-control routines as applicable. Recover original data, but do not substitute libopenmpt, another module player, a generic synth, or recorded music. Some productions use hardware voices, FM, speakers, streams, or no sound: provide only the evidence-backed device behavior needed by the original code, and state fidelity limits. Standard formats do not imply a standard replay routine.

Audio may follow the full visual sequence. When integrated, test original replay state, PCM or device-register evolution, chunk invariance, sample/loop boundaries, seeking, and the full visual/audio timeline. The player has a single audio output transport; it does not prescribe a format or a number of music voices.

## Implementation scope

`templates/player-template/README.md` documents the working runtime contract and checks. Its opt-in reference fixture verifies infrastructure only and must not appear as evidence for a port. Original release bytes, captured screenshots, an offline oracle match, controlled-schedule scene checks, browser integration, and measured performance remain distinct evidence classes.

These generic tools and runtime were implemented for this framework; no production-specific engine, scene scripts, memory model, or module replay library is included.

## Standard final player

Step 10 follows the [canonical release player specification](release-player-standard.md). Use the supplied landing/player/diagnostics shell and one release/ directory. Adapt production metadata, palette and source adapters; retain layout, controls and tested behavior. Test actual timeline gestures and both entry pages, not only window.player.seek(). Include measured FPS and source-driven module diagnostics, live darkened original landing animation, complete audiovisual seeks and packaged human review. Pending tests cannot be reported as PASS. Publication remains human-owned.
