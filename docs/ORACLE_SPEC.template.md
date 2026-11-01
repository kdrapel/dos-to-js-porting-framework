# Oracle Specification & Evidence Contract

The oracle is an offline verification harness for explicitly declared behavior on tested inputs. It supplies evidence within its CPU/device/timing limits; it does not automatically guarantee a whole production is correct.

---

## 1. Hierarchy of Evidence Classes

Never conflate different degrees of certainty. Every test and document must state its evidence class:

| Class | What it Proves | What it Does NOT Prove |
|---|---|---|
| **Original Executable Bytes** | Authentic release bytes and static resources. | Runtime memory layout, unpacked code, or timing. |
| **IDA Disassembly & SQLite Index** | Analyst navigation and disassembler interpretation. | Code reachability, function boundaries, or self-modifying code. |
| **DOSBox-X Capture Snapshot** | CPU and memory state at that specific captured microsecond. | Continuous execution flow or instruction retirement history. |
| **Offline Unicorn Execution** | Exact behavior of original machine code for a bounded interval. | Real DOSBox-X execution or real hardware timing automatically. |
| **Differential JS-vs-Unicorn Test** | Semantic equivalence of translated JS for tested inputs. | Correctness of entire demo or untested branch paths. |
| **Screenshot Comparison** | Overall visual likeness and approximate color. | State equality, memory preservation, or audio fidelity. |
| **Browser Benchmark** | Performance and frame rate on the host browser/hardware. | Original demo speed or hardware timing accuracy. |

---

## 2. Memory and Segment Coordinates

Before lifting instructions, define and verify the relationship between coordinates:

```text
Linear Address = Segment.Base + Effective_Offset
Memory_File_Offset = Linear Address - Memory_Base
```

In 32-bit protected-mode DOS extenders (e.g. DOS/4GW, PMODE/W, CauseWay):
- CS, DS, ES, SS typically share a flat base (e.g. `0xB9C0` or `0x0000`).
- When base is non-zero, effective offsets match file offsets only if base subtraction is modeled.
- GS or FS may have a zero base to access real-mode BIOS interrupt vectors or low memory (`0x00000000 - 0x000004FF`).
- Paging may be disabled (CR0 bit 31 = 0), in which case guest linear addresses directly equal physical addresses.

**Gate Requirement**: Do not begin routine translation until at least three separate instruction fetch addresses and two data memory references have been verified against raw bytes from capture dumps.

---

## 3. Boundary Contract Requirements

Each verified routine must be isolated as a bounded contract:
1. **Entry Conditions**: Exact register values, stack pointer (ESP), segment bases, and input memory buffer hashes.
2. **Exit / Stop Condition**:
   - A justified return target and restored stack under the observed operand/stack mode (for example, a 16-bit near RET pops 2 bytes and a 32-bit near RET pops 4). Do not infer return solely from stack movement.
   - Stop-before address (execution halts before an external call or hardware interaction).
3. **Execution Limit**: Finite maximum instruction count (e.g. 100,000 instructions) to prevent runaway execution.
4. **Hardware Stubs**: Any port I/O (`IN`/`OUT`) or interrupt (`INT 10h`, `INT 21h`, `INT 33h`) must fail explicitly with structured diagnostics unless covered by an isolated, tested adapter.

---

## 4. Differential Comparison Requirements

Use a comparison-contract JSON and `differential_compare.py --contract`. Declare successful endpoints, required input identity, observable register/flag masks, exact memory ranges or complete memory, ordered writes where meaningful, and optional framebuffer geometry/RGBA. Missing observations or an unsuccessful endpoint yield INSUFFICIENT_EVIDENCE; declared mismatches yield FAIL; only sufficient matching evidence yields PASS.

Optimized semantic translations need not preserve dead registers, undefined flags, or unobservable write granularity. Record exclusions and their rationale before testing. An ordered-write contract requires complete digests over canonical address/size/value events; a count or truncated trace preview is not equivalent evidence. Unicorn hooks describe observed callbacks rather than instruction retirement.

Compare real states across phases and branches, then dependent intervals, scenes, transitions/endings, and the actual browser page. A controlled interrupt schedule is part of the test contract and does not prove the same timing as a DOSBox run. Required FPU/device state must be restored by a verified adapter or the case remains incomplete. See [validation ladder](guides/validation-ladder.md).

---

## 5. Floating-Point & x87 Contract

1. **Precision Control**: Observe the x87 Control Word (CW bits 8–9):
   - `00`: 24-bit single precision significand.
   - `10`: 53-bit double precision significand.
   - `11`: 64-bit extended precision significand.
2. **Avoid Double Precision Drift**: Standard JavaScript `Number` is 64-bit float (53-bit significand). If the original demo uses 24-bit rounding or 80-bit extended precision, tiny numerical differences compound over hundreds of frames, causing 3D objects or cameras to drift out of view.
3. **Use Exact Dyadic or BigInt Emulation**: For precision-critical matrix inversions or spline evaluators, use exact BigInt or explicitly rounded operations during verification.

---

## 6. Graphics Frame Validation

1. **VGA Surface Extraction**:
   - Check VGA controller registers from capture (Mode 13h 320x200, Mode X, or 320x400 tweaked).
   - Extract raw DAC palette (256 RGB triplets, 6-bit 0–63 scaled to 8-bit 0–255).
2. **Buffer Verification**:
   - Compare guest video memory (typically `0xA0000` or double-buffer work page in heap) byte-for-byte.
   - Compare final rendered 32-bit RGBA pixels and SHA-256 hash against the capture reference.
