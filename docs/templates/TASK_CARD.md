# Task <ID>: <Concrete Bounded Outcome>

Status: planned / ready / in_progress / review / done / blocked

## Inputs and Scope

- **Input Paths & Hashes**:
  - `path/to/fixture`: SHA-256 `<hash>`
- **Addresses & Coordinate System**:
  - Entry CS:EIP or selector:offset:
  - Runtime linear address:
  - Segment base (e.g. `0xB9C0`):
- **Permitted File Edits**:
  - List exact paths this task may modify:
- **Dependencies Satisfied**:
  - Prerequisites (e.g., S02 address map verified):
- **Explicit Non-Goals**:
  - What is intentionally out of scope for this task:

## Work Description

Describe one bounded deliverable. Give existing commands and relevant indexed symbols.
State which facts are proven and which are hypotheses. Do not require the recipient to
rediscover unrelated architecture or scan the entire 5,000-function disassembly.

## Acceptance Criteria

- **Required Output Artifacts**:
  - Validation report JSON, test script, or lifted module.
- **Exact Reproduction Command**:
  ```powershell
  python tools/oracle/replay_suite.py --session oracle/extract/SESSION --plan oracle/replay-suite.json --output oracle/new-results
  ```
- **Verification Standard**:
  - Explicit comparison-contract path, declared observable state/ranges, justified exclusions, and successful stop conditions. Missing evidence never passes. Ordered writes are required only when the contract needs them.
- **Evidence Stage & Coverage**:
  - Routine / interval / scene / transition / browser; list real checkpoints/branches/endings exercised. Keep controlled interrupt schedules distinct from captured timing and browser performance.
- **Boundary Cases Tested**:
  - Positive, boundary, and deliberate failing negative tests.

## Return Report

When complete, record:
- Files changed.
- Commands executed and exact outputs.
- Established facts vs remaining unknowns.
- Concrete next action.
