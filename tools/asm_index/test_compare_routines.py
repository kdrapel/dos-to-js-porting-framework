import sqlite3
import tempfile
import unittest
from pathlib import Path
from compare_routines import compare_routines
from contextlib import closing


class RoutineComparisonTests(unittest.TestCase):
    def test_constant_normalization_does_not_hide_raw_differences(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'index.sqlite'
            with closing(sqlite3.connect(path)) as db:
                db.executescript('CREATE TABLE functions(id INTEGER,name TEXT); CREATE TABLE instructions(address INTEGER,line_number INTEGER,function_id INTEGER,mnemonic TEXT,operands TEXT);')
                db.executemany('INSERT INTO functions VALUES(?,?)',[(1,'left'),(2,'right')])
                db.executemany('INSERT INTO instructions VALUES(?,?,?,?,?)',[(None,1,1,'shld','eax, edx, 8'),(None,2,2,'shld','eax, edx, 10')])
                db.commit()
            report=compare_routines(path,'left',path,'right')
            self.assertEqual(report['normalized_similarity'],1)
            self.assertTrue(any('10' in line for line in report['raw_diff']))
            self.assertIn('not equivalence',__import__('compare_routines').__doc__)
