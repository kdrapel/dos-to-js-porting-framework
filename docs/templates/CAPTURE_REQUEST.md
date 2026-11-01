# Targeted Capture Request: <Routine / Subsystem>

> **Note for Agents**: Agents NEVER operate, launch, or automate DOSBox or DOSBox-X.
> When dynamic emulator state is missing, prepare this procedure for the human user to execute.
> This template is for a later bounded question. The first capture must use the continuing 1–2-second timeline profile and pass `tools/oracle/validate_capture_profile.py --purpose timeline`.
> **Exceptional use only**: Prefer a full start-to-end run with adequate memory (normally 8 MiB at every snapshot), reused offline. If an earlier run was undersized, correct that full-run profile first. Use this targeted template only at the human's explicit request or after documenting a specific question that an adequately sized full run, verified originals, and offline replay cannot resolve.

## Objective

- **Unresolved Semantics**: State exactly what cannot be deduced from static disassembly or offline execution.
- **Existing Captures Analyzed**: List existing capture IDs checked and explain why they lack the required state.
- **Why Full-Run Evidence Is Insufficient**: Identify the adequately sized full-run session audited and the offline approaches attempted. Missing memory from a 1 MiB run alone is not justification for point capture. A mid-routine checkpoint is not itself a blocker: resume it offline where appropriate.
- **Missing State**: State specific register, vector, hardware port, or memory range needed.

## DOSBox / DOSBox-X Capture Configuration

- **Target Executable**: Path, size, and SHA-256
- **CPU Core**: `normal` (required for instruction-accurate boundary capture)
- **Emulated Cycles**: Proposed practical fixed count (e.g. `5000` to start); record the actual setting and do not present an unverified value as the original run's speed.
- **Human CPU menu actions**: Before launch, choose **CPU → CPU core → normal**, then **CPU → Edit cycles** and enter the proposed fixed count. Verify the actual setting in DOSBox-X; do not imply a separate config file is required.
- **Memory Dump Region**:
  - Selector, offset, length, and the descriptor base/limit evidence. The selector value alone is not a linear base.
  - Required read/write ranges: include the complete source buffers, tables, destination, and stack needed by the bounded interval. Check that pointers and their full accessed extents lie inside readable captured regions.
  - Explain any size reduction from the starter 8 MiB region; small targeted ranges are valid when they cover the question. Deduplicate only mappings proven to overlap. After capture, check asset status and unreadable-byte counts, not just file sizes.
- **Required Snapshot Assets**:
  - [x] Memory dump (`memory_main.bin`)
  - [x] CPU registers (`registers.json`)
  - [x] Machine state / GDT (`machine_state.json`)
  - [x] VGA state & palette (`vga_state.json`)
  - [x] Screenshot (`screenshot.png`)
  - [x] Framebuffer (`framebuffer.bin`)

## Trigger & Stop Conditions

### Guarded CALL/return profiles

This separate profile is intended to capture the two bounded endpoints, not the full timeline. A long periodic interval/delay can suppress unrelated timed snapshots while address events trigger immediately when matched; it is not a wait before the paired address captures. Never reuse that setting for the initial 1–2-second timeline profile.

`pair_source` is the first observed instruction boundary **inside the callee**, after CALL pushed its four-byte return address. Set its `offset` to the routine entry and `previous_offset` to the verified CALL instruction. Setting `pair_source` on CALL itself after a MOV will fail the patch's stack-delta guard (`reference_source_near_call_stack_mismatch`). The `pair_return` offset is the caller continuation after RET, with the caller's stack restored, `occurrence: 1`, and `stop_after_capture: true`. This guard supports a 32-bit near call and return without argument cleanup; verify those conditions from code and new capture metadata.

Before handing the profile to the human, verify the CALL encoding in captured bytes and run:

```powershell
python tools/oracle/validate_capture_profile.py --purpose paired-targeted --call-bytes E8FB0F0000 targeted-profile.json
```

The bytes above are an illustrative `E8 rel32`, not bytes to copy into another demo's check. The agent discovers and supplies the actual profile path and verified bytes, records their provenance, and shows PASS. The validator checks callee entry and caller continuation arithmetic against those supplied bytes. It does not prove live selector mappings, memory readability, or that the trigger will be reached. Other CALL encodings need a separately justified review.

- **Entry Trigger**:
  - Instruction address (CS:EIP / linear): `0x...`
  - Hit condition: Occurrence number or specific caller address:
- **Stop Trigger**:
  - Natural return (near RET / far RET)
  - Frame completion boundary (e.g. End of vertical retrace loop)
- **Trace Boundaries**:
  - Narrowly bounded to the routine in question (avoid unconstrained whole-demo instruction tracing).

## User Procedure

1. Set core and fixed cycles through the DOSBox-X CPU menu.
2. Choose **Debug → Automatic capture → Select configuration...** and select the prepared JSON.
3. Launch the demo manually at the DOS prompt.
4. While the demo is running, choose **Debug → Automatic capture → Start** and check **Status**.
   - If the target occurs too early to start capture through the menu, use the debugger to pause the running demo at the verified caller CALL instruction, start capture while paused, and resume. This lets the patch observe CALL followed by callee entry. Do not repeatedly rely on clicking faster or assume an already-passed trigger can fire retroactively. Only the human sets breakpoints and operates the debugger.
5. After the target or program exit, check **Status** and choose **Stop** if capture is still active. Confirm `session.json` says `stopped` and its count matches completed capture directories. Provide the resulting `oracle/extract/<timestamp>/` session to the agent, noting any target address reached before capture started.
