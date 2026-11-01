# Quickstart: From DOS to the Browser

Start with **[tutorial.html](tutorial.html)**: open it in your browser for the illustrated guide and copy buttons. This is its text companion, with the same steps, agent prompts, reviews, and completion criteria.

You need the original DOS demo archive, an AI coding agent, IDA, and patched DOSBox-X. Windows users can use [the precompiled patched build](dosbox-release/patched-dosbox-x.exe).

You operate DOSBox-X and IDA and review results; the agent discovers workspace paths, analyzes captured evidence, translates code, and runs offline checks. Follow the steps in order and send each prompt when indicated. Continue only when the agent confirms completion; otherwise supply its requested result and stay on the same step. See [completion criteria](docs/guides/tutorial-outcomes.md).

---

## Step 00: Copy the framework and unpack the demo

Prepare a dedicated workspace containing the framework and the complete original demo.

- **You:** Copy or check out the complete framework into a folder dedicated to the demo.

- **You:** Create `original/` at its root and extract the full demo archive there. Open this framework copy as the agent’s workspace.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 00. This framework copy is the workspace for porting the demo in original/. Read AGENTS.md, discover and triage the executable and companion files there, preserve every original, initialize the port task queue, and report genuinely missing inputs. Identify packed/overlay candidates without treating signatures as verified formats. Ask me for the demo’s display name only if the files do not make it clear. Work in this workspace. Do not invent captures or disassembly.
```

- **Agent:** Discovers the executable and companion files and initializes the task queue.

- **You:** Check that the agent found the intended demo. Tell it if the identity is wrong or required files are missing.

- **Agent — outcome:** Says “You can continue to Step 01.” only when it has identified the intended demo and resolved required missing inputs. Otherwise says “Stay on Step 00” and gives the next action. Reply with any requested result so the agent can finish this same step.

**Notes**

The dedicated folder contains the full framework: `tools/`, `templates/`, `docs/`, and the other framework files. Preserve subfolders from the demo archive; its executable may depend on nearby data files. Keep the archive too. Later captures belong in this workspace’s `oracle/extract/`.

---

## Step 01: Run the demo and copy the debugger text

This first emulator pass is entirely yours. The debugger text gives the agent the initial register state and code location.

- **You — in DOSBox-X:** Launch the demo from `original/` using the provided patched DOSBox-X.

- **You — in the debugger:** Break while the demo runs. Select and copy the text showing registers and nearby disassembly.

- **You — in the agent chat:** Paste that text. There is no separate prompt to send in this step.

- **Agent:** Identifies the observed code selector from `CS`, the current instruction, and other available register information.

- **You:** Check that the agent received the registers and nearby disassembly. Supply missing text if it requests it.

- **Agent — outcome:** Says “You can continue to Step 02.” only when it has the debugger registers and nearby disassembly needed to plan capture. Otherwise says “Stay on Step 01” and gives the next action. Reply with any requested result so the agent can finish this same step.

**Notes**

`CS` identifies the active code segment selector. Together with `EIP` and the nearby instructions, it helps the agent plan which memory to capture and how to locate the running code. The agent does not operate DOSBox-X. See [DOSBox-X setup](docs/guides/dosbox-capture-setup.md).

---

## Step 02: Capture a timeline

Capture the demo from start to finish, including an 8 MiB memory region at every 1–2-second snapshot.

- **You:** Finish Step 01 and paste its debugger text to the agent before sending the prompt below.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 02. Use the debugger text and discovered original files to prepare a full start-to-end timeline capture, normally with 8 MiB at every 1–2-second snapshot. Follow AGENTS.md for coverage planning and validation, show PASS and any warnings, and give me exact DOSBox-X CPU/menu instructions. I will select the JSON, launch the demo manually, then start capture while it runs. Once I report the capture ready, discover the new session and audit its finalization, memory coverage, readability, and remaining gaps.
```

- **Agent:** Creates `autocapture-config.json` for a continuing 1–2 second timeline. Explains proposed CPU settings and memory ranges, justifies any reduction from the starter 8 MiB, and shows validator PASS and warnings.

- **You — in DOSBox-X:** Apply the CPU settings through the CPU menu. Select the JSON using **Debug → Automatic capture → Select configuration…**.

