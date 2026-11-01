# Assembly Indexer (`asm_index`)

A lightweight, zero-dependency Python tool to index large IDA Pro disassembly text listings (`.asm`) into a SQLite database with FTS5 full-text search.

## Why this exists

Disassembly listings of 1990s DOS demos frequently exceed 40–100 MB of text with 5,000+ functions. Feeding raw listings into an AI context window is expensive, slow, and leads to hallucinations or truncation.

`asm_index` parses the listing offline once and provides a fast, bounded JSON CLI query interface. An AI agent or developer can query specific functions, immediate callers, direct callees, cross-references, or full-text searches without loading the file into memory.

## Building the Index

```powershell
python tools/asm_index/asm_index.py --db oracle/demo.sqlite build --source oracle/memory_dump.bin.asm
```

The build process:
- Scans functions (`proc`/`endp`), instructions, symbols, and cross-references, including IDA text exports that omit addresses on instruction lines.
- Populates an FTS5 virtual table for full-text searching of comments, instructions, and strings.
- Refuses to overwrite an existing database (to preserve user notes and annotations).
- Validates database integrity via SQLite `PRAGMA integrity_check` and foreign keys.

This version writes schema 2. It does not modify an existing index. Build to a new `.sqlite` path to gain line-level instructions and call references from an addressless IDA export.

## Quick Query Reference

```powershell
# Show summary statistics and source metadata
python tools/asm_index/asm_index.py stats

# List functions matching a glob pattern
python tools/asm_index/asm_index.py functions 'render_%'

# Inspect the disassembly lines of a specific function
python tools/asm_index/asm_index.py function sub_12340

# Find all callers of a function
python tools/asm_index/asm_index.py callers sub_12340

# Find all direct callees called by a function
python tools/asm_index/asm_index.py callees sub_12340

# Find all references to a data symbol or variable
python tools/asm_index/asm_index.py refs dword_A420

# View context lines around any address
python tools/asm_index/asm_index.py context 0x12340 --radius 15

# Full-text search across all listing lines (instructions, comments, strings)
python tools/asm_index/asm_index.py search '"SetMode320x200"'

# Run custom SQL queries for complex graph or data analysis
python tools/asm_index/asm_index.py sql "SELECT name, instruction_count FROM function_summary ORDER BY instruction_count DESC LIMIT 10"
```

## Schema & Tables

| Table / View | Description |
|---|---|
| `functions` | Defined `proc`/`endp` boundaries, names, and source line ranges. |
| `instructions` | IDA instruction lines: mnemonic, operands, flow kind, and indirect flag. `address` is null when IDA omitted it. |
| `symbols` | Named labels, procedures, and data definitions with line numbers. |
| `refs` | Operand mentions and direct branch/call targets. `source_line` is always present; `source_address` can be null. |
| `lines` | Verbatim text of every line in the listing with printed address and function ID. |
| `source_fts` | SQLite FTS5 full-text index for fast pattern queries. |
| `calls` | View of direct function-to-function call edges. |
| `function_summary` | View containing instruction count and outgoing call count per function. |
| `annotations` | Table for analyst/agent persistent notes and reverse-engineering findings. |
| `metadata` | Source file path, SHA-256 hash, byte length, and index schema version. |

## Important Caveats

1. **IDA Classification is an Hypothesis**: The index reflects what IDA Pro identified in the disassembly. In DOS demos, code/data classification may be imperfect. Embedded data or self-modifying code must be verified against raw runtime bytes.
2. **Addressless IDA Lines**: Many IDA text exports print addresses on labels and `proc` lines but not each instruction. This index retains those instructions and line-level call references with null source addresses. It never guesses addresses by advancing from a label. Use raw dump bytes and an address map for exact instruction addresses.
3. **Function End Addresses**: `end_address` may be inferred from the `endp` symbol and can equal the function start in an addressless export. Source line spans remain useful; the end address is not a byte extent.
4. **Indirect Calls/Jumps**: Indirect transfers (`call eax`, `jmp [table+edx*4]`) are flagged with `is_indirect = 1`. Their targets cannot be resolved statically and require runtime tracing.
