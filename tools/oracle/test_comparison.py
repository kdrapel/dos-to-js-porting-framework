import copy
import hashlib
import unittest

from differential_compare import compare_states


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.contract = {'schema_version':1, 'evidence_class':'routine', 'registers':['eax'],
                         'flags_mask':'0x8d5', 'whole_memory':True, 'ordered_writes':True,
                         'stop_reasons':{'reference':['reached_stop_address'],'javascript':['completed']}}
        self.reference = {'initial_state_sha256':digest('same initial state'), 'stop_reason':'reached_stop_address',
                          'final_registers':{'eax':3,'eflags':'0x202'}, 'final_memory_sha256':digest('final'),
                          'writes_count':2, 'write_trace_sha256':digest('a then b'), 'write_trace_complete':True}
        self.js = dict(self.reference, stop_reason='completed')

    def test_empty_reports_and_missing_contract_never_pass(self):
        self.assertEqual(compare_states({}, {})['verdict'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(compare_states({}, {}, self.contract)['verdict'], 'INSUFFICIENT_EVIDENCE')

    def test_same_input_and_complete_evidence_pass(self):
        report=compare_states(self.reference,self.js,self.contract)
        self.assertEqual(report['verdict'],'PASS')
        self.assertIn('writes.order',report['checks_performed'])

    def test_missing_register_or_flags_never_silently_skipped(self):
        for name in ('eax','eflags'):
            js=copy.deepcopy(self.js); del js['final_registers'][name]
            self.assertEqual(compare_states(self.reference,js,self.contract)['verdict'],'INSUFFICIENT_EVIDENCE')

    def test_same_write_count_with_different_order_fails(self):
        self.js['write_trace_sha256']=digest('b then a')
        report=compare_states(self.reference,self.js,self.contract)
        self.assertEqual(report['verdict'],'FAIL')
        self.assertEqual(report['differences'][0]['name'],'writes.order')

    def test_truncated_trace_or_unsuccessful_execution_is_not_evidence(self):
        self.js['write_trace_complete']=False
        self.assertEqual(compare_states(self.reference,self.js,self.contract)['verdict'],'INSUFFICIENT_EVIDENCE')
        self.js['write_trace_complete']=True
        self.reference['stop_reason']='instruction_limit_reached'
        self.assertEqual(compare_states(self.reference,self.js,self.contract)['verdict'],'INSUFFICIENT_EVIDENCE')

    def test_different_initial_state_is_not_a_comparison_pass(self):
        self.js['initial_state_sha256']=digest('other input')
        self.assertEqual(compare_states(self.reference,self.js,self.contract)['verdict'],'INSUFFICIENT_EVIDENCE')

    def test_named_output_ranges_are_required_at_declared_addresses(self):
        contract={'schema_version':1,'memory_ranges':[{'name':'output','address':'0x200','length':2}],
                  'stop_reasons':self.contract['stop_reasons']}
        region={'address':512,'length':2,'sha256':digest('output')}
        self.reference['memory_ranges']={'output':region}
        self.js['memory_ranges']={'output':dict(region,address=514)}
        self.assertEqual(compare_states(self.reference,self.js,contract)['verdict'],'INSUFFICIENT_EVIDENCE')
        self.js['memory_ranges']['output']['address']=512
        self.assertEqual(compare_states(self.reference,self.js,contract)['verdict'],'PASS')

    def test_unknown_contract_fields_and_no_observables_are_rejected(self):
        self.contract['whole_memroy']=True
        self.assertEqual(compare_states(self.reference,self.js,self.contract)['verdict'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(compare_states(self.reference,self.js,{'schema_version':1})['verdict'],'INSUFFICIENT_EVIDENCE')

    def test_contract_cannot_bless_a_failed_replay(self):
        self.reference['stop_reason']='unicorn_exception'
        self.contract['stop_reasons']['reference']=['unicorn_exception']
        self.assertEqual(compare_states(self.reference,self.js,self.contract)['verdict'],'INSUFFICIENT_EVIDENCE')

    def test_small_output_mismatch_identifies_first_byte(self):
        contract={'schema_version':1,'memory_ranges':[{'name':'buffer','address':100,'length':3}],
                  'stop_reasons':self.contract['stop_reasons']}
        for report,data in [(self.reference,b'abc'),(self.js,b'axc')]:
            report['memory_ranges']={'buffer':{'address':100,'length':3,'sha256':hashlib.sha256(data).hexdigest(),'bytes_hex':data.hex()}}
        result=compare_states(self.reference,self.js,contract)
        self.assertEqual(result['verdict'],'FAIL')
        self.assertEqual(result['differences'][0]['first_address'],101)

    def test_malformed_ranges_geometry_and_negative_counts_are_insufficient(self):
        contract={'schema_version':1,'memory_ranges':[{'name':'output','address':0,'length':1}],
                  'stop_reasons':self.contract['stop_reasons']}
        self.js['memory_ranges']=[]
        self.assertEqual(compare_states(self.reference,self.js,contract)['verdict'],'INSUFFICIENT_EVIDENCE')
        contract.update(memory_ranges=[],framebuffer=True)
        self.reference['framebuffer']={'width':'not-a-number','height':0,'sha256':digest('')}
        self.js['framebuffer']=self.reference['framebuffer']
        self.assertEqual(compare_states(self.reference,self.js,contract)['verdict'],'INSUFFICIENT_EVIDENCE')
        self.reference['writes_count']=self.js['writes_count']=-1
        self.assertEqual(compare_states(self.reference,self.js,self.contract)['verdict'],'INSUFFICIENT_EVIDENCE')
