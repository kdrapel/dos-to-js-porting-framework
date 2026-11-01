# Project Task Queue & Dependency Gates

Use this ordered task list to track reverse-engineering progress. Do not begin downstream tasks until their gating prerequisites are satisfied.

## Active tutorial step

The agent maintains this summary using [the tutorial outcome protocol](guides/tutorial-outcomes.md). Tutorial numbers 00–10 are distinct from the detailed `Sxx` task IDs below.

- **Tutorial step**: Record the current tutorial number.
- **Outcome**: COMPLETE / ACTION NEEDED / INCOMPLETE.
- **Preferred work order**: Visuals first (default) / sound first; preserve the human's stated choice.
- **Visual/audio milestones**: Track Step 08 full graphics and Step 09 audio independently, plus the full integrated playback check. Deferred work remains pending. Route to the unfinished milestone before Step 10.
- **Evidence and remaining requirements**: Link the results; name any pending human review.
- **Next action and owner**: One concrete action by You or Agent.
- **Continuation decision**: “You can continue to Step MM.” only if complete; otherwise “Stay on Step NN.” followed by the next action. Use actual step numbers.

## Detailed tasks

| ID | Milestone / Task | Depends On | Concrete Acceptance Criteria | Status |
|---|---|---|---|---|
| **S00** | Original inventory & first debugger excerpt | — | Original files hashed; human-supplied CS, registers, and nearby disassembly recorded. | [ ] |
| **S01** | Initial timeline capture & provenance audit | S00 | 1–2-second profile passes `validate_capture_profile.py --purpose timeline`; human supplies session; `inventory.json` confirms `session.json` stopped with matching count and records cadence, hashes, and warnings. | [ ] |
| **S02** | Coordinate and address mapping proof | S01 | Segment bases and file offset formula proven with 5+ byte checks. | [ ] |
| **S03** | Capture suitability audit | S01 | Trace completeness, CPU cores, and snapshot suitability cataloged. | [ ] |
| **S04** | Discover real reachable runtime code | S02 | Disassembly indexed when available; execution paths from captured EIP identified; misclassified data excluded. | [ ] |
| **S05** | Build first offline Unicorn interval runner | S02, S03, S04 | Leaf routine executes to natural boundary in Unicorn; produces state dump. | [ ] |
| **S06** | First JavaScript baseline & differential comparator | S05 | Real-input JS comparison passes an explicit contract with successful endpoints and required state/ranges; missing observations cannot pass. Expand across suitable checkpoint phases. | [ ] |
| **S07** | x87 FPU semantics inventory & first routine | S06 | If x87 is used, a verified adapter/routine matches required CW/rounding/precision; otherwise document evidence that this milestone is not required. | [ ] |
| **S08** | Screenshot atlas & provisional scene ledger | S01 | Contact sheets generated; cut points and scene intervals identified. | [ ] |
| **S09** | Discover main loop, scene dispatch & timers | S04, S08 | Master dispatcher, timer interrupt handlers, and scene switches mapped. | [ ] |
| **S10** | Discover & extract native music data | S04 | Actual sound data, replay/synthesis/device-control code, and timing identified; recover patterns/samples only where applicable, or establish verified silence. | [ ] |
| **S11** | Extract geometry, textures & palette tables | S04, S09 | 3D meshes, bitplanes, and palettes extracted into `oracle/assets/`. | [ ] |
| **S12** | Translate first shared graphics primitives | S06, S07, S11 | Inner span rasterizers or projection kernels match reference execution. | [ ] |
| **S13** | First complete JS-rendered frame | S09, S12 | Live frame presented with geometry/palette and declared reference comparison checked; evidence, timing limits, and differences recorded for human review. | [ ] |
| **S14** | First continuous short scene in browser | S13 | Multi-frame sequence executes smoothly in minimal canvas preview. | [ ] |
| **S15** | Tracker / control replay baseline | S05, S10 | Original replay/sequencing/synthesis or device-control code matches declared real-state/observable contracts; no replacement module library. | [ ] |
| **S16** | Native software sample mixer | S15 | Original mixing or required device adapter produces tested PCM/events at the output rate; chunk/loop boundaries verified where applicable. | [ ] |
| **S17** | Audio master clock & timeline synchronization | S14, S16 | Recovered visual and original sound clocks integrated, full-run sync checked and limits recorded; verified silent productions use the recovered visual clock. | [ ] |
| **S18** | Remaining scenes & transitions | S14, S09 | All visual groups translated; continuous graphical playback with explicit simulation timing. Audio may remain pending. If audio exists, check integrated playback. | [ ] |
| **S19** | Performance profiling & kernel optimization | S14, S18 | Actual browser/worker timings meet the production target; only measured bottlenecks optimized, with comparison regressions rerun. | [ ] |
| **S20** | State checkpoints & fast timeline seeking | S17, S18 | Measure replay-based seeking first; add complete-state checkpoints only if needed and compare restore/forward with uninterrupted playback. Record size and latency. | [ ] |
| **S21** | Web player UI & responsive presentation | S14 | Gate overlay, HUD controls, fullscreen API, and dark styling. | [ ] |
| **S22** | Diagnostics & "Stats for nerds" overlay | S17, S20, S21 | Actual page/worker/frame/seek metrics and original sound diagnostics where available; no assumed tracker/voice count or fake telemetry. | [ ] |
| **S23** | Original startup & shutdown handling | S09, S18 | Demo starts from clean state and handles natural ending/cleanup. | [ ] |
| **S24** | Standalone shipping package audit | S17, S18, S20–S22 | Full visual/audio integration checked; static package verified: zero external dependencies, no oracle leaks. | [ ] |
| **S25** | Public documentation & README | S18, S24 | Credits, live demo link, technical explanations, and screenshots. | [ ] |
| **S26** | Final acceptance certification | S19, S23–S25 | End-to-end full run passes all requirements without emulation. | [ ] |

## Step 10 standard release record

- Canonical UI version: release-player-standard v1; package: release/ only.
- Landing live animation/dark overlay/credits, actual timeline pointer+keyboard checks, both root/player routes and responsive/fullscreen controls: pending.
- Measured FPS and original replay module grid or truthful non-module diagnostics: pending.
- Independent frames, graphics/audio restore+forward checks, full-run audio/visual synchronization and page/worker/seek performance: pending (record commands and evidence).
- Manifest/development-route audit and exact deploy checklist: pending.
- Final packaged human review: pending; publication human-owned.
