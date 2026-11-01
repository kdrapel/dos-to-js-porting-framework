# Agent Instructions & Operational Rules

This repository contains the **DOS Demo JavaScript Porting Framework**. If you are an AI agent assisting a human developer with reverse-engineering and porting a DOS demo to JavaScript, you MUST follow these non-negotiable operational rules.

---

## 1. Emulator Boundaries & Human Ownership

- **DOSBox and DOSBox-X are strictly operated by the human user**:
  - NEVER attempt to launch, execute, spawn, attach to, debug, or inspect DOSBox, DOSBox-X, or other emulator processes via bash/cmd/PowerShell.
  - NEVER attempt to take live memory captures or screenshots from an emulator yourself.
  - For the **first capture**, prepare a timeline profile from [the starter JSON](docs/templates/autocapture-config.template.json): sample every 1–2 seconds, start without an hour-long delay, continue until program exit or human Stop, use no address stop event, and disable instruction tracing. Use the debugger text to choose memory selectors. Run `python tools/oracle/validate_capture_profile.py --purpose timeline autocapture-config.json` and show its PASS result before asking the human to run it.
  - **Plan and audit memory coverage**: The template starts with an 8 MiB region, not 1 MiB. Justify reductions using selector bases/limits, available RAM, and complete input/heap/stack ranges; label unknown coverage provisional. Show validator warnings: its PASS does not prove coverage. Flag debugger pointers outside proposed regions. After capture, use descriptors and asset metadata to report actual ranges and partial/unreadable zero-filled bytes. Identical overlapping selector dumps do not add coverage. Preserve existing captures and correct insufficient coverage with a new broader full-run timeline first, under the policy below.
  - **Prefer one complete run over point captures**: The default evidence source is a start-to-end timeline with the starter 8 MiB memory region at every 1–2-second snapshot, adjusted only for verified mappings/RAM needs. If an earlier run used an insufficient region such as 1 MiB, prepare a new full-run timeline with corrected coverage. Do not turn a memory-size mistake into repeated per-routine breakpoint/capture requests. Preserve the earlier session and analyze the broader run offline across later steps.
  - **Targeted captures are exceptional**: Request one only when the human explicitly asks for it, or after auditing an adequately sized full-run session and demonstrating a concrete remaining question that cannot be resolved from its checkpoints, verified original files, or offline execution. Missing bytes in an undersized run are a reason to correct the full-run profile first. Explain why the full run is insufficient before preparing a separate [Targeted Capture Request](docs/templates/CAPTURE_REQUEST.md). A targeted profile may stop after an endpoint and must not replace the full-run timeline.
  - For guarded CALL/return capture, `pair_source.offset` is the callee entry after CALL, and `previous_offset` is the CALL instruction; the source must observe the four-byte stack push. `pair_return.offset` is the caller continuation after RET. For an `E8 rel32` pair, run `validate_capture_profile.py --purpose paired-targeted --call-bytes <verified-call-bytes> <profile>` and show PASS with captured-byte provenance before requesting a run. Other encodings need explicit review. If the call occurs too early for menu activation, instruct the human to pause at the verified caller CALL, start capture while paused, then resume; never operate the debugger yourself.
  - The human selects the JSON, launches the demo manually, then chooses **Debug → Automatic capture → Start** while it runs. The human provides the new session under `oracle/extract/`.
- **Offline Unicorn is Allowed**:
  - Executing original machine code inside offline Python scripts using the `unicorn` engine on captured memory dumps is fully permitted and encouraged.

---

## 2. Evidence Hierarchy & No Hallucinated Claims

1. **Original Bytes are Truth**: The disassembled `.asm` listing is an analyst's hypothesis. Misclassified data, missed jump tables, and wrong function boundaries are common in DOS demo disassemblies. Always cross-check against raw captured bytes.
2. **Never Conflate Evidence Classes**:
   - Resembling a screenshot $\neq$ Correct execution.
   - Passing an offline Unicorn test $\neq$ Validating the entire demo.
   - Fast browser frame rate $\neq$ Original hardware fidelity.
   - Always state the evidence class in your reports.
3. **Never Synthesize or Fake Frames**:
   - Every single intro frame shown by the player must be generated live by translated JavaScript code.
   - Never capture screenshots or video and play them back as an animation.
