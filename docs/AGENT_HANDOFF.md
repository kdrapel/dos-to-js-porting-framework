# Framework Maintenance Handoff

## Current state

- The framework is demo agnostic: `README.md` names no production and shows no screenshot gallery, and the docs and DOSBox-X patch use generic examples rather than a named demo.
- The canonical release player standard is `docs/guides/release-player-standard.md`. It defines the generic metadata-configured landing/player shell, live original first-animation background in a separate worker, measured presented FPS, normalized module grid driven by original audio diagnostics, paired graphics/audio seek completion, one `release/` packager, and both entry routes. Tutorial (HTML and Markdown), root/skeleton `AGENTS.md`, the outcome protocol, validation ladder, and task/handoff templates all require it.
- This standardizes the release UI and behavior; it does not mark a production Step 10 complete.

## Reproduce

```bash
node --test templates/player-template/tests/runtime.test.mjs
node templates/player-template/tests/browser.mjs
node templates/player-template/build-release.mjs   # must fail clearly while unconfigured
```

Production flow: copy the template to `player/`, implement original adapters and metadata, run `node player/build-release.mjs`, serve with `node release/serve.mjs`, then run `node player/tests/browser.mjs --url http://127.0.0.1:1997/ --expectations <independent expectations> --output release/browser-acceptance.json`.

## Verification status

- 11/11 runtime/release tests and headless Chrome infrastructure acceptance passed for the release standard; report at `docs/reports/release-player-standard-browser.json`. Fixture evidence covers infrastructure only, never production fidelity.
- The tutorial's editorial layout has no recorded visual browser review.

## Blockers and limits

- Each production must implement format-specific display decoding, read-only original cursor telemetry, a verified live landing loop, suitable graphics/audio checkpoints, whole-run performance measurement, and final human review.
- The release builder requires a stale/unused-data audit; publication remains human-owned.

## Next action

Apply `docs/guides/release-player-standard.md` to the next production Step 10: run its independent expectations, complete `docs/templates/RELEASE_CHECKLIST.md`, and keep new docs, README additions, and patch examples free of production names, screenshots, and port credits.