- **You — in DOSBox-X:** Launch the demo manually. While it runs, choose **Debug → Automatic capture → Start**. Let it run through the sequence you want to capture.

- **You — in DOSBox-X:** Check capture Status after the demo exits and choose Stop if capture remains active. Make sure the new session is under `oracle/extract/`.

- **You — in the agent chat:** After the capture has stopped, copy and send this prompt. Then wait for the agent’s inventory before continuing.

```text
The full capture is done. Please inspect the new session and continue Step 02.
```

- **Agent:** Discovers and inventories the new session, checks its manifest and capture count, and reports memory coverage and any unreadable or missing ranges.

- **You:** Check the inventory and any reported capture gaps. Follow the agent’s next action if the session or required evidence is incomplete.

- **Agent — outcome:** Says “You can continue to Step 03.” only when it has inventoried a finalized timeline session and audited actual memory coverage. Otherwise says “Stay on Step 02” and gives the next action. Reply with any requested result so the agent can finish this same step.

**Notes**

Use [the capture setup guide](docs/guides/dosbox-capture-setup.md). A starting fixed count such as `5000` is a proposal; record the actual value used. Save screenshots, registers, VGA state, and the 8 MiB memory region at every snapshot by default. Reduce cadence only with a stated evidence tradeoff; extra disk use is preferable to repeated manual point captures. The profile must pass the timeline validator; valid JSON alone is insufficient. PASS does not prove memory coverage: code, input buffers, heap, and stack may lie beyond a small dump. The starter region is 8 MiB; the agent must justify any reduction, verify mappings, and report partial/unreadable memory. Overlapping code/data dumps do not extend the captured range. After capture, check Status and Stop if still active. A session.json left at running with zero captures is not finalized even if snapshot folders exist. Reuse this full run for offline analysis. A [targeted capture](docs/templates/CAPTURE_REQUEST.md) is exceptional and requires a concrete question that the adequately sized full run cannot answer.

---

## Step 03: Save and index the disassembly

Create the IDA listing first; then let the agent find and index it.

- **You:** Finish the capture in Step 02. Choose the code image to disassemble using the agent’s guidance; use a working copy if it came from a capture session.

- **You — in IDA:** Create the disassembly and export a text listing with a descriptive `.asm` filename into this workspace’s `oracle/` folder. Finish the export before sending the prompt.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 03. Find the IDA .asm listing in oracle/ and determine whether it describes the original executable or a captured code image. Inspect any existing SQLite index for that listing, including its source hash, schema version, and instruction count. If a legacy index omitted instruction lines, rebuild with the current schema-v2 asm_index into a new unused .sqlite path; preserve the old database and any annotations. Report instruction and call-reference counts, and use the selected new database explicitly with --db for later queries. Keep addresses unknown where IDA omitted them; do not invent offsets. Find the relevant capture session in oracle/extract/ and use its code and data dumps for byte checks. Do not ask me for filenames, session IDs, or another data export.
```

- **Agent:** Finds the listing and relevant captures, identifies the listing’s source, and builds or selects a usable SQLite index without overwriting an existing database.

- **You:** Check that the agent reports a usable index, instruction/call-reference counts, and any unknown addresses. Unfinished capture metadata must remain clearly recorded.

- **Agent — outcome:** Says “You can continue to Step 04.” only when it has identified the listing’s source and a usable index, with limits recorded. Otherwise says “Stay on Step 03” and gives the next action. Reply with any requested result so the agent can finish this same step.

**Notes**

An existing schema-v1 index with zero instructions can be replaced for analysis by a new schema-v2 index, without overwriting the old file. IDA may omit addresses on instruction lines; the indexer retains their line numbers and call references with unknown addresses. Keep capture dumps in their original session directory under `oracle/extract/`. If you load a captured binary into IDA, use a working copy outside that immutable session so IDA database sidecars do not alter it. See [asm_index](tools/asm_index/README.md) and [address mapping](docs/guides/address-mapping.md).

---

## Step 04: Map memory addresses

Connect disassembly addresses to bytes in the memory dumps.

- **You:** Finish Step 03: wait for the agent to identify a usable index and the relevant capture session.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 04. Discover the usable assembly index and relevant session in this workspace; do not ask me for their paths or IDs. Use the session’s code and data-segment dumps to document segment bases and dump offsets. Keep each capture’s provenance distinct. Verify several code, data, and stack anchors against raw bytes. For any asm_index query, pass the discovered index path with --db. Record formulas, evidence, and mismatches in docs/address-map.md before translating any routine. If session metadata conflicts with the capture files, document the discrepancy and state what can still be verified.
```

