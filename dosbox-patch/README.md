# DOSBox-X Automatic Capture Patch

This directory contains the unified patch for **DOSBox-X** that adds the **Automatic Capture** feature used to extract regular periodic snapshots, full memory dumps, register states, and VGA data from running DOS demos.

---

## 1. Upstream Base Commit

- **Repository**: [https://github.com/joncampbell123/dosbox-x](https://github.com/joncampbell123/dosbox-x)
- **Base Commit SHA**: `0933a6fdff4cc3c56da692d449a96440a5710d6f`

This patch includes the two feature commits from branch `feature/automatic-capture`:
1. `225294ee8` — *automatic capture at regular interval*
2. `2fc3473bf` — *feat: improved auto capture*

Plus all subsequent working-tree refinements (passive PIC/PIT/keyboard event tracing, version 2 multi-cadence asset serialization, stack-frame context pairing, and VGA DAC palette capture).

---

## 2. What this Patch Adds to DOSBox-X

1. **Automatic Capture Core (`src/debug/autocapture.cpp`, `include/autocapture.h`)**:
   - Periodic capture triggers based on emulated time (`interval_ms`, e.g. every 1,000 ms).
   - Time spent pausing, writing to disk, encoding PNGs, or dumping memory does **not** advance the emulated guest clock.
   - Session management: captures are stored in a timestamped folder with atomic staging (`.tmp` directories finalized only on completion).
2. **Exported Snapshot Assets**:
   - `registers.json`: Complete 32-bit CPU state (EAX..EIP, EFLAGS, CR0, GDTR, IDTR, CS, DS, ES, SS, FS, GS).
   - `machine_state.json`: Global & Interrupt Descriptor Tables (GDT/IDT), cached selector descriptor bases, limits, and access attributes.
   - `vga_state.json`: Full VGA hardware state including CRTC registers, Sequencer, Graphics Controller, Attribute Controller, and 256-color DAC palette.
   - `screenshot.png`: Exact display raster at that microsecond.
   - `framebuffer.bin`: Raw video memory buffer.
   - `memory_main.bin`: Full physical/segmented memory block (e.g. 4 MiB or 8 MiB).
   - `session.json`: Master execution summary and final capture count.
3. **GUI Integration (`src/gui/menu.cpp`, `src/gui/menu_callback.cpp`)**:
   - Adds **Debug $\to$ Automatic capture** menu:
     - *Select configuration...*
     - *Start* (attaches to the running DOS program, or waits for the next one)
     - *Capture now* (manual one-off snapshot)
     - *Status* (shows tracked PSP, elapsed guest time, and next capture deadline)
     - *Stop* (finalizes the session and flushes pending writes)
4. **Passive Event Tracing**:
   - Non-intrusive logging of IRQ activations/deliveries, I/O port dispatches (`IN`/`OUT`), BIOS timer callbacks, and video mode switches.

---

## 3. How to Apply the Patch

Clone the official DOSBox-X repository, checkout the starting commit, and apply the patch:

```bash
# 1. Clone the DOSBox-X repository
git clone https://github.com/joncampbell123/dosbox-x.git
cd dosbox-x

# 2. Checkout the verified base commit
git checkout 0933a6fdff4cc3c56da692d449a96440a5710d6f

# 3. Create a branch and apply the patch
git checkout -b feature/automatic-capture
git apply /path/to/dosbox-patch/dosbox-x-autocapture.patch
```

---

## 4. Building the Patched DOSBox-X

### On Windows (Visual Studio)
1. Open `vs/dosbox-x.sln` in Visual Studio 2022 (or 2019).
2. Select build configuration: **Debug** (or **Release**), platform **x64**, SDL version **SDL2**.
3. Build the solution. The output binary will be located in `bin/x64/Debug SDL2/dosbox-x.exe`.

### On Linux
```bash
./autogen.sh
./configure --enable-debug --enable-sdl2
make -j$(nproc)
```

---

## 5. Usage with the Porting Framework

1. Copy the template capture configuration from [`docs/templates/autocapture-config.template.json`](../docs/templates/autocapture-config.template.json) to your project workspace.
   The starter profile samples every second and continues until process exit or manual Stop. Use a separate targeted profile for instruction tracing and `stop_after_capture` events.
2. In the patched DOSBox-X, open **Debug $\to$ Automatic capture $\to$ Select configuration...** and pick your JSON profile.
3. Run your demo executable (`DEMO.EXE`) manually.
4. While the demo is running, choose **Debug → Automatic capture → Start** and check **Status**. The session attaches to the current process; a trigger reached before Start will not be captured.
5. After the demo finishes, check **Status** and choose **Stop** if capture is still active. Confirm `session.json` says `stopped` and its capture count matches the completed capture directories, then verify the session using the inventory tool:
   ```powershell
   python tools/oracle/inventory.py --session oracle/extract/<timestamp>
   ```
