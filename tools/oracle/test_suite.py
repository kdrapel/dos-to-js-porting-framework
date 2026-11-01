import json
from pathlib import Path
import sys
import tempfile
import unittest

from replay_suite import run_suite
from test_replay import CorpusFixture
from unicorn_runner import UNICORN_AVAILABLE


@unittest.skipUnless(UNICORN_AVAILABLE, 'Unicorn needed for end-to-end suite')
class SuiteTests(CorpusFixture, unittest.TestCase):
    def test_python_reference_and_real_node_driver_agree_on_capture_fixture(self):
        work=Path(self.temp.name)
        contract={'schema_version':1,'evidence_class':'routine','registers':['eax'], 'flags_mask':'0x8d5',
                  'memory_ranges':[{'name':'output','address':'0x200','length':2}], 'ordered_writes':True,
                  'stop_reasons':{'reference':['reached_stop_address'],'javascript':['completed']}}
        (work/'contract.json').write_text(json.dumps(contract))
        helper=(Path(__file__).parent/'report.mjs').resolve().as_uri()
        # An independent translation of this tiny CPU fixture, not an emulator or reference-output copy.
        (work/'translated.mjs').write_text(f'''
import {{loadCaseInput, finishCase, saveReport}} from {json.dumps(helper)};
const state = await loadCaseInput(process.argv[2]);
state.registers.eax = 1 + 2;
state.registers.eflags = 0x206;
state.memory.write(0x200, new Uint8Array([state.registers.eax, 0]));
await saveReport(process.argv[3], finishCase(state, {{stopReason:'completed'}}));
''')
        plan={'required_stages':['routine'],'cases':[{'name':'tiny real input','stage':'routine','capture':0,
              'contract':'contract.json','stop_linear':'0x109','javascript_command':['node','translated.mjs','{input}','{output}']}]}
        path=work/'plan.json';path.write_text(json.dumps(plan))
        before={p:p.read_bytes() for p in self.session.rglob('*') if p.is_file()}
        summary=run_suite(self.session,path,work/'results')
        self.assertEqual(summary['verdict'],'PASS',summary)
        self.assertEqual(before,{p:p.read_bytes() for p in self.session.rglob('*') if p.is_file()})
        with self.assertRaisesRegex(ValueError,'unused'):run_suite(self.session,path,work/'results')
        plan['required_stages']=['routine','scene'];path.write_text(json.dumps(plan))
        summary=run_suite(self.session,path,work/'other-results')
        self.assertEqual(summary['verdict'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(summary['missing_stages'],['scene'])

    def test_missing_input_cannot_become_a_passing_case(self):
        work=Path(self.temp.name)
        plan={'required_stages':['routine'],'cases':[{'name':'missing checkpoint','stage':'routine','capture':99}]}
        path=work/'plan.json';path.write_text(json.dumps(plan))
        report=run_suite(self.session,path,work/'missing-results')
        self.assertEqual(report['verdict'],'INSUFFICIENT_EVIDENCE')

    def test_suite_cannot_write_into_a_capture_session(self):
        work=Path(self.temp.name)
        path=work/'plan.json';path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'unused'):run_suite(self.session,path,self.session/'new')

    def test_controlled_scene_stream_keeps_dependent_state_and_checks_ending(self):
        work=Path(self.temp.name)
        data=bytearray((self.directory/'memory.bin').read_bytes())
        data[0x100:0x105]=bytes.fromhex('FF06000290') # inc word [0x200], stop-before NOP
        (self.directory/'memory.bin').write_bytes(data)
        contract={'schema_version':1,'evidence_class':'controlled scene fixture',
                  'memory_ranges':[{'name':'counter','address':512,'length':2}],
                  'stop_reasons':{'reference':['frame_complete'],'javascript':['frame_complete']}}
        (work/'contract.json').write_text(json.dumps(contract))
        helper=(Path(__file__).parent/'report.mjs').resolve().as_uri()
        (work/'scene.mjs').write_text(f'''
import {{writeFile}} from 'node:fs/promises';
import {{loadCaseInput, finishCase}} from {json.dumps(helper)};
const state=await loadCaseInput(process.argv[2]); const frames=[];
for(let tick=1;tick<=3;tick++){{
  const old=state.memory.read(512,2), value=(old[0]|old[1]<<8)+1;
  state.memory.write(512,new Uint8Array([value&255,value>>8]));
  frames.push(JSON.stringify({{...finishCase(state,{{stopReason:'frame_complete'}}),sample:{{tick,operation:'frame'}}}}));
}}
await writeFile(process.argv[3],frames.join('\\n'));
''')
        (work/'reference.py').write_text(f'''
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,{str(Path(__file__).parent.resolve())!r})
from unicorn_runner import UnicornCaptureRunner
source=json.loads(Path(sys.argv[1]).read_text())
runner=UnicornCaptureRunner.from_capture(Path(source['capture_directory']).parent,source['capture'])
frames=[]
for tick in range(1,4):
    runner.engine.emu_start(0x100,0x104,count=10)
    data=bytes(runner.engine.mem_read(512,2))
    frames.append(json.dumps({{'initial_state_sha256':source['initial_state_sha256'],'stop_reason':'frame_complete',
      'sample':{{'tick':tick,'operation':'frame'}},'memory_ranges':{{'counter':{{'address':512,'length':2,'sha256':hashlib.sha256(data).hexdigest()}}}}}}))
Path(sys.argv[2]).write_text('\\n'.join(frames))
''')
        plan={'required_stages':['scene'],'timing_model':'three explicit fixture updates',
              'cases':[{'name':'dependent updates','stage':'scene','capture':0,'contract':'contract.json',
                        'sequence':True,'expected_samples':3,'final_tick':3,
                        'reference_command':[sys.executable,'-B','reference.py','{input}','{output}'],
                        'javascript_command':['node','scene.mjs','{input}','{output}']}]}
        path=work/'plan.json';path.write_text(json.dumps(plan))
        summary=run_suite(self.session,path,work/'stream-results')
        self.assertEqual(summary['verdict'],'PASS',summary)
        self.assertEqual(summary['cases'][0]['compared_samples'],3)
