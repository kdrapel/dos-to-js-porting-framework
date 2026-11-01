"""Timeline profile validation and memory-coverage warning regressions."""
import copy
import json
import unittest
from pathlib import Path

from validate_capture_profile import memory_coverage_warnings, validate_timeline, validate_paired_targeted


class CaptureProfileTests(unittest.TestCase):
    def setUp(self):
        template = Path(__file__).resolve().parents[2] / 'docs/templates/autocapture-config.template.json'
        self.profile = json.loads(template.read_text(encoding='utf-8'))

    def test_starter_is_valid_and_uses_eight_mib(self):
        self.assertEqual(validate_timeline(self.profile), [])
        self.assertEqual(memory_coverage_warnings(self.profile), [])
        self.assertEqual(int(self.profile['memory'][0]['length'], 16), 8 * 1024 * 1024)
        self.assertEqual(self.profile['memory'][0]['every_n_captures'], 1)

    def test_duplicate_one_mib_regions_warn_instead_of_summing(self):
        first = self.profile['memory'][0]
        first['length'] = '00100000'
        self.profile['memory'] = [copy.deepcopy(first) for _ in range(8)]
        self.assertEqual(validate_timeline(self.profile), [])
        self.assertTrue(memory_coverage_warnings(self.profile))

    def test_bad_lengths_and_overflow_are_rejected(self):
        for length in ('00000000', 'not-hex', '100000000', 1048576):
            with self.subTest(length=length):
                self.profile['memory'][0]['length'] = length
                self.assertTrue(validate_timeline(self.profile))
        self.profile['memory'][0].update(offset='FFFF0000', length='00020000')
        self.assertTrue(any('offset + length' in error for error in validate_timeline(self.profile)))

    def test_one_hour_address_stop_and_trace_are_rejected(self):
        self.profile['trigger'].update(interval_ms=3600000, initial_delay_ms=3600000)
        self.profile['events']['execution_addresses'] = [{'stop_after_capture': True}]
        self.profile['reference'].update(enabled=True, trace_instructions=True)
        self.assertGreaterEqual(len(validate_timeline(self.profile)), 5)

    def paired_profile(self):
        config = self.profile
        config['events']['execution_addresses'] = [
            {'selector': '0008', 'offset': '00002000', 'previous_offset': '00001000',
             'occurrence': 1, 'pair_source': True},
            {'selector': '0008', 'offset': '00001005', 'occurrence': 1,
             'pair_return': True, 'stop_after_capture': True}
        ]
        config['reference'].update(enabled=True, trace_instructions=True, start_at_first_address=True)
        return config

    def test_paired_entry_and_return_follow_verified_call_bytes(self):
        config = self.paired_profile()
        self.assertEqual(validate_paired_targeted(config, 'E8 FB 0F 00 00'), [])
        config['events']['execution_addresses'][0].update(offset='00001000', previous_offset='00000FFA')
        errors = validate_paired_targeted(config, 'E8 FB 0F 00 00')
        self.assertTrue(any('post-CALL routine entry' in error for error in errors))

    def test_paired_backward_call_and_wrong_continuation(self):
        config = self.paired_profile()
        config['events']['execution_addresses'][0].update(offset='00001000', previous_offset='00002000')
        config['events']['execution_addresses'][1]['offset'] = '00002005'
        self.assertEqual(validate_paired_targeted(config, 'E8 FB EF FF FF'), [])
        config['events']['execution_addresses'][1]['offset'] = '00002006'
        self.assertTrue(any('caller continuation' in error for error in
                            validate_paired_targeted(config, 'E8 FB EF FF FF')))

    def test_pair_requires_supported_call_evidence_and_safe_endpoints(self):
        config = self.paired_profile()
        self.assertTrue(validate_paired_targeted(config))
        self.assertTrue(validate_paired_targeted(config, 'FF D0'))
        config['events']['execution_addresses'][1]['stop_after_capture'] = False
        config['reference']['trace_instructions'] = False
        self.assertGreaterEqual(len(validate_paired_targeted(config, 'E8 FB 0F 00 00')), 2)


if __name__ == '__main__':
    unittest.main()
