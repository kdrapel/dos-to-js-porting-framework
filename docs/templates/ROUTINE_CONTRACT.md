# Routine Contract: <Symbol / Hex Address>

## Identity & Provenance

- **Coordinate System**: Selector:Offset (`0008:0001ABCD`), Linear Base (`0xB9C0`), Runtime Linear (`0x0002658D`)
- **IDA Disassembly Symbol**: `sub_1ABCD` or labeled procedure
- **Code Extent & Bytes**: `<len>` bytes, SHA-256 `<hash>`
- **Source Capture**: Capture ID, memory dump hash, observed caller address
- **Evidence Class**: Disassembly-reviewed / Unicorn-exercised / Differential match
- **Input Evidence**: Real demo input / synthetic fixture. Record the source capture or original file, byte range, hash, and any recovery steps. Keep synthetic-fixture results separate from the real-input milestone.
- **Comparison Contract & Coverage**: Link the explicit comparison JSON and list suitable real checkpoints/phases exercised; expand from the first passing case to different branches and endings. Record CPU/device adapter versions and whether any timing schedule is controlled.

## Execution Boundary Contract

- **Entry Address**: Hex offset
- **Natural Exit / Stop Address**: Hex offset (e.g. Stop before `RET` or frame completion)
- **Calling Convention & Stack**:
  - Registers passed (e.g., EAX = count, ESI = src, EDI = dst)
  - Stack arguments layout
  - Expected ESP delta upon exit (e.g. `RET` vs `RET 4`)
- **Required CPU / FPU State**:
  - Segments (CS, DS, ES, SS, FS, GS)
  - FPU Control Word (CW), Tag Word, TOP, live registers ST(0)..ST(n)
- **Input Memory Dependencies**:
  - Readable memory buffers, lookup tables, global variables
  - Verify every required read range is available; list missing ranges explicitly. Do not silently substitute zero-filled bytes.
- **Initial State Provenance**:
  - Entry capture / resumed mid-routine capture / justified reconstruction
  - Explain reconstructed registers, stack, and memory; do not move EIP back to entry while treating evolved register values as entry values.
- **Hardware Prerequisites**:
  - None (leaf routine) / PIT / VGA / DMA / Interrupts

## Behavior & Algorithmic Contract

- **Derived Algorithm**: Summary of the mathematical or graphic operation
- **Modified Memory Ranges**: Buffer writes, stack scratch variables
- **Modified Output Registers / Flags**: Return values (EAX), modified flags (CF, ZF, etc.)
- **Precision / Arithmetic Constraints**:
  - Integer wrap, 32-bit signed vs unsigned
  - Floating point: 24-bit vs 53-bit vs 64-bit precision, rounding mode, signed zero
- **Exceptional / Edge Cases**:
  - Zero count, clipping boundaries, NaN/infinity handling

## Validation & Differential Verification

- **Real-Input Milestone Status**: Incomplete / passed. A synthetic fixture alone leaves it incomplete.
- **Tutorial Step 06 Outcome**: COMPLETE / ACTION NEEDED / INCOMPLETE, following [the outcome protocol](../guides/tutorial-outcomes.md). Record the next action and owner while incomplete. Only a completed real-input milestone permits the agent to say “You can continue to Step 07.” After a requested capture arrives, resume verification and comparison; do not end the step at session inventory.
- **Compared State & Exclusions**: List exact output ranges, relevant registers/flags, and memory effects checked. An output hash alone verifies only that output range. Explain any excluded state.
- **Missing Evidence Recovery**: Search full-run checkpoints and verified originals or choose another suitable interval. If the previous run's memory was undersized, prepare a new start-to-end timeline with corrected coverage, normally 8 MiB at every snapshot, preserving the old session. Analyze that run before requesting a targeted capture; the targeted exception requires a specific question the adequately sized full run and offline replay cannot resolve, or an explicit human request.
- **Offline Interval Choice**: A captured mid-routine state may be resumed in both Unicorn and JavaScript to a bounded stop. A live paired entry/return capture or instruction trace is not required to complete this real-input routine milestone.
- **Reference Offline Execution**:
  ```powershell
  python tools/oracle/unicorn_runner.py --entry 0x1ABCD --stop 0x1ABEF ...
  ```
- **JavaScript Translation Runner**:
  ```powershell
  node js/test_sub_1ABCD.mjs ...
  ```
- **Differential Verification Tool**:
  ```powershell
  python tools/oracle/differential_compare.py --contract oracle/comparison-contract.json --reference ref.json --js js.json
  ```
- **State Invariants Verified**:
  - [ ] All general-purpose registers match
  - [ ] Arithmetic flags match (CF, ZF, SF, OF, PF, AF)
  - [ ] Full memory hash / dirty page byte match
  - [ ] Memory write trace ordering agrees

Check only the observables declared in the contract and clearly mark unchecked fields. Do not demand instruction-level write order from a bulk semantic translation unless that ordering is observable. `INSUFFICIENT_EVIDENCE` is not a match. See [validation ladder](../guides/validation-ladder.md) for batch checkpoint replay, first-byte diagnostics, and scene/browser integration checks.
