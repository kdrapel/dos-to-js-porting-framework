# DOS Demo Porting Framework

> A disciplined, evidence-based engineering framework to reverse-engineer 1990s DOS demos and intros and port them to modern, high-performance JavaScript and Web Audio.

---

## What is this?

This framework helps a human developer and an AI coding agent reverse-engineer a DOS demo and build a standalone browser port. It brings together a practical workflow, capture and analysis tools, verification harnesses, and a JavaScript player template. The framework is demo agnostic: it ships no production code, assets, or screenshots, and its workflow, tools, and prompts apply to any DOS demo you bring to it.

The aim is to understand and translate the original program's graphics, timing, and sound code into JavaScript, then compare the translation with evidence from the original. The result is a live browser player built for the particular demo; the framework provides the tools and structure, not an automatic conversion of an executable.

---

## Key Features & Highlights

- **100% Live JavaScript Rendering**: No recorded video, no synthetic frame sequences, no pre-rendered background movies. Every frame is calculated live by translated algorithms.
- **Original-Code Sound Replay**: Translate the production’s own replay, mixer, synthesis, and/or device-control code. Original data is replayed live; module-player libraries and generic replacement synths are not substitutes.
- **Bounded Assembly Indexer (`asm_index`)**: Indexes 50–100 MB IDA Pro disassembly listings into a fast SQLite + FTS5 database, allowing developers and AI agents to query functions, callers, callees, references, and instruction flows without choking LLM context windows.
- **Explicit Verification Contracts**: Compare declared state/output observables on real input; missing evidence and unsuccessful replay cannot pass. Built-in real16/protected32 integer replay and production-specific adapter drivers feed a routine-to-browser validation ladder.
- **Measured Seeking**: The player supports deterministic reset-and-advance; optional complete-state checkpoints can accelerate it. Size, spacing, and latency depend on the production and must be measured.
- **Zero-Dependency Standalone Deliverable**: Pure ES Modules. No `npm install`, no `node_modules`, no bundlers required. Runs on any static host (like GitHub Pages) or locally via a double-click Windows launcher (`Start.cmd`) or Node.js (`server.mjs`).
- **AI Agent Ready**: Includes comprehensive operational constraints, evidence contracts, and task templates optimized for human-AI pair programming.

---

## Quickstart

Open **[tutorial.html](tutorial.html)** in your browser and follow the illustrated guide. It takes you from a DOS demo archive through capture, analysis, translation, and validation to a browser player. You operate DOSBox-X and IDA; the guide provides prompts and instructions for working with your AI coding agent.

Windows users can start with the precompiled [patched DOSBox-X executable](dosbox-release/patched-dosbox-x.exe) in `dosbox-release/`. It includes the automatic capture patch used by the tutorial.

The [text version of the tutorial](QUICKSTART.md) is also available, along with the detailed [methodology](METHODOLOGY.md).

---

## Repository Structure

```text
09-dos-porting-framework/
├── README.md                      # This documentation
├── tutorial.html                  # Interactive visual tutorial of the quickstart guide
├── QUICKSTART.md                  # 10-step walk-through from raw .EXE to shipping player
├── METHODOLOGY.md                 # Deep-dive engineering methodology and architecture
├── AGENTS.md                      # Operational rules and instructions for AI agents
│
├── dosbox-patch/                  # Custom DOSBox-X Automatic Capture patch & build guide
│   ├── dosbox-x-autocapture.patch # Unified patch against base commit 0933a6fd
│   └── README.md                  # Patch instructions, base commit, and build steps
├── dosbox-release/                # Precompiled patched DOSBox-X executable for Windows
│
├── tools/                         # Offline development & verification tools (Python; Unicorn/Pillow where needed)
│   ├── asm_index/                 # Standalone IDA disassembly indexer and bounded CLI query tool
│   │   ├── asm_index.py           # CLI tool (functions, callers, callees, refs, context, search, SQL)
│   │   ├── schema.sql             # SQLite + FTS5 database schema
│   │   ├── test_asm_index.py      # Unit tests
│   │   └── README.md              # Detailed tool manual
│   └── oracle/                    # Capture inspection and differential testing
│       ├── inventory.py           # Capture corpus validator and provenance hasher
│       ├── unicorn_runner.py      # Bounded real16/protected32 integer replay; explicit unsupported-state diagnostics
│       ├── differential_compare.py# Contract comparator with PASS/FAIL/INSUFFICIENT_EVIDENCE
│       ├── capture_corpus.py      # Immutable checkpoint loading and independent working memory
│       ├── replay_suite.py        # Multi-checkpoint/stage batch execution
│       ├── sequence_compare.py    # First divergent frame/tick/operation in report streams
│       ├── report.mjs             # Offline JavaScript report and memory helper
│       ├── binary_triage.py        # Format/asset candidates before disassembly
│       └── scene_atlas.py         # Screenshot transition analyzer and scene contact sheet generator
│
├── templates/
│   ├── project-skeleton/          # Clean starter directory structure for a new demo port
│   └── player-template/           # Standalone modern web player boilerplate
│       ├── index.html             # Presentation interface (canvas, HUD, fullscreen, nerd stats)
│       ├── style.css              # Dark responsive presentation stylesheet
│       ├── server.mjs             # Zero-dependency local Node.js static server (COOP/COEP)
│       ├── Start.cmd              # One-click Windows batch launcher
│       ├── Start.ps1              # One-click Windows PowerShell HTTP server
│       ├── app/
│       │   ├── app.mjs            # Main browser coordinator and keyboard controller
│       │   ├── render-worker.mjs  # OffscreenCanvas / ImageData graphics rendering thread
│       │   ├── audio-worker.mjs   # Software mixer and tracker sequencer thread
│       │   ├── audio-worklet.mjs  # Real-time Web Audio Worklet for glitch-free streaming
│       │   └── tracker-view.mjs   # Optional source-driven channel diagnostics
│       └── runtime/
│           ├── machine.mjs        # Simulated guest x86 memory, flags, and arithmetic engine
│           └── checkpoint.mjs     # Differential sparse-page encoder & restorer for seeking
│
└── docs/                          # Guides, contracts, and workflow templates
    ├── MIGRATION_PLAN.template.md # Master 13-phase porting recipe (Phases A through M)
    ├── ORACLE_SPEC.template.md    # Evidence classes and differential verification contract
    ├── TASK_QUEUE.template.md     # Ordered milestone task queue (S00 to S26)
    ├── AGENT_HANDOFF.template.md  # Session-to-session handoff template
    ├── templates/
    │   ├── TASK_CARD.md           # Bounded task specification card
    │   ├── ROUTINE_CONTRACT.md    # Routine translation and verification contract
    │   ├── CAPTURE_REQUEST.md     # Emulator capture specification for the human operator
    │   └── autocapture-config.template.json # Custom DOSBox-X automatic capture configuration
    └── guides/
        ├── dosbox-capture-setup.md# Custom DOSBox-X build setup, auto-capture & snapshot workflow
        ├── address-mapping.md     # DOS memory models, segmentation, linear bases, and IDA coords
        ├── x87-floating-point.md  # FPU precision, rounding modes, trig approximations, and drift
        ├── audio-and-music.md     # Tracker reverse-engineering, mixer math, and AudioWorklet
        ├── sync-and-timing.md     # Audio-clock master synchronization and frame scheduling
        └── checkpoint-seeking.md  # Sparse-page memory diffing and scrubbing architecture
```

