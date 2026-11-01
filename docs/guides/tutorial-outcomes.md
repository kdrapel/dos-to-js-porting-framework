# Tutorial step outcomes

Use this protocol for every tutorial step, including the human debugger handoff in Step 01, and every follow-up while that step is active. The outcome applies to the whole step, not just the latest subtask.

This behavior comes from `AGENTS.md`; it does not depend on a reminder in a tutorial prompt. Short follow-ups such as “Resume Step 06” and “The capture is ready” receive the same outcome and continuation decision automatically. After a framework refresh, read the current rules and recover the active step from the conversation and existing artifacts. Do not ask the human to restate the reporting format, paths, or completed work.

## Required agent response

Start with one status:

- **STEP NN — COMPLETE**: All requirements for this step are met, including any required human review.
- **STEP NN — ACTION NEEDED**: A specific human action is needed, such as running a prepared capture or reviewing a contact sheet. The step is not complete.
- **STEP NN — INCOMPLETE**: Required evidence, a comparison, or implementation is still missing or failing. State what remains and the next action. Do not mark it complete because a report was written.

Follow the status with brief evidence and links to the relevant output. Finish with exactly one explicit decision, using actual step numbers and a concrete action:

- Complete: **You can continue to Step MM.**
- Not complete: **Stay on Step NN. Next: [You or Agent] — [one concrete action].**
- Final Step 10 complete: **Tutorial complete. You can proceed to your release decision.** Publication remains the human's choice.

When the next action is human-owned, provide the prepared files/instructions or review links, and say what the human should reply with afterward. Discover files and session IDs yourself. A reply such as “The capture is ready; continue Step 06” is sufficient; do not require a fresh tutorial prompt or user-supplied paths.

Continue authorized offline work while it can resolve the issue. Do not stop merely to ask whether to run the next offline check. After a human provides a capture or review, resume the same step through its remaining analysis and checks and report a new outcome. Preparing a capture JSON, receiving a session, or inventorying it is not the completion of Step 06.

Minimize human capture work: reuse a full start-to-end run with adequate memory, normally 8 MiB at every snapshot. Correct an undersized run with a broader full-run profile before considering point captures. Resume mid-routine checkpoints offline; live entry/return pairs are not prerequisites for Step 06. A targeted capture request is exceptional and must explain a specific question that an adequately sized full run and offline analysis cannot resolve, unless the human explicitly requested that experiment. If a corrected full run is pending during Step 06, report ACTION NEEDED on Step 06 rather than restarting unrelated completed steps.

Record the active step, status, evidence, and next action in the task queue and handoff. Human review that is required but has not happened means ACTION NEEDED. Do not infer approval from silence. Technical detail may live in linked reports; the response itself must make the decision and next action clear.

## Completion criteria

After Step 07, default to **visuals first: 08 → 09 → 10**. If the human chooses sound first, use **09 → 08 → 10**. Remember an existing preference; do not repeatedly ask. Step 08 is the full graphical sequence and Step 09 is sound/synchronization. Track the two milestones independently: pending sound does not block visual work and must not be marked complete just because it was deferred. Step 10 requires both milestones and a full integrated playback check.

If an existing project used the older numbering (08 for sound, 09 for full graphics), reconcile the recorded artifacts by their meaning, not just their step number. Preserve verified work and update the task queue/handoff; do not repeat completed work solely because the tutorial was reordered.

| Step | Complete when | Next |
| --- | --- | --- |
| 00 | The workspace's intended executable and companion files are identified and required missing inputs are resolved. | 01 |
| 01 | Pasted debugger text establishes the observed CS, instruction location, and nearby disassembly needed to plan capture. No separate prompt or agent-operated emulator pass is required. | 02 |
| 02 | A human-run timeline contains multiple snapshots, the session is finalized with a matching count, and actual memory mappings/readability and any coverage limits are audited. Preparing JSON or seeing validator PASS alone is insufficient. | 03 |
| 03 | The listing's source is identified and a usable index is selected or built with source/schema/count checks, with unknown addresses and evidence limits recorded. | 04 |
| 04 | Code/data/stack anchors and mapping formulas are checked against raw bytes, with no unresolved mapping issue preventing the intended next analysis. | 05 |
| 05 | The atlas/contact sheet and ledger are delivered, and the human has confirmed the first scene and its approximate interval. Other uncertain cuts remain explicitly provisional. | 06 |
| 06 | Original captured code and JavaScript pass a differential comparison on real demo input with justified initial state, reproducible commands, and explicit output/state coverage. Synthetic-only matches, prepared capture profiles, or unprocessed captures leave this incomplete. | 07 |
| 07 | A live first frame renders, its reference comparison and differences are recorded, and the human has reviewed it. | 08 by default; 09 if sound first was chosen |
| 08 | The full graphical sequence plays, scene/transition comparisons and timing limits are recorded, and the human has reviewed it. Audio is not a prerequisite. Normal playback is smooth; capture-schedule matches and provisional draw-rate assumptions are documented separately. If audio is already complete, also check full integrated playback. | 09 if sound is pending; otherwise 10 after the integrated check |
| 09 | Actual soundtrack/timing behavior is implemented, synchronization is checked through a transition, and the human has reviewed playback. If full graphics exist, check integrated playback across the full run. If there is no soundtrack, establish that from evidence and document its actual timing source. | 08 if full graphics are pending; otherwise 10 after the integrated check |
| 10 | Both visual and audio milestones and the full integrated playback check are complete; the standalone package meets [the standard release player](release-player-standard.md), real UI and both entry routes pass browser checks, finite-timeline seeking passes visual/audio restore comparisons, and the human has reviewed packaged playback and remaining differences/release checklist. Publishing is not a completion requirement. | Release decision |

Evaluate the stated criterion, not a claim that the entire demo is proven correct. Record nonblocking limitations explicitly; never hide a missing requirement behind a broad PASS.
