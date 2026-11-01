# Agent Session Handoff

*Copy this file to `docs/AGENT_HANDOFF.md` and update it at the end of every work session.*

## 1. Current State & Milestone

- **Date**: YYYY-MM-DD
- **Active Task**: `S...` (see [TASK_QUEUE.md](TASK_QUEUE.md))
- **Tutorial Step & Outcome**: Actual tutorial number 00–10 (distinct from the `Sxx` task IDs); COMPLETE / ACTION NEEDED / INCOMPLETE under [the outcome protocol](guides/tutorial-outcomes.md).
- **Work Order & Independent Milestones**: Visuals first (default) / sound first; Step 08 full graphics, Step 09 audio, and full integrated playback status. Deferred work remains pending; preserve verified artifacts when migrating older 08/09 numbering.
- **Validation Coverage**: Contract/suite paths, checkpoints and covered stages, first mismatch, exclusions, CPU/device adapter limits, and browser integration status. Separate controlled-schedule evidence from observed playback timing.
- **Original Sound Provenance**: Original replay/mixer/synthesis/device routines translated and tested; original input sources; remaining fidelity limits. A library/module player is not an accepted substitute.
- **Tutorial Continuation Decision**: “You can continue to Step MM.” only if complete; otherwise “Stay on Step NN.” with one concrete next action and owner. Preserve the active step across capture/review follow-ups; use actual numbers.
- **Current Milestone Status**:
  - Summarize what was accomplished this session.
  - State which scenes, routines, or subsystems are now functioning.

## 2. Invariants & Rules for the Next Agent

- **DO NOT automate DOSBox / DOSBox-X**: Live emulator operation is reserved for the human user.
- **DO NOT use pre-rendered video or fake frames**: All graphics must be computed live by translated JavaScript code.
- **DO NOT dump raw 40+ MB disassembly listings into LLM context**: Query the SQLite database with `python tools/asm_index/asm_index.py`.
- **DO NOT overwrite immutable evidence**: Never modify files in `original/`, `oracle/extract/`, or existing `.sqlite` databases containing analyst annotations.

## 3. Verified Artifacts & Reproducible Commands

List runnable commands to reproduce the latest findings:

```powershell
# Query assembly index
python tools/asm_index/asm_index.py function <symbol>

# Run offline Unicorn golden reference
python tools/oracle/unicorn_runner.py ...

# Run differential verification
python tools/oracle/differential_compare.py ...
```

## 4. Known Blockers & Unresolved Questions

- State any hardware accesses (e.g. unknown interrupt vectors, unmapped ports, self-modifying code).
- State any missing emulator captures or low-memory address requirements.

## 5. Next Immediate Concrete Action

- [ ] Exact command, file to edit, or routine to translate next.

## Step 10 standard release record

- Canonical UI version: release-player-standard v1; package: release/ only.
- Landing live animation/dark overlay/credits, actual timeline pointer+keyboard checks, both root/player routes and responsive/fullscreen controls: pending.
- Measured FPS and original replay module grid or truthful non-module diagnostics: pending.
- Independent frames, graphics/audio restore+forward checks, full-run audio/visual synchronization and page/worker/seek performance: pending (record commands and evidence).
- Manifest/development-route audit and exact deploy checklist: pending.
- Final packaged human review: pending; publication human-owned.