---

## How to Use this Framework

The generic [validation tools](docs/guides/validation-ladder.md) and [player contract](templates/player-template/README.md) are implemented and tested infrastructure. The production’s algorithms, loader, timing, and required device/FPU adapters must still be recovered and verified. The default player refuses an unconfigured port; `?fixture=1` is an explicitly labeled infrastructure test, not a demo recreation.

### 1. Starting a New Demo Port
1. Follow [tutorial.html](tutorial.html) for the step-by-step roadmap; [QUICKSTART.md](QUICKSTART.md) provides the text version.
2. Copy or check out the entire framework into a folder dedicated to that demo, and open that folder as the agent workspace.
3. Create `original/` there and extract the complete demo archive into it, preserving data files and subfolders. Save the IDA `.asm` listing under `oracle/`. Code and data dumps from automatic capture stay in `oracle/extract/`; only separately supplied dumps go in `oracle/inputs/` with provenance.

### 2. Navigating Assembly Listings
Index your disassembly listing to navigate the codebase without opening 50 MB text files:
```powershell
python tools/asm_index/asm_index.py --db oracle/demo.sqlite build --source oracle/demo.asm
python tools/asm_index/asm_index.py --db oracle/demo.sqlite function sub_14000
python tools/asm_index/asm_index.py --db oracle/demo.sqlite callers sub_14000
python tools/asm_index/asm_index.py --db oracle/demo.sqlite refs dword_A240
```

### 3. Verifying Code with the Oracle

Use [comparison contracts and batch replay](docs/guides/validation-ladder.md) to sample real checkpoints, then validate intervals, scenes, transitions, and actual browser output. Compare suspected engine copies with `tools/asm_index/compare_routines.py` before duplicating translations.
Compare your translation against the original on the contract’s declared observables and tested inputs:
```powershell
python tools/oracle/replay_suite.py --session oracle/extract/SESSION --plan oracle/replay-suite.json --output oracle/new-results
```

The agent discovers the actual session path and prepares the plan/contracts; `SESSION` illustrates the CLI interface, not information the human must supply. The suite writes new input/reference/JavaScript/comparison reports and never overwrites captures or previous suite runs.

### 4. Running the Web Player
- **Windows**: Double-click `player/Start.cmd`.
- **Node.js**: Run `node player/server.mjs`.
- **Web**: Upload the `player/` folder to GitHub Pages or any static web host.

---

## Recommended AI Pair Programming Workflow

When collaborating with an AI coding assistant (Claude, Gemini, GPT):
1. Point the agent to [AGENTS.md](AGENTS.md) as its primary operating rulebook.
2. Copy `docs/TASK_QUEUE.template.md` to `docs/TASK_QUEUE.md` to maintain strict phase gates.
3. Use [docs/templates/TASK_CARD.md](docs/templates/TASK_CARD.md) to assign small, bounded, verifiable tasks.
4. Have the agent fill out [docs/AGENT_HANDOFF.template.md](docs/AGENT_HANDOFF.template.md) at the end of every session so context is never lost.

---

## Standard final player

Step 10 follows the [canonical release player specification](docs/guides/release-player-standard.md). Use the supplied landing/player/diagnostics shell and one release/ directory. Adapt production metadata, palette and source adapters; retain layout, controls and tested behavior. Test actual timeline gestures and both entry pages, not only window.player.seek(). Include measured FPS and source-driven module diagnostics, live darkened original landing animation, complete audiovisual seeks and packaged human review. Pending tests cannot be reported as PASS. Publication remains human-owned.
