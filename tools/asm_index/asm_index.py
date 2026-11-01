"""Lossless IDA text index and bounded, JSON query interface (Python standard library only).

Indexes large IDA Pro disassembly listings (.asm) into an SQLite database with FTS5
full-text search, symbol tables, cross-references, call graphs, and instruction flows.
Provides bounded JSON queries suited for AI context windows and offline tooling.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ADDRESS = re.compile(r'^([0-9A-Fa-f]{8,16})(?:\s+|$)(.*)$')
TOKEN = re.compile(r'\b[A-Za-z_?$@][\w?$@]*\b')
DATA = {'db', 'dw', 'dd', 'dq', 'dt', 'do', 'dy', 'dz', 'align', 'unicode'}
DIRECTIVES = DATA | {'proc', 'endp', 'equ', 'segment', 'ends', 'assume', 'end', 'org', 'public', 'extrn', 'include', 'use16', 'use32'}


def code_part(text):
    # Semicolons inside quoted strings are not comments; doubled quotes are handled safely.
    return re.split(r";(?=(?:[^']*'[^']*')*[^']*$)", text, maxsplit=1)[0].strip()


def parse(text):
    match = ADDRESS.match(text)
    address, body = (int(match[1], 16), match[2]) if match else (None, text)
    body = code_part(body)
    symbol = None
    label = re.match(r'^([\w?$@]+):\s*(.*)$', body)
    if label:
        symbol, body = label.groups()
    parts = body.split(None, 2)
    if len(parts) >= 2 and parts[1].lower() in DIRECTIVES:
        symbol = parts[0]
        body = ' '.join(parts[1:])
    # The first symbol or data declaration on a line may lack an explicit printed address.
    if address is None and symbol:
        suffix = re.search(r'_([0-9A-Fa-f]+)$', symbol)
        if suffix:
            address = int(suffix[1], 16)
    parts = body.split(None, 1)
    return address, symbol, parts[0].lower() if parts else '', parts[1] if len(parts) > 1 else ''


def flow(mnemonic):
    if mnemonic in {'call', 'callf'}:
        return 'call'
    if mnemonic in {'jmp', 'jmpf'} or mnemonic.startswith('j') or mnemonic.startswith('loop'):
        return 'jump'
    if mnemonic.startswith('ret') or mnemonic in {'iret', 'iretd', 'iretq'}:
        return 'return'
    return 'ordinary'


def build(source, destination):
    source = Path(source)
    destination = Path(destination)
    if not source.is_file():
        raise SystemExit(f'Source listing not found: {source}')
    if destination.exists():
        raise SystemExit(f'Refusing to overwrite {destination}; specify a new --db path (annotations may exist).')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.building')
    if temporary.exists():
        raise SystemExit(f'Remove or inspect interrupted build {temporary} before retrying.')
    
    schema_path = Path(__file__).with_name('schema.sql')
    if not schema_path.is_file():
        raise SystemExit(f'Schema file not found at {schema_path}')
        
    db = sqlite3.connect(temporary)
    try:
        db.executescript(schema_path.read_text(encoding='utf-8'))
        current = None
        digest = hashlib.sha256()
        with source.open('rb') as stream, db:
            for number, raw in enumerate(stream, 1):
                digest.update(raw)
                text = raw.decode('utf-8-sig' if number == 1 else 'utf-8', errors='replace').rstrip('\r\n')
                address, symbol, mnemonic, operands = parse(text)
                if mnemonic == 'proc' and symbol and address is not None:
                    if current is not None:
                        raise ValueError(f'Nested function at line {number}')
                    current = db.execute('INSERT INTO functions(name,start_address,start_line) VALUES (?,?,?)', (symbol, address, number)).lastrowid
                db.execute('INSERT INTO lines VALUES (?,?,?,?)', (number, address, current, text))
                if symbol and address is not None and mnemonic != 'endp':
                    kind = 'function' if mnemonic == 'proc' else 'data' if mnemonic in DATA else 'label'
                    db.execute('INSERT INTO symbols VALUES (?,?,?,?,?)', (symbol, address, kind, number, current))
                if mnemonic and mnemonic not in DIRECTIVES and re.match(r'^[a-z][a-z0-9]*$', mnemonic):
                    # IDA's ordinary text export often prints addresses only on
                    # labels/proc lines. Keep the instruction and its source line,
                    # but never invent an address for an unaddressed instruction.
                    db.execute('INSERT INTO instructions(address,line_number,function_id,mnemonic,operands,flow_kind,is_indirect) VALUES (?,?,?,?,?,?,0)', (address, number, current, mnemonic, operands, flow(mnemonic)))
                if mnemonic == 'endp' and current is not None:
                    db.execute('UPDATE functions SET end_address=?,end_line=? WHERE id=?', (address, number, current))
                    current = None
            if current is not None:
                raise ValueError('Unclosed function at end of listing')
            symbols = dict(db.execute('SELECT name,address FROM symbols'))
            # Resolve operand references, ignoring comments and literal strings.
            for line, address, owner, text in db.execute('SELECT l.line_number,l.address,l.function_id,l.text FROM lines l JOIN instructions i ON i.line_number=l.line_number'):
                _, _, mnemonic, operands = parse(text)
                if not mnemonic or mnemonic in {'proc', 'endp'}:
                    continue
                clean = re.sub(r"'[^']*'|\"[^\"]*\"", '', operands)
                names = list(dict.fromkeys(n for n in TOKEN.findall(clean) if n in symbols))
                kind = flow(mnemonic)
                control = kind in {'call', 'jump'}
                direct = re.fullmatch(r'(?:(?:short|near ptr|far ptr)\s+)?([\w?$@]+)', clean.strip(), re.I)
                direct_name = direct[1] if direct else None
                for name in names:
                    ref_kind = kind if control and direct_name == name else 'address' if re.search(r'\boffset\b', clean, re.I) else 'operand'
                    db.execute('INSERT INTO refs(source_address,source_line,source_function,target_address,target_symbol,kind,expression) VALUES (?,?,?,?,?,?,?)', (address, line, owner, symbols[name], name, ref_kind, operands))
                if control:
                    numeric = re.fullmatch(r'(?:short\s+)?(?:0x([0-9a-f]+)|([0-9][0-9a-f]*)h)', clean.strip(), re.I)
                    if numeric:
                        target = int(numeric[1] or numeric[2], 16)
                        db.execute('INSERT INTO refs(source_address,source_line,source_function,target_address,kind,expression) VALUES (?,?,?,?,?,?)', (address, line, owner, target, kind, operands))
                    elif direct_name not in symbols:
                        db.execute('UPDATE instructions SET is_indirect=1 WHERE line_number=?', (line,))
            db.execute("INSERT INTO source_fts(source_fts) VALUES ('rebuild')")
            db.executemany('INSERT INTO metadata VALUES (?,?)', [
                ('schema_version', '2'),
                ('source_path', str(source.resolve())),
                ('source_sha256', digest.hexdigest()),
                ('source_bytes', str(source.stat().st_size)),
                ('function_policy', 'Explicit IDA proc/endp only; source line spans are authoritative. End address may be inferred from a symbol and is not a byte extent.'),
                ('instruction_address_policy', 'NULL when IDA does not print an instruction address; no address is inferred from nearby labels')
            ])
        db.execute('ANALYZE')
        db.commit()
        result = db.execute('PRAGMA integrity_check').fetchone()[0]
        if result != 'ok' or db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Index integrity check failed: ' + result)
        db.close()
        temporary.rename(destination)
    except BaseException:
        db.close()
        raise
    return {'database': str(destination), 'source_sha256': digest.hexdigest(), 'source_bytes': source.stat().st_size}


def address_of(db, value):
    row = db.execute('SELECT address FROM symbols WHERE name=?', (value,)).fetchone()
    if row:
        return row[0]
    try:
        return int(value.lower().removeprefix('0x').removesuffix('h'), 16)
    except ValueError:
        raise ValueError(f'Unknown symbol or invalid hexadecimal address: {value}') from None


def query(args):
    db_path = Path(args.db)
    if not db_path.is_file():
        raise SystemExit(f'Index database not found: {db_path}. Build it first with `asm_index.py build --source <file.asm>`')
    with closing(sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        return query_connection(db, args)


def query_connection(db, args):
    db.row_factory = sqlite3.Row
    limit = args.limit
    if args.command == 'stats':
        return {
            'counts': {t: db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ['lines', 'symbols', 'functions', 'instructions', 'refs']},
            'unowned_instructions': db.execute('SELECT count(*) FROM instructions WHERE function_id IS NULL').fetchone()[0],
            'indirect_transfers': db.execute('SELECT count(*) FROM instructions WHERE is_indirect=1').fetchone()[0],
            'metadata': dict(db.execute('SELECT * FROM metadata'))
        }
    if args.command == 'sql':
        sql, parameters = args.expression, ()
    elif args.command == 'search':
        sql, parameters = 'SELECT l.* FROM source_fts JOIN lines l ON l.line_number=source_fts.rowid WHERE source_fts MATCH ? ORDER BY rank', (args.expression,)
    elif args.command == 'functions':
        sql, parameters = 'SELECT * FROM function_summary WHERE name LIKE ? ORDER BY start_address', (args.expression or '%',)
    else:
        address = address_of(db, args.expression)
        if args.command == 'function':
            row = db.execute('SELECT * FROM functions WHERE start_address<=? AND end_address>=? ORDER BY start_address DESC LIMIT 1', (address, address)).fetchone()
            if not row:
                return {'address': address, 'function': None, 'hint': 'No explicit IDA function covers this address; use context.'}
            sql, parameters = 'SELECT * FROM lines WHERE function_id=? ORDER BY line_number', (row['id'],)
        elif args.command == 'context':
            row = db.execute('SELECT line_number FROM lines WHERE address<=? ORDER BY address DESC,line_number LIMIT 1', (address,)).fetchone()
            if not row:
                return []
            sql, parameters = 'SELECT * FROM lines WHERE line_number BETWEEN ? AND ? ORDER BY line_number', (max(1, row[0] - args.radius), row[0] + args.radius)
        elif args.command == 'refs':
            sql, parameters = 'SELECT * FROM refs WHERE target_address=? ORDER BY source_address', (address,)
        elif args.command == 'callees':
            sql, parameters = 'SELECT * FROM calls WHERE source_function=(SELECT id FROM functions WHERE start_address<=? AND end_address>=? ORDER BY start_address DESC LIMIT 1) ORDER BY source_address', (address, address)
        elif args.command == 'callers':
            sql, parameters = "SELECT * FROM refs WHERE target_address=? AND kind='call' ORDER BY source_address", (address,)
    cursor = db.execute(sql, parameters)
    if args.offset:
        cursor.fetchmany(args.offset)
    rows = cursor.fetchmany(limit + 1)
    return {'rows': [dict(r) for r in rows[:limit]], 'truncated': len(rows) > limit, 'limit': limit, 'offset': args.offset}


def discover_defaults():
    # Look for sqlite or asm files in oracle/
    cwd = Path.cwd()
    oracle_dir = cwd / 'oracle'
    default_db = oracle_dir / 'listing.sqlite'
    default_source = oracle_dir / 'listing.asm'
    if oracle_dir.is_dir():
        sqlite_files = list(oracle_dir.glob('*.sqlite'))
        if sqlite_files:
            default_db = sqlite_files[0]
        asm_files = list(oracle_dir.glob('*.asm'))
        if asm_files:
            default_source = asm_files[0]
    return default_db, default_source


def main():
    default_db, default_source = discover_defaults()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=default_db, help=f'Path to SQLite database (default: {default_db})')
    parser.add_argument('--limit', type=int, default=80, help='Maximum rows to return in query (default: 80)')
    parser.add_argument('--offset', type=int, default=0, help='Query pagination offset (default: 0)')
    sub = parser.add_subparsers(dest='command', required=True)
    
    p = sub.add_parser('build', help='Build SQLite index from an IDA assembly listing')
    p.add_argument('--source', type=Path, default=default_source, help=f'Source .asm file (default: {default_source})')
    
    sub.add_parser('stats', help='Show index counts and source metadata')
    for name in ['functions', 'function', 'context', 'refs', 'callers', 'callees', 'search', 'sql']:
        p = sub.add_parser(name, help=f'Query {name}')
        p.add_argument('expression', nargs='?' if name == 'functions' else None, help='Symbol, address, search pattern, or SQL')
        if name == 'context':
            p.add_argument('--radius', type=int, default=12, help='Line radius around address')
            
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000:
        parser.error('--limit must be between 1 and 10000')
    if args.offset < 0:
        parser.error('--offset must be nonnegative')
        
    try:
        result = build(args.source, args.db) if args.command == 'build' else query(args)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f'Error: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
