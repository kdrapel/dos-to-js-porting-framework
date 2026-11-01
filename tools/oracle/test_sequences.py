import json
from pathlib import Path
import tempfile
import unittest
from sequence_compare import compare_sequences
from test_comparison import digest


class SequenceTests(unittest.TestCase):
    def test_full_sequence_and_first_divergent_operation(self):
        contract={'schema_version':1,'registers':['eax'],'stop_reasons':{'reference':['frame_complete'],'javascript':['frame_complete']}}
        samples=[{'sample':{'tick':tick,'operation':'draw'},'initial_state_sha256':digest('shared run'),
                  'stop_reason':'frame_complete','final_registers':{'eax':tick}} for tick in (0,1,2)]
        with tempfile.TemporaryDirectory() as directory:
            a,b=Path(directory)/'a.jsonl',Path(directory)/'b.jsonl'
            def save(path,values):path.write_text('\n'.join(json.dumps(v) for v in values))
            save(a,samples);save(b,samples)
            self.assertEqual(compare_sequences(a,b,contract)['compared_samples'],3)
            self.assertEqual(compare_sequences(a,b,contract,expected_samples=3,final_tick=2)['verdict'],'PASS')
            self.assertEqual(compare_sequences(a,b,contract,expected_samples=4)['verdict'],'INSUFFICIENT_EVIDENCE')
            self.assertEqual(compare_sequences(a,b,contract,final_tick=3)['verdict'],'INSUFFICIENT_EVIDENCE')
            samples[1]['final_registers']['eax']=99;save(b,samples)
            result=compare_sequences(a,b,contract)
            self.assertEqual(result['verdict'],'FAIL');self.assertEqual(result['sample']['tick'],1)
            self.assertEqual(result['compared_samples'],1)
            save(b,samples[:1]);self.assertEqual(compare_sequences(a,b,contract)['verdict'],'INSUFFICIENT_EVIDENCE')

    def test_empty_and_unaligned_streams_are_not_passing(self):
        with tempfile.TemporaryDirectory() as directory:
            a,b=Path(directory)/'a',Path(directory)/'b';a.write_text('');b.write_text('')
            self.assertEqual(compare_sequences(a,b,{})['verdict'],'INSUFFICIENT_EVIDENCE')
            a.write_text('{"sample":{"tick":1}}');b.write_text('{"sample":{"tick":2}}')
            self.assertEqual(compare_sequences(a,b,{})['verdict'],'INSUFFICIENT_EVIDENCE')
