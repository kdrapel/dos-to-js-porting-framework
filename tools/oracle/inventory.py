"""Generic Capture Corpus Inventory and Provenance Validator.

Scans captured DOSBox/DOSBox-X snapshots, hashes root files, validates asset
integrity, and outputs an inventory JSON report for reproducibility.
Does NOT run an emulator.
"""
import argparse
import collections
import hashlib
import json
import sqlite3
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def inventory_session(root_dir, session_dir, output_file=None):
    root = Path(root_dir).resolve()
    session = Path(session_dir).resolve()
    if not session.is_dir():
        raise SystemExit(f"Session directory not found: {session}")

    report = {
        'schema_version': 1,
        'scope': 'Offline capture inventory and provenance validation',
        'session_path': str(session.relative_to(root) if session.is_relative_to(root) else session),
        'root_inputs': [],
        'index': {},
        'session_metadata': {},
        'captures': [],
        'errors': [],
        'warnings': []
    }

    # Hash files in original/ and oracle/
    candidate_paths = list((root / 'original').glob('*')) if (root / 'original').is_dir() else []
    candidate_paths += [p for p in (root / 'oracle').glob('*.bin*') if p.is_file()] if (root / 'oracle').is_dir() else []
    
    for path in sorted(candidate_paths):
        if path.is_file() and path.stat().st_size < 200 * 1024 * 1024:  # Skip gigantic blobs >200MB if needed
            rel = str(path.relative_to(root))
            report['root_inputs'].append({
                'path': rel,
                'bytes': path.stat().st_size,
                'sha256': digest(path)
            })

    # Check for sqlite assembly index
    sqlite_files = list((root / 'oracle').glob('*.sqlite')) if (root / 'oracle').is_dir() else []
    if sqlite_files:
        db_path = sqlite_files[0]
        try:
            with sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True) as db:
                report['index']['database'] = str(db_path.relative_to(root))
                report['index']['metadata'] = dict(db.execute('SELECT key, value FROM metadata'))
                report['index']['counts'] = {
                    table: db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                    for table in ['lines', 'symbols', 'functions', 'instructions', 'refs']
                }
        except Exception as e:
            report['warnings'].append(f"Failed to inspect SQLite index {db_path.name}: {e}")

    # Load session.json if present
    session_json = session / 'session.json'
    if session_json.is_file():
        report['session_metadata'] = load_json(session_json)
    else:
        report['warnings'].append('session.json is missing; session finalization and capture count cannot be verified')

    # Scan captures
    manifests = sorted(session.glob('capture_*/capture.json'))
    if not manifests:
        manifests = sorted(session.glob('*/capture.json'))

    cores = collections.Counter()
    cycles = collections.Counter()
    bases = collections.Counter()

    for manifest in manifests:
        try:
            data = load_json(manifest)
            boundary = data.get('captureBoundary', {})
            execution = data.get('execution', {})
            cpu = data.get('cpu', {})
            assets = data.get('assets', {})
            elapsed = data.get('time', {}).get('process_elapsed_us')
            
            row = {
                'capture': data.get('capture'),
                'path': str(manifest.parent.relative_to(root) if manifest.is_relative_to(root) else manifest.parent),
                'status': data.get('status'),
                'elapsed_us': elapsed,
                'cpu_mode': cpu.get('mode') or cpu.get('cpu_mode'),
                'boundary': {
                    'kind': boundary.get('kind'),
                    'cpu_core': boundary.get('cpu_core'),
                    'cpu_trace_incomplete': boundary.get('cpu_trace_incomplete'),
                    'dropped_events': boundary.get('dropped_events')
                },
                'asset_errors': [],
                'memory_regions': []
            }

            for name, asset in assets.items():
                if asset.get('segment') is not None and asset.get('offset') is not None:
                    row['memory_regions'].append({
                        'name': name,
                        'segment': asset['segment'],
                        'offset': asset['offset'],
                        'requested_bytes': asset.get('expected_size'),
                        'actual_bytes': asset.get('size'),
                        'status': asset.get('status'),
                        'error': asset.get('error')
                    })
                if asset.get('status') in ('partial', 'error', 'unavailable'):
                    detail = asset.get('error') or asset.get('reason') or 'no detail supplied'
                    report['warnings'].append(
                        f"Capture {row['capture']} asset {name}: {asset['status']}: {detail}")
                filename = asset.get('file')
                if not filename:
                    continue
                asset_path = manifest.parent / filename
                if not asset_path.is_file():
                    row['asset_errors'].append(f'{name}: missing file {filename}')
                elif asset.get('size') is not None and asset_path.stat().st_size != asset['size']:
                    row['asset_errors'].append(f'{name}: size mismatch (declared {asset["size"]}, actual {asset_path.stat().st_size})')

            cores[str(boundary.get('cpu_core'))] += 1
            cycles[(cpu.get('cycle_mode'), cpu.get('configured_cycles'))] += 1
            bases[str(execution.get('selector_base'))] += 1

            report['captures'].append(row)
            if row['asset_errors']:
                report['errors'].extend(f"Capture {row['capture']}: {err}" for err in row['asset_errors'])
        except Exception as e:
            report['errors'].append(f"{manifest.name}: {e}")

    report['summary'] = {
        'total_captures': len(report['captures']),
        'cpu_cores': dict(cores),
        'selector_bases': dict(bases)
    }

    metadata = report['session_metadata']
    if metadata:
        status = metadata.get('status')
        if status != 'stopped':
            report['warnings'].append(
                f'session.json status is {status!r}, not stopped; the session may not have been finalized')
        declared = metadata.get('captures')
        if isinstance(declared, int) and declared != len(report['captures']):
            report['warnings'].append(
                f'session.json declares {declared} captures, but {len(report["captures"])} capture manifests exist')
        if status == 'stopped' and not metadata.get('stop_reason'):
            report['warnings'].append('session.json has no stop_reason for a stopped session')

    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f"Inventory saved to {out_path}")
    else:
        print(json.dumps(report, indent=2))

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.', help='Project root directory')
    parser.add_argument('--session', required=True, help='Path to capture session directory (e.g. oracle/extract/...)')
    parser.add_argument('--output', default=None, help='Output report JSON path')
    args = parser.parse_args()
    inventory_session(args.root, args.session, args.output)


if __name__ == '__main__':
    main()