4. **Routine Checks Must Identify Their Input Evidence**:
   - A synthetic-fixture match is a useful algorithm test, but does not complete the tutorial's real-input routine milestone. Compare original captured code and JavaScript on real demo input from captures or verified original-file bytes, with a justified initial state. Record input provenance, compared outputs/registers/flags/memory effects, exclusions, and results; an output-buffer hash alone does not prove all state matches.
   - Check required memory ranges before replay. A mid-routine snapshot is not a function-entry state: resume the captured interval or justify reconstructing entry state. Never silently zero-fill missing dependencies and report a real-input pass.
   - Resume a real mid-routine checkpoint through a bounded interval offline when appropriate; the original code in Unicorn supplies the reference for JavaScript. A live entry/return pair or instruction trace is not required for the routine milestone. Do not demand new boundary captures merely because the periodic checkpoint is inside a routine.
   - If dependencies are missing, inspect all suitable full-run checkpoints and originals or choose another suitable interval first. If the run's memory coverage was insufficient, prepare a corrected full-run timeline (normally 8 MiB at every snapshot). Only escalate to targeted capture under the exception rule above. Preserve earlier capture sessions, clearly distinguish replacement profiles, and keep the milestone incomplete until the real-input check passes.

---

## 3. Tooling Usage Rules

1. **Assembly Listing Navigation (`asm_index`)**:
   - Never grep or read the entire 40–100 MB disassembly listing into context.
   - Always query the SQLite index:
     ```powershell
     python tools/asm_index/asm_index.py function <symbol>
     python tools/asm_index/asm_index.py callers <symbol>
     python tools/asm_index/asm_index.py callees <symbol>
     python tools/asm_index/asm_index.py refs <symbol>
     python tools/asm_index/asm_index.py context <address> --radius 12
     ```
   - Inspect an existing index's source hash, schema version, and instruction count before reusing it. If a schema-v1 index omitted addressless IDA instruction lines, build a new schema-v2 database at an unused path. Preserve the old database and annotations. Pass the chosen new index with `--db` on later queries so default discovery cannot select the old one. Keep unknown instruction addresses null.
2. **Preserve Immutable Files**:
   - Never overwrite files in `original/`.
   - Never overwrite capture sessions in `oracle/extract/`.
   - Never overwrite existing `.sqlite` index files containing analyst annotations.
3. **Place Analyst Exports by Evidence Class**:
   - Save the IDA disassembly listing under `oracle/` with a descriptive `.asm` filename, then index that exact path without reading the whole listing into context.
   - Use code and data-segment dumps already present in `oracle/extract/<session_id>/`; do not ask the human to export or disassemble the captured data segment again. Keep those sessions immutable. Open a working copy of a captured code image in IDA so database sidecars stay outside the capture session.
   - Place only separately supplied IDA or debugger memory dumps in `oracle/inputs/` with source, selector, starting offset, and size recorded. A selector number is not a proven linear base.
4. **Discover Workspace Paths Yourself**:
   - Inspect `original/` for the executable and companion files, `oracle/` for the IDA `.asm` listing, and `oracle/extract/` for capture sessions. Use manifests, hashes, and timestamps to identify the relevant session; do not guess from a folder name alone.
   - Do not require the human to type an executable filename, listing path, or session ID when the files are already in the workspace. Ask only when multiple plausible inputs remain after inspection or a required file is absent.

---

## 4. End-of-Session Handoff Protocol

At the end of every significant work session:
1. Update `docs/TASK_QUEUE.md` with current task status.
2. Create or update `docs/AGENT_HANDOFF.md` with:
   - What was accomplished and verified.
   - Runnable commands to reproduce results.
   - Known blockers and open questions.
   - One concrete next command or action for the next agent.

## 5. Tutorial Outcomes

This is an automatic framework requirement, independent of the wording of the human's prompt. It applies to short messages such as “Resume Step 06” or “The capture is ready.” Never require the human to repeat reporting rules or request a continuation decision. On resuming after a framework refresh, read the current instructions and outcome protocol, recover the active step from conversation and existing artifacts, and apply them without restarting completed work.

For every tutorial step and follow-up, follow [the outcome protocol](docs/guides/tutorial-outcomes.md). Begin the response with `STEP NN — COMPLETE`, `STEP NN — ACTION NEEDED`, or `STEP NN — INCOMPLETE`, provide brief evidence, and end with `You can continue to Step MM.` only when the whole step's criteria and required human review are met. Otherwise end with `Stay on Step NN. Next: [You or Agent] — [one concrete action].` Use actual numbers and actions. For completed Step 10, say `Tutorial complete. You can proceed to your release decision.` Record the step/status in the queue and handoff. Continue available authorized offline work; after a human capture or review, resume the same step without requiring a fresh prompt or paths. A prepared capture, synthetic fixture, or inventory alone cannot complete Step 06.

## 6. Visual and Audio Work Order

After the first live frame (Step 07), default to full graphics (Step 08), then sound/synchronization (Step 09). Honor sound-first if the human prefers it, using 07 → 09 → 08 → 10. Remember the preference and track visual/audio completion separately. Sound may remain pending while the full graphical sequence is built; it is not a prerequisite or a completed task. Use an explicit replaceable simulation clock based on recovered timing, and recover music-driven control events as needed without requiring audible replay. After integration, check the full timeline with sound before Step 10. Route continuation to the unfinished milestone, not automatically to the next number. When adopting the reordered tutorial, reconcile older 08/09 records by their actual artifacts and preserve completed work.

