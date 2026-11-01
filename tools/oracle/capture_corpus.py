"""Read immutable capture sessions and fork covered memory for offline experiments."""
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import copy


def capture_int(value):
    """DOSBox address/register strings are hexadecimal even without 0x."""
    if isinstance(value, bool):
        raise ValueError('boolean is not capture state')
    return int(value, 16) if isinstance(value, str) else int(value)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def asset_path(directory, name):
    path = (directory / name).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError('asset path escapes its capture directory')
    return path


@dataclass(frozen=True)
class Region:
    address: int
    data: bytes
    source: str


class MemoryImage:
    def __init__(self, regions):
        self.regions = sorted([(r.address, bytearray(r.data)) for r in regions], key=lambda pair: pair[0])

    def covered(self, address, size):
        if address < 0 or size < 0:
            return False
        end = address + size
        for start, data in self.regions:
            if start > address:
                break
            if start <= address < start + len(data):
                address = min(end, start + len(data))
            if address == end:
                return True
        return size == 0

    def read(self, address, size):
        if not self.covered(address, size):
            raise ValueError(f'uncaptured memory range {address:#x}+{size:#x}')
        result = bytearray()
        end = address + size
        while address < end:
            start, data = next((s, d) for s, d in self.regions if s <= address < s + len(d))
            count = min(end - address, start + len(data) - address)
            result.extend(data[address - start:address - start + count])
            address += count
        return bytes(result)

    def write(self, address, data):
        if not self.covered(address, len(data)):
            raise ValueError('write outside captured memory')
        end = address + len(data)
        # Update every alias, so overlapping selector dumps remain coherent.
        for start, buffer in self.regions:
            lo, hi = max(address, start), min(end, start + len(buffer))
            if lo < hi:
                buffer[lo - start:hi - start] = data[lo - address:hi - address]

    def clone(self):
        return MemoryImage([Region(start, bytes(data), 'working clone') for start, data in self.regions])


@dataclass
class CaptureState:
    directory: Path
    capture: object
    elapsed_us: object
    registers: dict
    machine: dict
    regions: tuple
    warnings: list
    auxiliary: dict = field(default_factory=dict)

    def clone(self):
        return copy.deepcopy(self)

    def memory(self):
        return MemoryImage(self.regions)

    def state_hash(self):
        summary = {'registers': self.registers, 'machine': self.machine,
                   'auxiliary': {name: {k: v for k, v in asset.items() if k != 'path'} for name, asset in self.auxiliary.items()},
                   'regions': [{'address': r.address, 'length': len(r.data),
                                'sha256': hashlib.sha256(r.data).hexdigest()} for r in self.regions]}
        return hashlib.sha256(json.dumps(summary, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class CaptureCorpus:
    def __init__(self, session):
        self.session = Path(session).resolve()
        self.manifests = sorted(self.session.glob('*/capture.json'))
        if not self.manifests:
            raise ValueError('no completed capture directories found')
        self.entries = [(path, read_json(path)) for path in self.manifests]

    def load(self, capture):
        candidates = []
        for path, meta in self.entries:
            if str(meta.get('capture')) == str(capture) or path.parent.name == str(capture):
                candidates.append((path, meta))
        if len(candidates) != 1:
            raise ValueError(f'capture {capture!r} is absent or ambiguous')
        path, manifest = candidates[0]
        directory, assets = path.parent, manifest.get('assets', {})

        def load_asset(name):
            asset = assets.get(name, {})
            if asset.get('status') not in ('complete', 'ok') or not asset.get('file'):
                raise ValueError(f'{name} is not a readable completed asset')
            target = asset_path(directory, asset['file'])
            if target.stat().st_size != asset.get('size'):
                raise ValueError(f'{name} file size mismatch')
            return read_json(target)

        raw_registers, machine = load_asset('registers'), load_asset('machine_state')
        if not isinstance(raw_registers, dict) or not isinstance(machine, dict):
            raise ValueError('register and machine assets must be objects')
        registers = {key.lower(): capture_int(value) for key, value in raw_registers.items()
                     if key.lower() in ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp', 'eip',
                                        'eflags', 'cs', 'ds', 'es', 'ss', 'fs', 'gs')}
        segments = machine.get('segments', {})
        bases = {}
        for name, segment in segments.items():
            if isinstance(segment, dict) and segment.get('base') is not None and segment.get('selector') is not None:
                selector, base = capture_int(segment['selector']), capture_int(segment['base'])
                if name in registers and registers[name] != selector:
                    raise ValueError(f'{name} selector changed between captured assets')
                if selector in bases and bases[selector] != base:
                    raise ValueError('conflicting cached bases for one selector')
                bases[selector] = base
        regions, warnings = [], []
        for name, asset in assets.items():
            if asset.get('segment') is None or asset.get('offset') is None:
                continue
            if asset.get('status') not in ('complete', 'ok'):
                warnings.append(f'{name}: excluded {asset.get("status")} memory')
                continue
            selector = capture_int(asset['segment'])
            if selector not in bases:
                warnings.append(f'{name}: excluded memory without a proven selector base')
                continue
            target = asset_path(directory, asset['file'])
            data = target.read_bytes()
            if len(data) != asset.get('size') or len(data) != asset.get('expected_size', len(data)):
                raise ValueError(f'{name}: memory size mismatch')
            address = bases[selector] + capture_int(asset['offset'])
            for existing in regions:
                lo, hi = max(address, existing.address), min(address + len(data), existing.address + len(existing.data))
                if lo < hi and data[lo-address:hi-address] != existing.data[lo-existing.address:hi-existing.address]:
                    raise ValueError('overlapping memory assets disagree')
            regions.append(Region(address, data, str(target)))
        if not regions:
            raise ValueError('this checkpoint has no usable memory; select another full-run checkpoint')
        auxiliary = {}
        for name, asset in assets.items():
            if name in ('registers', 'machine_state') or asset.get('segment') is not None:
                continue
            if asset.get('status') not in ('complete', 'ok') or not asset.get('file'):
                auxiliary[name] = {'status': asset.get('status')}
                continue
            target = asset_path(directory, asset['file'])
            data = target.read_bytes()
            if len(data) != asset.get('size'):
                raise ValueError(f'{name}: auxiliary state size mismatch')
            auxiliary[name] = {'path': str(target), 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'status':asset['status']}
        return CaptureState(directory, manifest.get('capture'), manifest.get('time', {}).get('process_elapsed_us'),
                            registers, machine, tuple(sorted(regions, key=lambda r: r.address)), warnings, auxiliary)

    def checkpoints(self):
        for path, meta in self.entries:
            capture = meta.get('capture', path.parent.name)
            try:
                state = self.load(capture)
                yield {'capture': capture, 'elapsed_us': state.elapsed_us, 'usable': True,
                       'regions': [{'address': r.address, 'length': len(r.data)} for r in state.regions],
                       'warnings': state.warnings}
            except (OSError, ValueError, KeyError, TypeError) as exc:
                yield {'capture': capture, 'usable': False, 'reason': str(exc)}
