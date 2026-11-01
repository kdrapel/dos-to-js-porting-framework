"""Bounded offline x86 replay. Unsupported CPU/device/FPU state fails explicitly.

Built-in adapters: real-mode 16-bit and captured protected-mode 32-bit, no paging.
Hardware interactions and x87 need a separately verified production adapter.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from capture_corpus import CaptureCorpus, CaptureState, Region, capture_int, read_json
try:
    import unicorn as uc
    from unicorn import x86_const as x86
    UNICORN_AVAILABLE = True
except ImportError:
    UNICORN_AVAILABLE = False

REGISTER_MAP_32 = {name: 'UC_X86_REG_' + name.upper() for name in
                   ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','cs','ds','es','ss','fs','gs')}
INTEGER_EXTENDED = frozenset(range(0x40,0x50)) | frozenset(range(0x80,0xa0)) | frozenset(range(0xc8,0xd0)) | {
    0xa3,0xa4,0xa5,0xab,0xac,0xad,0xaf,0xb0,0xb1,0xb3,0xb6,0xb7,0xba,0xbb,0xbc,0xbd,0xbe,0xbf}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def find_dirty_pages(before, after, page_size=4096):
    return [{'page': p // page_size, 'address': p, 'size': min(page_size, len(before)-p)}
            for p in range(0, len(before), page_size) if before[p:p+page_size] != after[p:p+page_size]]


class UnicornCaptureRunner:
    def __init__(self, ram_path=None, registers_path=None, machine_state_path=None, linear_base=0, *, snapshot=None, mode=None):
        if not UNICORN_AVAILABLE:
            raise RuntimeError('Install offline execution dependency: python -m pip install unicorn')
        if snapshot is None:
            machine = read_json(machine_state_path)
            raw = read_json(registers_path)
            registers = {k: capture_int(v) for k,v in raw.items() if k in REGISTER_MAP_32}
            snapshot = CaptureState(Path(ram_path).parent, None, None, registers, machine,
                                    (Region(linear_base, Path(ram_path).read_bytes(), str(ram_path)),), [])
        self.snapshot = snapshot.clone()
        self.linear_base = linear_base
        self.image = self.snapshot.memory()
        self.registers, self.machine = self.snapshot.registers, self.snapshot.machine
        observed_mode = self.machine.get('cpu_mode')
        selected = mode or {'real':'real16', 'protected32':'protected32'}.get(observed_mode)
        if selected not in ('real16','protected32'):
            raise ValueError(f'CPU mode {observed_mode!r} needs an explicit verified replay adapter')
        self.mode = selected
        if observed_mode in ('real','protected16','protected32') and selected != {'real':'real16','protected16':'protected16','protected32':'protected32'}[observed_mode]:
            raise ValueError('selected adapter contradicts the captured CPU mode')
        for name in ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','cs','ds','es','ss','fs','gs'):
            if name not in self.registers:
                raise ValueError(f'missing initial register {name}')
        if self.registers['eflags'] & (1 << 17):
            raise ValueError('virtual-8086 replay needs a verified adapter')
        cr0 = capture_int(self.machine.get('cr0', 0))
        if cr0 & 0x80000000:
            raise ValueError('paging replay needs captured page tables and a verified adapter')
        if selected == 'real16' and cr0 & 1 or selected == 'protected32' and not cr0 & 1:
            raise ValueError('selected mode contradicts captured CR0')
        self.engine = uc.Uc(uc.UC_ARCH_X86, uc.UC_MODE_16 if selected == 'real16' else uc.UC_MODE_32)
        # Map merged pages, but retain byte-level coverage checks for padding and holes.
        pages = set()
        for region in self.snapshot.regions:
            pages.update(range(region.address & ~4095, (region.address + len(region.data) + 4095) & ~4095, 4096))
        for page in sorted(pages):
            self.engine.mem_map(page, 4096)
        for region in self.snapshot.regions:
            self.engine.mem_write(region.address, region.data)
        self._setup_descriptors(cr0)
        for name in ('cs','ds','es','ss','fs','gs','eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags'):
            self.engine.reg_write(getattr(x86, REGISTER_MAP_32[name]), self.registers[name])
        self.instruction_count = 0
        self.write_trace = []
        self.writes_count = 0
        self.write_digest = hashlib.sha256()
        self.stop_reason = None
        self.stop_linear = None
        self.return_target = None
        self.engine.hook_add(uc.UC_HOOK_CODE, self._instruction)
        self.engine.hook_add(uc.UC_HOOK_MEM_READ, self._read)
        self.engine.hook_add(uc.UC_HOOK_MEM_WRITE, self._write)
        self.engine.hook_add(uc.UC_HOOK_MEM_INVALID, self._invalid)

    @classmethod
    def from_capture(cls, session, capture, **options):
        return cls(snapshot=CaptureCorpus(session).load(capture), **options)

    def _setup_descriptors(self, cr0):
        if self.mode == 'real16':
            for name, segment in self.machine.get('segments', {}).items():
                if name in self.registers and capture_int(segment['base']) != self.registers[name] << 4:
                    raise ValueError('unreal-mode cached segment needs a verified adapter')
                if segment.get('limit') is not None and capture_int(segment['limit']) != 0xffff:
                    raise ValueError('nonstandard real-mode segment limit needs a verified adapter')
            self.engine.reg_write(x86.UC_X86_REG_CR0, cr0)
            return
        for table, constant in [('gdtr', x86.UC_X86_REG_GDTR), ('idtr', x86.UC_X86_REG_IDTR)]:
            state = self.machine.get(table)
            if not isinstance(state, dict):
                raise ValueError(f'missing {table}')
            base, limit = capture_int(state['base']), capture_int(state['limit'])
            if not self.image.covered(base, limit+1):
                raise ValueError(f'{table} bytes are outside captured memory')
            self.engine.reg_write(constant, (0,base,limit,0))
        self.engine.reg_write(x86.UC_X86_REG_CR0, cr0)
        for name in ('cs','ds','es','ss','fs','gs'):
            selector = self.registers[name]
            if selector & 4:
                raise ValueError('LDT replay needs a verified adapter')
            if selector:
                gdt = self.machine['gdtr']
                desc = capture_int(gdt['base']) + (selector >> 3)*8
                if desc + 7 > capture_int(gdt['base']) + capture_int(gdt['limit']):
                    raise ValueError('selector outside captured GDT')
                raw = self.image.read(desc,8)
                base = raw[2] | raw[3]<<8 | raw[4]<<16 | raw[7]<<24
                observed = self.machine.get('segments',{}).get(name,{})
                if observed.get('base') is None or capture_int(observed['base']) != base:
                    raise ValueError('cached segment does not match captured GDT descriptor')
                limit = raw[0] | raw[1]<<8 | (raw[6]&15)<<16
                if raw[6]&0x80:
                    limit = (limit<<12)|0xfff
                if observed.get('limit') is not None and capture_int(observed['limit']) != limit:
                    raise ValueError('cached segment limit does not match captured GDT descriptor')
                if observed.get('default_32bit') is not None and bool(observed['default_32bit']) != bool(raw[6]&0x40):
                    raise ValueError('cached segment size does not match captured descriptor')
                if name in ('cs','ss') and not raw[6] & 0x40:
                    raise ValueError('16-bit protected code/stack needs a verified adapter')

    def _stop(self, reason):
        self.stop_reason = reason
        self.engine.emu_stop()

    def _read(self, engine, access, address, size, value, user):
        if not self.image.covered(address,size):
            self._stop(f'uncaptured_read:{address:#x}+{size:#x}')

    def _invalid(self, engine, access, address, size, value, user):
        self._stop(f'unmapped_access:{address:#x}+{size:#x}')
        return False

    def _write(self, engine, access, address, size, value, user):
        if not self.image.covered(address,size) or size > 8:
            self._stop(f'unsupported_write:{address:#x}+{size:#x}')
            return
        value &= (1 << (size*8))-1
        self.write_digest.update(f'{address}:{size}:{value:x}\n'.encode())
        self.writes_count += 1
        if len(self.write_trace) < 100:
            self.write_trace.append({'address':address,'size':size,'value':hex(value)})

    def _instruction(self, engine, address, size, user):
        if not self.image.covered(address,size):
            self._stop(f'uncaptured_fetch:{address:#x}+{size:#x}')
            return
        if address == self.stop_linear:
            self._stop('reached_stop_address')
            return
        if self.return_target:
            target, stack, selector = self.return_target
            sp = engine.reg_read(x86.UC_X86_REG_ESP)
            if self.mode == 'real16': sp &= 0xffff
            if address == target and sp == stack and engine.reg_read(x86.UC_X86_REG_CS) == selector:
                self._stop('natural_return')
                return
        code = bytes(engine.mem_read(address,size))
        index = 0
        while index < len(code) and code[index] in (0x26,0x2e,0x36,0x3e,0x64,0x65,0x66,0x67,0xf0,0xf2,0xf3):
            index += 1
        opcode = code[index] if index < len(code) else 0
        if opcode in (0xcc,0xcd,0xce,0xcf,0xe4,0xe5,0xe6,0xe7,0xec,0xed,0xee,0xef,0x6c,0x6d,0x6e,0x6f,0xf4):
            self._stop(f'unsupported_hardware_instruction:{address:#x}')
            return
        if 0xd8 <= opcode <= 0xdf or opcode == 0x9b:
            self._stop(f'unsupported_x87_state:{address:#x}')
            return
        if opcode == 0x0f and (index+1 >= len(code) or code[index+1] not in INTEGER_EXTENDED):
            self._stop(f'unsupported_extended_cpu_state:{address:#x}')
            return
        if opcode in (0x62,0xc4,0xc5) and index+1 < len(code) and code[index+1] >= 0xc0:
            self._stop(f'unsupported_vector_state:{address:#x}')
            return
        self.instruction_count += 1

    def _base(self, name):
        if self.mode == 'real16':
            return self.registers[name] << 4
        return capture_int(self.machine['segments'][name]['base'])

    def run(self, entry_offset=None, stop_offset=None, instruction_limit=1000000, expect_return=False, *, stop_linear=None, ranges=()):
        if self.instruction_count or self.stop_reason:
            raise ValueError('runner is single-use; fork a new capture state')
        if instruction_limit <= 0:
            raise ValueError('instruction limit must be positive')
        offset = self.registers['eip'] if entry_offset is None else entry_offset
        entry = self._base('cs') + offset
        initial = dict(self.registers, eip=offset)
        self.engine.reg_write(x86.UC_X86_REG_EIP,offset)
        self.stop_linear = stop_linear if stop_linear is not None else self._base('cs') + stop_offset if stop_offset is not None else None
        if self.stop_linear is None and not expect_return:
            raise ValueError('an explicit stop or justified near-return boundary is required')
        if expect_return:
            size = 2 if self.mode == 'real16' else 4
            sp = self.registers['esp'] & (0xffff if size==2 else 0xffffffff)
            target = int.from_bytes(self.image.read(self._base('ss')+sp,size),'little')
            self.return_target = (self._base('cs')+target,(sp+size)&(0xffff if size==2 else 0xffffffff),self.registers['cs'])
        initial_hash = sha256_bytes(json.dumps({'snapshot':self.snapshot.state_hash(),'registers':initial},sort_keys=True,separators=(',',':')).encode())
        before = [bytes(self.engine.mem_read(r.address,len(r.data))) for r in self.snapshot.regions]
        try:
            endpoint = self.stop_linear if self.stop_linear is not None else self.return_target[0]
            self.engine.emu_start(entry, endpoint, count=instruction_limit)
            if self.stop_reason is None:
                pc = self.engine.reg_read(x86.UC_X86_REG_EIP) + self._base('cs')
                if self.stop_linear is not None and pc == self.stop_linear:
                    self.stop_reason = 'reached_stop_address'
                elif self.return_target is not None:
                    target, stack, selector = self.return_target
                    sp = self.engine.reg_read(x86.UC_X86_REG_ESP) & (0xffff if self.mode=='real16' else 0xffffffff)
                    self.stop_reason = ('natural_return' if pc == target and sp == stack and
                                        self.engine.reg_read(x86.UC_X86_REG_CS) == selector else
                                        'return_boundary_guard_failed' if pc == target else 'instruction_limit_reached')
                else:
                    self.stop_reason = 'instruction_limit_reached'
        except uc.UcError as exc:
            if self.stop_reason is None: self.stop_reason = f'unicorn_exception:{exc}'
        after = [bytes(self.engine.mem_read(r.address,len(r.data))) for r in self.snapshot.regions]
        final = {name:hex(self.engine.reg_read(getattr(x86,constant))) for name,constant in REGISTER_MAP_32.items()}
        memory_ranges = {}
        for region in ranges:
            address, length = int(region['address']), int(region['length'])
            if not self.image.covered(address,length):
                raise ValueError('declared output lies outside captured memory')
            data = bytes(self.engine.mem_read(address,length))
            memory_ranges[region['name']] = {'address':address,'length':length,'sha256':sha256_bytes(data)}
            if length <= 4096:
                memory_ranges[region['name']]['bytes_hex'] = data.hex()
        return {'stop_reason':self.stop_reason,'instruction_boundaries_observed':self.instruction_count,
                'initial_state_sha256':initial_hash,'initial_registers':initial,
                'final_registers':final,'initial_memory_sha256':sha256_bytes(b''.join(before)),
                'final_memory_sha256':sha256_bytes(b''.join(after)), 'memory_ranges':memory_ranges,
                'writes_count':self.writes_count,'write_trace_sha256':self.write_digest.hexdigest(),
                'write_trace_complete':self.stop_reason in ('reached_stop_address','natural_return'),
                'write_trace_preview':self.write_trace, 'write_trace_kind':'Unicorn pre-write callbacks', 'capture':self.snapshot.capture,
                'cpu_adapter':self.mode, 'reference_engine':{'name':'Unicorn','version':uc.__version__},
                'state_limits':['no hardware, paging, LDT, protected16 or x87 adapter'],
                'evidence_class':'bounded_original_execution'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--session');source.add_argument('--ram')
    parser.add_argument('--capture');parser.add_argument('--registers');parser.add_argument('--machine')
    parser.add_argument('--base',default='0');parser.add_argument('--mode',choices=['real16','protected32'])
    parser.add_argument('--entry');parser.add_argument('--stop');parser.add_argument('--limit',type=int,default=1000000)
    parser.add_argument('--expect-return',action='store_true');parser.add_argument('--output')
    args=parser.parse_args()
    if args.session:
        if args.capture is None: parser.error('--session requires an agent-selected --capture')
        runner=UnicornCaptureRunner.from_capture(args.session,args.capture,mode=args.mode)
    else:
        if not args.registers or not args.machine: parser.error('--ram requires --registers and --machine')
        runner=UnicornCaptureRunner(args.ram,args.registers,args.machine,int(args.base,0),mode=args.mode)
    result=runner.run(int(args.entry,0) if args.entry else None,int(args.stop,0) if args.stop else None,args.limit,args.expect_return)
    output=json.dumps(result,indent=2)
    if args.output: Path(args.output).write_text(output,encoding='utf-8')
    print(output)
    return 0 if result['stop_reason'] in ('reached_stop_address','natural_return') else 2


if __name__=='__main__': raise SystemExit(main())
