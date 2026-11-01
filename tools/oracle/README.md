# Offline capture analysis

Install optional offline screenshot/replay dependencies with `python -m pip install -r tools/oracle/requirements.txt`. Pillow is used by screenshot tools; Unicorn is used by CPU replay. Neither is shipped with the browser player.

## Replay and comparison tools

See [validation ladder](../../docs/guides/validation-ladder.md) for capture loading/forking (`capture_corpus.py`), batch checkpoint/stage execution (`replay_suite.py`), streamed first-divergence checks (`sequence_compare.py`), explicit contracts and strict verdicts (`differential_compare.py`), and the JavaScript driver helper (`report.mjs`). `binary_triage.py` supplies format/asset candidates before disassembly. The built-in CPU adapters are bounded real16/protected32 integer replay; unsupported FPU/devices/paging need verified offline adapter drivers and cannot silently pass.

## Default evidence: a full-run timeline

Prefer a complete start-to-end capture with the starter 8 MiB memory region at every 1–2-second snapshot, then reuse its checkpoints offline. If the existing run saved too little RAM, prepare a corrected full-run timeline and preserve the old session. A mid-routine checkpoint can be resumed to a bounded stop in Unicorn and JavaScript; live entry/return snapshots are not required for that comparison.

## Exceptional guarded routine capture profiles

Use a targeted profile only at the human's explicit request or after analyzing an adequately sized full-run session and documenting a specific question it and offline execution cannot resolve. Insufficient coverage in an earlier 1 MiB run is a reason to correct the full run, not a reason to request point captures.

For a targeted E8 rel32 CALL/return pair, the source event is the callee entry after CALL, with `previous_offset` pointing at the CALL instruction. The return event is the caller continuation after RET. Validate the configuration against verified captured CALL bytes before handing it to the human:

```powershell
python tools/oracle/validate_capture_profile.py --purpose paired-targeted --call-bytes E8FB0F0000 targeted-profile.json
```

The command's bytes are illustrative; the agent supplies the actual captured bytes and discovered profile path. This check supports five-byte E8 rel32 calls with a 32-bit stack and return without argument cleanup; other encodings need separate review. PASS checks the supplied byte arithmetic and profile settings, not live mappings or memory coverage. See the [capture request procedure](../../docs/templates/CAPTURE_REQUEST.md), including the human debugger procedure for triggers reached too early to activate capture from the menu.

## Scene review

The agent discovers the relevant capture session and chooses descriptive output filenames outside it:

```powershell
python tools/oracle/scene_atlas.py --session oracle/extract/SESSION --output oracle/scene-atlas.json --contact-sheet oracle/contact-sheet.jpg
```

`SESSION` is an agent-discovered path, not information the human must supply. The tool reads capture files and generates a JSON atlas and optional labeled contact sheet. Keep outputs outside immutable capture sessions.

Frame comparison decodes screenshots to RGB, applies palette colors, and measures mean absolute RGB difference on 64×64 samples. PNG compression and metadata do not affect this score. The original file SHA-256 remains in `sha256`; `decoded_rgb_sha256` records decoded pixel content and dimensions.

Differences above 35% and resolution changes produce **unreviewed candidate windows**, bounded by adjacent capture times. They do not establish scene boundaries: motion, flashes, and fades can also produce large differences, and small changes or sparse sampling can hide transitions. `provisional_scenes_count` counts proposed groups, not confirmed scenes. Missing/corrupt screenshots generate warnings and break pixel comparisons; unknown times remain null.

Use the contact sheet and decoded screenshots to write a short draft ledger with descriptions, approximate intervals, uncertain boundaries, and links to review images. Ask the human to accept or correct the proposed visual phases before treating them as milestones. An unfinished session manifest or final blank screenshot does not prove the demo ended.

Regression checks:

```powershell
python -B -m unittest discover -s tools/oracle -p test_scene_atlas.py
```
