# Guide: DOSBox-X Custom Capture Setup & Procedures

The porting framework relies on a **special, instrumented version of DOSBox-X** provided alongside the project. This custom build contains an internal **Automatic Capture** module capable of taking periodic or event-driven snapshots of the running demo without manual debugger pausing.

---

## 1. What the Custom DOSBox-X Captures

At each capture interval (normally every 1,000 milliseconds of emulated time), the emulator exports a snapshot directory. Large assets can use a slower cadence:

| Artifact | File Name | Description |
|---|---|---|
| **Capture Manifest** | `capture.json` | Metadata: emulated timestamp (microseconds), CPU mode, cycle mode, configured cycles, asset list. |
| **CPU Registers** | `registers.json` | GPRs (EAX..EIP), EFLAGS, segment registers (CS, DS, ES, SS, FS, GS), CR0, GDTR, IDTR. |
| **Machine State** | `machine_state.json` | Full segment descriptor tables (bases, limits, attributes), GDT/IDT base & limit. |
| **VGA State** | `vga_state.json` | CRTC registers, Sequencer, Graphics Controller, Attribute Controller, and the 256-color DAC palette. |
| **Screenshot** | `screenshot.png` | PNG image of the displayed screen at that exact microsecond. |
| **Framebuffer** | `framebuffer.bin` | Raw video memory dump (e.g. 64,000 bytes for Mode 13h 320×200). |
| **RAM Dump** | `memory_main.bin` | Memory block exported from the configured selector. The starter profile requests 8 MiB at every snapshot; audit mapping and readability. |
| **Session Metadata** | `../session.json` | Master session summary: total captures, reason for stopping (e.g. process exit), total elapsed time. |

---

## 2. Configuration Profile (`autocapture-config.json`)

The custom DOSBox-X reads a JSON configuration profile to govern its capture behavior. A starter profile is provided in [docs/templates/autocapture-config.template.json](../templates/autocapture-config.template.json).
For the first pass, copy that timeline profile and change only the output path, observed selectors, memory sizes, and cadence needed for this demo. Do not turn it into a two-address endpoint capture.

### Key Configuration Settings

```json
{
  "version": 2,
  "output_directory": "oracle/extract",
  "trigger": {
    "type": "emulated_time",
    "interval_ms": 1000,
    "initial_delay_ms": 0
  },
  "process": {
    "mode": "current_or_next",
    "on_exit": "stop"
  },
  "assets": {
    "registers": { "enabled": true, "every_n_captures": 1 },
    "screenshot": { "enabled": true, "format": "png", "every_n_captures": 1 },
    "machine_state": { "enabled": true, "every_n_captures": 1 },
    "vga_state": { "enabled": true, "include_palette": true, "every_n_captures": 1 },
    "framebuffer": { "enabled": true, "every_n_captures": 1 }
  },
  "memory": [
    {
      "name": "main",
      "segment": "0008",
      "offset": "00000000",
      "length": "00800000",
      "every_n_captures": 1
    }
  ],
  "reference": {
    "enabled": false,
    "expected_cycles": 0,
    "trace_instructions": false
  }
}
```

### Critical Fields:
1. **`trigger.interval_ms`**: Set to `1000` for 1-second sampled snapshots across the demo, or `2000` for 2-second sampling. Do not use an hour-long interval for a timeline capture.
2. **`memory[].segment`**: The 16-bit selector to dump. In 32-bit protected mode, this is usually the primary code/data selector (for example `0008` or `0860`). If unsure, check `CS` and the other selectors the code uses in an initial run.
3. **`memory[].length`**: The template starts at `"00800000"` (8 MiB). Keep that starting size when appropriate for the available memory and selector; justify any reduction. Neither 4 MiB nor 8 MiB guarantees complete heap/stack coverage. Check bases, limits, available RAM, and required pointer ranges. If multiple selectors map the same range, duplicating it does not increase coverage.
4. **`memory[].every_n_captures`**: The starter value `1` dumps RAM at every 1–2-second snapshot alongside registers and screenshots. This supports offline replay from many checkpoints. Lower RAM frequency only with a documented evidence tradeoff; do not default to sparse RAM and compensate with repeated manual captures.
5. **`reference.enabled`**: Keep `false` for the first timeline pass to avoid instruction tracing overhead. Analyze the full run and resume bounded checkpoints offline first. Targeted reference tracing is an exception for a specific question the adequately sized full run cannot resolve. A `stop_after_capture` event deliberately ends that targeted session.

Before handing the first profile to the human, run:

```powershell
python tools/oracle/validate_capture_profile.py --purpose timeline autocapture-config.json
```

The validator must print **PASS**. A one-hour interval, an address stop event, or instruction tracing fails this gate. JSON syntax alone is not enough. Show warnings as well: PASS checks profile structure and timeline behavior, not whether all required memory is captured. Profiles with only regions smaller than the starter 8 MiB emit a size warning; a smaller region can be valid when justified.

