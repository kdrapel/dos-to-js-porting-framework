"""Memory file integrity does not establish readable capture coverage."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from inventory import inventory_session


class MemoryInventoryTests(unittest.TestCase):
    def test_expected_size_partial_dump_still_warns_and_records_range(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / 'oracle/extract/session'
            capture = session / 'capture_000000'
            capture.mkdir(parents=True)
            (capture / 'memory.bin').write_bytes(bytes(16))
            (capture / 'capture.json').write_text(json.dumps({
                'capture': 0, 'assets': {'data': {
                    'file': 'memory.bin', 'size': 16, 'expected_size': 16,
                    'segment': '0858', 'offset': '00100000',
                    'status': 'partial', 'error': '16 unreadable bytes were zero-filled'
                }, 'skipped': {'status': 'skipped', 'reason': 'cadence'}}
            }))
            (session / 'session.json').write_text(json.dumps({
                'status': 'stopped', 'captures': 1, 'stop_reason': 'manual'
            }))
            with contextlib.redirect_stdout(io.StringIO()):
                report = inventory_session(root, session)
            self.assertEqual(report['errors'], [])
            self.assertEqual(len(report['warnings']), 1)
            self.assertIn('unreadable', report['warnings'][0])
            region = report['captures'][0]['memory_regions'][0]
            self.assertEqual(region['offset'], '00100000')
            self.assertEqual(region['requested_bytes'], 16)
            self.assertEqual(region['status'], 'partial')


if __name__ == '__main__':
    unittest.main()
