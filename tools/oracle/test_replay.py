import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from capture_corpus import CaptureCorpus, CaptureState, Region
from unicorn_runner import UnicornCaptureRunner, UNICORN_AVAILABLE


def make_state(protected=False, code=None):
    data=bytearray(4096)
    if code is None:
        code=(bytes.fromhex('B8010000000502000000A30002000090') if protected else bytes.fromhex('B80100050200A3000290'))
    data[0x100:0x100+len(code)]=code
    regs={name:0 for name in ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','cs','ds','es','ss','fs','gs')}
    regs.update(eip=0x100,esp=0x800,eflags=0x202)
    segments={name:{'selector':'0000','base':'00000000'} for name in ('cs','ds','es','ss','fs','gs')}
    machine={'cpu_mode':'real','cr0':'00000000','segments':segments}
    if protected:
        data[0x508:0x510]=bytes.fromhex('FFFF0000009ACF00')
        data[0x510:0x518]=bytes.fromhex('FFFF00000092CF00')
        regs.update(cs=8,ds=16,es=16,ss=16)
        for name in ('cs','ds','es','ss'): segments[name]['selector']=f'{regs[name]:04X}'
        machine.update(cpu_mode='protected32',cr0='00000001',gdtr={'base':'00000500','limit':'0017'},idtr={'base':'00000000','limit':'0000'})
    return CaptureState(Path('.'),0,0,regs,machine,(Region(0,bytes(data),'synthetic CPU regression fixture'),),[])


@unittest.skipUnless(UNICORN_AVAILABLE,'Unicorn is required for CPU replay tests')
class ReplayTests(unittest.TestCase):
    def test_real16_and_protected32_use_original_bytes_and_stop_before_boundary(self):
        for protected in (False,True):
            with self.subTest(protected=protected):
                state=make_state(protected)
                runner=UnicornCaptureRunner(snapshot=state)
                report=runner.run(stop_linear=0x10f if protected else 0x109,ranges=[{'name':'output','address':0x200,'length':4 if protected else 2}])
                self.assertEqual(report['stop_reason'],'reached_stop_address')
                self.assertEqual(report['final_registers']['eax'],'0x3')
                self.assertEqual(int(report['final_registers']['eflags'],16) & 0x8d5,0x4)
                self.assertEqual(report['writes_count'],1)
                self.assertTrue(report['write_trace_complete'])
                self.assertEqual(state.memory().read(0x200,4),bytes(4),'snapshot remains immutable')

    def test_hardware_and_fpu_are_explicit_unsupported_boundaries(self):
        for code,prefix in [('EC90','unsupported_hardware'),('D9E890','unsupported_x87'),('0F57C090','unsupported_extended')]:
            runner=UnicornCaptureRunner(snapshot=make_state(code=bytes.fromhex(code)))
            report=runner.run(stop_linear=0x110)
            self.assertTrue(report['stop_reason'].startswith(prefix),report)
            self.assertFalse(report['write_trace_complete'])

    def test_instruction_limit_is_not_a_successful_return(self):
        runner=UnicornCaptureRunner(snapshot=make_state(code=bytes.fromhex('EBFE')))
        report=runner.run(stop_linear=0x110,instruction_limit=10)
        self.assertEqual(report['stop_reason'],'instruction_limit_reached')

    def test_near_return_requires_the_saved_target_and_stack(self):
        for code,expected in [('C3','natural_return'),('E97D00','return_boundary_guard_failed')]:
            state=make_state(code=bytes.fromhex(code))
            data=bytearray(state.regions[0].data);data[0x800:0x802]=(0x180).to_bytes(2,'little')
            state.regions=(Region(0,bytes(data),'return fixture'),)
            result=UnicornCaptureRunner(snapshot=state).run(expect_return=True)
            self.assertEqual(result['stop_reason'],expected)

    def test_padding_inside_mapped_page_cannot_supply_missing_input(self):
        state=make_state(code=bytes.fromhex('A1000390'))
        state.regions=(Region(0x100,state.regions[0].data[0x100:0x104],'code only'),)
        report=UnicornCaptureRunner(snapshot=state).run(stop_linear=0x103)
        self.assertTrue(report['stop_reason'].startswith('uncaptured_read'))


class CorpusFixture:
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.session=Path(self.temp.name)/'session'; self.directory=self.session/'capture_000000'
        self.directory.mkdir(parents=True)
        state=make_state()
        registers={name:f'{value:08X}' for name,value in state.registers.items()}
        self.assets={}
        for name,value in [('registers',registers),('machine_state',state.machine)]:
            path=self.directory/f'{name}.json';path.write_text(json.dumps(value))
            self.assets[name]={'file':path.name,'size':path.stat().st_size,'status':'complete'}
        path=self.directory/'memory.bin';path.write_bytes(state.regions[0].data)
        self.assets['memory']={'file':path.name,'size':4096,'expected_size':4096,'segment':'0000','offset':'00000000','status':'complete'}
        self.save()

    def save(self):
        (self.directory/'capture.json').write_text(json.dumps({'capture':0,'time':{'process_elapsed_us':0},'assets':self.assets}))


class CorpusTests(CorpusFixture, unittest.TestCase):
    def test_register_strings_are_hex_and_memory_forks_are_independent(self):
        corpus=CaptureCorpus(self.session);state=corpus.load(0)
        self.assertEqual(state.registers['eip'],0x100)
        a,b=state.memory(),state.memory();a.write(0x200,b'abc')
        self.assertEqual(b.read(0x200,3),bytes(3))
        self.assertFalse(b.covered(4095,2))

    def test_partial_memory_is_not_zero_filled_into_a_valid_snapshot(self):
        self.assets['memory']['status']='partial';self.save()
        with self.assertRaisesRegex(ValueError,'no usable memory'):CaptureCorpus(self.session).load(0)

    def test_conflicting_overlapping_assets_are_rejected(self):
        (self.directory/'alias.bin').write_bytes(bytes([255])*4096)
        self.assets['alias']=dict(self.assets['memory'],file='alias.bin');self.save()
        with self.assertRaisesRegex(ValueError,'overlapping'):CaptureCorpus(self.session).load(0)

    def test_missing_ram_checkpoint_remains_visible_in_coverage_listing(self):
        del self.assets['memory'];self.save()
        rows=list(CaptureCorpus(self.session).checkpoints())
        self.assertFalse(rows[0]['usable'])