### Memory coverage planning and review

**Default: one full run, reused offline.** Capture from the beginning through the end with adequate memory at every snapshot. An 8 MiB region is the normal starting point, with its selector mappings and readable ranges verified after capture. If the previous run only saved 1 MiB, fix that full-run profile rather than asking the human to hit individual addresses. Resume mid-routine checkpoints offline when useful; Unicorn can compute the reference endpoint without a live paired capture.

Targeted capture is allowed when explicitly requested by the human, or when the agent has audited an adequately sized full-run session and explains a concrete unresolved question that cannot be answered from it, verified originals, or offline execution. Missing memory in an undersized run alone does not justify this exception.

Before asking the human to capture, record each region's selector, offset, length, intended code/input/heap/stack coverage, and known or unverified base/limit. Use the initial debugger registers to flag pointers already outside the proposed region. When descriptors or total RAM are unknown, label the coverage provisional and ask the human to confirm the relevant DOSBox-X memory setting if needed; do not guess a selector's linear base from its number.

After capture, use `machine_state.json` and the memory asset metadata to verify actual mappings and statuses. For a base-zero selector, a dump starting at zero with length `00100000` covers offsets `00000000` through `000FFFFF`. A source pointer at `001C0DA4` is outside it, even if separate code and data dumps contain identical bytes. Capture the full required source range, not just the pointer's first byte. Record coverage gaps before indexing or selecting replay routines.

Check each memory asset for partial/unreadable bytes: the patched exporter can zero-fill unreadable memory and mark it partial. A file with the expected byte count is not proof that all its bytes were readable. Avoid blindly increasing the requested length beyond mapped/readable memory. Where possible, reduce redundant overlapping dumps or dump RAM less often rather than silently truncating required address ranges.

If an undersized timeline lacks required data, preserve it and prepare a new full start-to-end timeline with corrected coverage, normally the starter 8 MiB at every snapshot. Analyze that new full run before considering a targeted profile. Missing RAM does not invalidate the existing screenshots, but it can prevent offline replay. Choosing a larger future region cannot recover bytes from an earlier run; capture a new session if existing originals or captures cannot supply them.

---

## 3. Human Operator Procedure

> **Reminder**: AI agents NEVER launch or control DOSBox-X. The human developer runs this procedure.

### Step-by-Step Instructions:

1. **Copy the Configuration**:
   Copy [docs/templates/autocapture-config.template.json](../templates/autocapture-config.template.json) to your working directory as `autocapture-config.json` and adjust the `output_directory` path.
2. **Launch the Custom DOSBox-X**:
   Start the provided instrumented `dosbox-x.exe`.
3. **Configure Emulation Settings**:
   - Before starting capture or launching the demo, choose **CPU → CPU core → normal** in the DOSBox-X menu. Do not select **CPU → Normal speed**; that is a different control.
   - Choose **CPU → Edit cycles** and enter a practical fixed count (for example, `5000` as a starting point). Confirm that DOSBox-X shows fixed cycles. Record the value actually used; do not infer it from a debugger excerpt.
   - These settings are changed in the running DOSBox-X instance. A separate `dosbox-x.conf` is not required for this procedure. Recheck them after restarting DOSBox-X.
4. **Select the Capture Profile**:
   - In the DOSBox-X menu bar, choose **Debug → Automatic capture → Select configuration...** and select your `autocapture-config.json`.
   - Selecting the JSON does not start capture.
5. **Execute the Demo Manually**:
   - In the DOS prompt, navigate to your mounted drive and launch the demo executable:
     ```text
     C:\> DEMO.EXE
     ```
6. **Start Automatic Capture**:
   - While the demo is running, choose **Debug → Automatic capture → Start**. This attaches the capture session to the current demo process. Check **Status** to confirm it is active.
   - Let the demo continue. The timeline profile records every 1–2 seconds until the process exits or you choose **Stop**. Start promptly after launch so the opening is represented. Use its checkpoints for offline replay; an exact live routine-entry snapshot is not a default requirement.
7. **Capture Session Completion**:
   - After the demo exits, check **Debug → Automatic capture → Status**. If the capture is still active, choose **Stop**. Do this before closing DOSBox-X.
   - Confirm the session's `session.json` says `status: stopped`, has a stop reason, and reports the same capture count as the completed `capture_*` directories. A directory full of snapshots with `status: running` is an incomplete provenance record; do not report it as a finalized session.
   - The session directory appears under `oracle/extract/<timestamp>/`.
8. **Verify the Corpus**:
   Run the inventory tool to verify that all assets were exported cleanly:
   ```powershell
   python tools/oracle/inventory.py --session oracle/extract/<timestamp> --output oracle/reports/inventory.json
   ```
   Resolve or report its finalization warnings before using the session as complete timeline evidence.
