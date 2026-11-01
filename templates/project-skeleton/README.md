# <Demo Name> — JavaScript Port

Reverse-engineering and porting **<Demo Name>** (by <Group Name>, <Year>) to modern JavaScript and Web Audio.

## Project Structure

```text
.
├── original/             # Original immutable production files (EXE, README, data)
├── oracle/               # Evidence, IDA assembly listing, and SQLite index
│   ├── inputs/           # Separately supplied IDA/debugger dumps with provenance
│   ├── extract/          # Immutable DOSBox-X capture corpus
│   ├── fixtures/         # Isolated bounded execution inputs with provenance
│   ├── reference/        # Golden outputs from original-code execution (Unicorn)
│   ├── reports/          # Verification ledgers, coverage reports, and diffs
│   ├── assets/           # Extracted textures, meshes, palettes, and music
│   └── <demo>.sqlite     # SQLite FTS5 index of the IDA assembly listing
├── tools/
│   ├── asm_index/        # Assembly listing query CLI
│   └── oracle/           # Bounded interval replay and differential comparators
├── js/                   # Translated JavaScript kernels and state machine
├── player/               # Standalone browser deliverable (zero-npm static app)
└── docs/                 # Engineering notes, address maps, and task queue
```

## Running the Player

- **Windows**: Double-click `player/Start.cmd`.
- **Node.js**: Run `node player/server.mjs` and open `http://localhost:1997`.
- **Static Hosting**: Deploy the contents of `player/` to GitHub Pages or any web server.