- **Agent:** Checks code, data, and stack anchors against captured bytes and writes the mapping formulas, evidence, and mismatches to `docs/address-map.md`.

- **You:** Check that the report identifies verified mappings and their limits. Have the agent resolve any mismatch affecting the intended analysis.

- **Agent — outcome:** Says “You can continue to Step 05.” only when it has verified the address map and resolved mismatches affecting the next analysis. Otherwise says “Stay on Step 04” and gives the next action. Reply with any requested result so the agent can finish this same step.

**Notes**

For protected mode, the useful address is usually segment base plus register offset, adjusted for dump base. Do not assume an IDA address equals a file offset. The agent supplies any suggested follow-up command for your information; you do not need to run an index query yourself. See [address mapping](docs/guides/address-mapping.md).

---

## Step 05: Mark the scenes

Make a short scene ledger so translation follows the demo’s actual order.

- **You:** Finish Step 04: wait for the address map and byte-check results.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 05. Find the timeline session in oracle/extract/. Use decoded screenshot pixels, not compressed image bytes, to build a scene atlas and a labeled contact sheet under oracle/, outside the immutable capture session. Inspect the screenshots and propose a concise docs/scene-ledger.md with visual descriptions, approximate time ranges, and transition evidence. Automated change scores identify candidates, not confirmed scenes. Give me links to the contact sheet and ledger, and ask me to accept or correct the proposed visual phases and uncertain transition windows before treating them as milestones. Do not require exact cut times beyond what the captures establish, or infer demo completion from a final blank screenshot or unfinished session manifest.
```

- **Agent:** Builds a labeled contact sheet and proposes a scene ledger from decoded screenshots, with approximate time ranges and uncertain transitions. Provides links for your review.

- **You:** Open the contact sheet and scene ledger. Tell the agent which phases you accept and which need correction; request larger images if needed. Confirm the first scene and its approximate time span in your reply.

- **Agent — outcome:** Says “You can continue to Step 06.” only when you have confirmed the first scene and its approximate interval. Otherwise says “Stay on Step 05” and gives the next action. Reply with any requested result so the agent can finish this same step.

**Notes**

The atlas organizes captured screenshots; it does not become player footage. Motion, fades, and flashes can trigger automated change scores within one scene. Review proposed phases visually; a tool’s provisional count is not a confirmed scene count. Sparse captures can miss brief scenes, and an unfinished session or final blank frame does not establish the demo’s end. See [scene review guidance](tools/oracle/README.md).

---

## Step 06: Prove one routine

Translate a small routine and compare it with original code on real demo input.

- **You:** Finish Step 05: review the scene ledger and confirm which scene comes first.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 06. Use real full-run checkpoints to choose one bounded routine or resumable interval needed by the first scene. Define its comparison contract, run original code offline and the JavaScript translation on the same justified input/state, and report compared outputs, covered checkpoints, first mismatches, and limitations. Use the framework replay tools where suitable. If an undersized earlier run lacks input, prepare a corrected full-run capture before considering exceptional point captures. Record reproducible results; synthetic fixtures and missing evidence do not complete this step.
```

- **Agent — offline:** Uses explicit contracts and suitable real checkpoints to compare original machine code and JavaScript, reporting missing evidence and the first mismatch. Records the input source, compared outputs and state, and any gaps.

- **Agent — if evidence is missing:** Checks all suitable checkpoints and original files. If the earlier run used an undersized dump, prepares a corrected full-run profile with adequate memory coverage, normally 8 MiB per snapshot. Analyzes that new full run offline before considering any point capture.

- **You — in DOSBox-X, only if requested:** If a corrected full run is needed, follow the supplied menu instructions and capture from start to finish. Reply “The full capture is ready.” The agent discovers the session and resumes this step’s offline comparison.

- **You:** Check the real-input comparison report and its stated output/state coverage. A synthetic fixture, prepared capture profile, or new session alone does not complete this step. The agent must resolve missing evidence or mismatches before declaring completion.