## 7. Reusable Validation and Production Adapters

- Follow [the validation ladder](docs/guides/validation-ladder.md): real-input routines across suitable checkpoints, dependent intervals, scenes including their endings, inherited transitions, then the actual browser canvas/controls. Reuse full-run captures offline. Do not infer whole-scene or browser correctness from one routine check.
- Use explicit comparison contracts with `differential_compare.py --contract`. Required observations, initial-state identity, successful endpoints, and complete ordered-write evidence where requested must be present. `INSUFFICIENT_EVIDENCE` is not PASS. Define observable registers/flags/output ranges and justify exclusions before accepting results; optimized semantic ports need not preserve dead temporaries or unobservable store granularity.
- Triage formats/packed assets and verify loader relocation. Use bounded index queries and `compare_routines.py` to find candidate engine copies; normalized similarity is not semantic proof. Share only variants whose address layouts, rounding, aliases, and other differences have been verified on real inputs.
- The generic player contract is reset/advance-to-time/live render with production-defined geometry and timing. Use `templates/player-template/README.md`; the default unconfigured adapter must fail clearly. The opt-in infrastructure fixture is never production evidence. Production frames and transition handoffs must come from translated original algorithms, not captured pictures or the development oracle.
- Verify the actual browser player, pause, seek/resume, transitions, endings, and original-code audio output. Measure the page's frame/worker/seek/transition behavior before optimizing. Checkpoint size, speed, and spacing are measured production choices, not universal guarantees.
- Keep original-execution, controlled-schedule scene equivalence, captured timeline timing, browser integration, and performance evidence distinct. Missing CPU/FPU/device support requires a verified offline adapter; never invent state or treat a failing adapter as a reason for automatic point captures.

## 8. Original-Code Sound Only

Translate and validate the production's original replay, sequencing, mixing, synthesis, and/or device-control code as applicable, using original sound data. Do not substitute libopenmpt, another module-player library, a generic replacement synthesizer, or recorded music. Tracker formats are examples, not a framework assumption; preserve custom drivers, hardware-based sound, arbitrary voice counts, or verified silence. Required device adapters must be driven by original code and separately validated. Web Audio is the output transport, not a substitute player. Infrastructure fixture audio tests transport only and must remain explicitly labeled. Record provenance, state/PCM or device-event comparisons, timing, and fidelity limits.

## 9. Playback Timing and Capture Validation

- Default to smooth live playback driven by recovered animation/music time. Capture sampling intervals and draw completions in an underclocked emulator are reference observations, not automatic player frame-rate limits. Keep capture-schedule matching as an explicitly selected validation mode; never silently make it the production default because hashes match there.
- Distinguish the original logical timer, any draw-dependent simulation updates, and browser presentation. Do not infer draw frequency from timer frequency, fixed CPU cycles, screenshot spacing, or how long the emulator took to rasterize. No universal tick/draw rate is prescribed. Record every chosen rate as recovered, measured, or provisional, with its evidence and a concrete verification task.
- Stateful drawing (feedback, trails, frame counters, palette accumulation, etc.) belongs in the logical simulation at an evidence-backed cadence. Preserve those updates even when their images are not presented. Extra redraws or repeated advance-to-the-same-time calls must not advance state; monitor refresh and dropped presentations must not change the effect.
- Compare capture-matching and smooth playback evidence separately, aligning by justified logical counters/state as needed. A provisional smooth draw schedule may support ongoing visual development, but must not be reported as verified original timing. Confirm transitions/duration/audio anchors independently; neither a high RAF count nor smooth appearance proves the logical cadence is correct.
- Test presentation-cadence independence and same-time redraws under the player contract, with explicit state checks where needed. Generate intermediate frames with translated original algorithms; do not blend/replay captured screenshots or invent interpolation as a fidelity shortcut. Analyze the existing full run and original timing code before considering additional human captures.

## Standard Step 10 release

Follow [the canonical release player standard](docs/guides/release-player-standard.md) and templates/player-template. Keep the canonical landing/player shell, a live module pattern grid driven by the original replay cursor, and measured FPS consistent across ports; adapt metadata/palette/source-specific adapters only. Use exactly one release/ directory, updated in place. Require real pointer/keyboard navigation tests, graphics+audio seek completion, both entry routes, live darkened first-animation landing background, full-run integration and human packaged review. Do not copy another demo's timing, channel count or format. Do not claim a pending harness passed. Framework maintenance itself is not a completed production tutorial step.
