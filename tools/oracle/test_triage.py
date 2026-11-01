import struct
import tempfile
import unittest
from pathlib import Path
from binary_triage import inspect_file


class TriageTests(unittest.TestCase):
    def test_format_and_signature_candidates_do_not_modify_originals(self):
        data=bytearray(256)
        struct.pack_into('<14H',data,0,0x5a4d,0,0,2,4,0,0,0,0,0,0x59,0,0,0)
        data[64:67]=b'RNC'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'arbitrary.exe';path.write_bytes(data)
            report=inspect_file(path)
            self.assertEqual(report['format'],'MZ')
            self.assertEqual(report['load_relative_entry'],{'cs':0,'ip':0x59})
            self.assertFalse(report['candidates'][0]['verified'])
            self.assertEqual(path.read_bytes(),data)