- **Agent — outcome:** Says “You can continue to Step 07.” only when a real-input routine comparison passes with evidence and comparison scope recorded. Otherwise says “Stay on Step 06” and gives the next action. Reply with any requested result so the agent can finish this same step.

**Notes**

Periodic checkpoints can supply real memory and register state even when sampled inside a routine. Resume from that instruction to a bounded stop in Unicorn, then compare JavaScript on the same state. A live CALL/return pair is not required. When a 1 MiB dump omitted the input, correct the full-run memory coverage before requesting more manual experiments. Targeted captures are reserved for a demonstrated question that an adequately sized full run and offline execution cannot resolve. See [routine contract](docs/templates/ROUTINE_CONTRACT.md) and [capture guidance](docs/guides/dosbox-capture-setup.md).

---

## Step 07: Render a live frame

Connect scene setup and drawing code to the browser canvas.

- **You:** Finish Step 06: wait for a passing comparison on real demo input, with the compared outputs and state documented.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 07. Implement the production adapter in the player template and translate the first scene’s setup, palette, and drawing using recovered geometry and timing. Generate the frame live, compare it with the captured reference at a justified matching state/time, and report pixel/hash results and visible differences separately. Give me the browser review instructions.
```

- **Agent:** Translates the first scene’s setup, palette, and drawing, then compares a live frame with the captured reference.

- **You — in the browser:** Open the player using the agent’s instructions. Tell the agent you reviewed the frame and report any visible differences; ask it to address issues that prevent continuing.

- **You:** Continue with visuals first by default. If you prefer sound first, tell the agent once; it will remember your choice.

- **Agent — outcome:** Once the frame comparison and your review are recorded, says “You can continue to Step 08.” for visuals first, or “You can continue to Step 09.” if you chose sound first. Otherwise says “Stay on Step 07” and gives the next action. Reply with any requested result so the agent can finish this same step.

**Notes**

Screenshot resemblance is a visual check, not execution proof. Exact hashes require matching dimensions, palette conversion, and capture time. Never play back captured frames. See the [player contract](templates/player-template/README.md) and [validation ladder](docs/guides/validation-ladder.md).

---

## Step 08: Complete the visual sequence

Port the full graphical timeline. Sound can wait until the next step.

- **You:** Finish Step 07 and review the first live frame. If you chose sound first, return here after Step 09.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 08. Complete the graphical sequence through the scene ledger in chronological order. Generate every frame live, verify bounded routines across real inputs, and compare continuous scenes, representative frames, inherited transitions, and endings. Reuse verified shared engines and layouts where appropriate; preserve variant quirks. Audio replay is not a prerequisite. Use a replaceable simulation clock based on recovered demo timing so sound can be integrated later. Default to smooth live playback, keep capture-schedule matching in validation mode, and document unverified draw-rate assumptions; preserve any known music-driven progression and record unresolved timing assumptions. If audio is already implemented, keep it integrated and check synchronization across the completed timeline. Profile before optimizing and rerun relevant comparisons. Give me the player instructions and a concise list of remaining visual and timing differences for review. Keep deferred sound clearly recorded as pending.
```

- **Agent:** Ports the scenes in order, checks routines and transitions, and builds continuous visual playback using an explicit simulation clock. If audio is already implemented, checks full integrated playback as well.

- **You — in the browser:** Review the full graphical sequence. Tell the agent about missing scenes, visual differences, or timing issues. Silent playback is expected if you chose visuals first.

- **Agent — outcome:** Once the full visual sequence, comparisons, remaining differences, and your review are recorded, says “You can continue to Step 09.” if sound is pending. If Step 09 is already complete and full playback synchronization is checked, says “You can continue to Step 10.” Otherwise says “Stay on Step 08” with the next action.

**Notes**

Use this step before or after sound according to your preference. A temporary visual clock should advance simulation from elapsed time or explicit ticks, not from browser frame count. Slow emulator draws and screenshot intervals do not set the normal player frame rate. Preserve draw-dependent feedback updates in simulation and keep extra redraws from advancing them; record any provisional draw cadence. If visuals depend on tracker positions or music events, recover those control values as needed without requiring full audible replay. When sound is added, switch the time source and recheck scene transitions. See [timing guidance](docs/guides/sync-and-timing.md).

---

## Step 09: Add sound and synchronization

Rebuild live sound and connect it to visual timing. You may do this immediately after Step 07 if you prefer.

- **You:** Finish Step 08 for the default visuals-first route, or finish Step 07 if you chose sound first.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 09. Recover the actual sound system and translate its original replay, sequencer, mixer, synthesis, or device-control code using original data. Verify real state/PCM or device-event behavior and relevant chunk/loop boundaries. Integrate it with the visual clock and check a transition; if full graphics exist, check the full audiovisual timeline. Give me playback instructions and remaining differences for review. Preserve pending graphics if sound was chosen first. Establish verified silence from evidence when applicable.
```

- **Agent:** Identifies the actual soundtrack and timing source, implements live replay, and checks synchronization with the available visuals. If the full visual sequence exists, checks the full integrated playback.

- **You — in the browser:** Listen and watch through a transition, or the full run when visuals are complete. Tell the agent you reviewed playback and report sound or synchronization problems.

- **Agent — outcome:** Once audio, transition synchronization, and your review are recorded, says “You can continue to Step 08.” if the visual sequence is pending. If Step 08 is already complete and full integrated playback is checked, says “You can continue to Step 10.” Otherwise says “Stay on Step 09” with the next action.

**Notes**

The graphics and sound milestones may be completed in either order. Deferring sound does not mean it is complete. If sound is completed first, return to Step 08 for the remaining scenes. Before packaging, check the complete visual sequence with live audio and record remaining synchronization differences. See [audio guidance](docs/guides/audio-and-music.md) and [timing guidance](docs/guides/sync-and-timing.md).

---

## Step 10: Standard player and release

Build the canonical landing page, player controls and live diagnostics in one release/ directory; test real UI interactions and packaged playback.

- **You:** Finish both Step 08 (full visuals) and Step 09 (sound, or verified absence of a soundtrack), in either order. Review full integrated playback and remaining differences. Finite productions include timeline seeking by default; measure latency and add checkpoints where needed.

- **You — in the agent chat:** Copy and send the following prompt now.

```text
Tutorial Step 10. Build the standard standalone release described in docs/guides/release-player-standard.md, using templates/player-template as the canonical implementation. Use exactly one release/ directory and update it in place. Preserve the standard landing page, live darkened first-animation background, responsive player layout, controls and keyboard behavior; adapt only production metadata, credits, links and palette. Include Stats for nerds with measured FPS and a live module pattern grid with channel headers, note/instrument/effect columns, surrounding rows and a highlighted current row driven by the original replay cursor when module data exists; otherwise show truthful source-specific sound diagnostics or verified silence. Test the packaged root and player entry pages, actual timeline click/hold/drag and keyboard controls, paused/running seeks, rapid and backward seeks, stop/restart, volume, scale, fullscreen, transitions and natural ending. Compare actual canvas frames with independently generated expectations using the browser acceptance harness. Measure page/worker/seek/transition performance. Add sparse complete graphics/audio checkpoints when measured seeking cost needs them and compare restored plus forward playback with uninterrupted execution. Remove fixture routes, development oracles and unused assets from the package. Provide the release manifest, completed checklist, exact local preview and HTTPS deployment steps, remaining differences and human review link. Finish all automated checks and request packaged full-run audiovisual review; leave publication to me.
```

- **Agent:** Packages and tests the standalone player. Follows docs/guides/release-player-standard.md, retains the template UI, measures seeking and verifies complete restored playback against uninterrupted playback.

- **You — in the browser:** Run the packaged player using the supplied instructions and check playback and any seeking controls.

- **You:** Tell the agent the packaged playback review result and review remaining differences and the release checklist. You decide when and where to publish.

- **Agent — outcome:** Says “Tutorial complete. You can proceed to your release decision.” only when packaged playback, the standard UI and seeking checks, and your review are complete. Otherwise says “Stay on Step 10” and gives the next action. Reply with any requested result so the agent can finish this same step.

**Notes**

Finite-player seeking is standard; checkpoint storage is an implementation choice driven by measured latency. See [checkpoint guidance](docs/guides/checkpoint-seeking.md). Test `node release/serve.mjs` and both packaged entry pages, then review the hosted build.

Step 10 UI, packaging and acceptance requirements: [standard release player](docs/guides/release-player-standard.md).
