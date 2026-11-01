import argparse
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from asm_index import build, parse, query


class IndexTests(unittest.TestCase):
    def test_operand_size_is_not_symbol(self):
        self.assertEqual(parse('0000ABCF                 sldt word ptr [eax]'), (0xABCF, None, 'sldt', 'word ptr [eax]'))

    def test_quoted_semicolon_and_initial_symbol(self):
        self.assertEqual(parse("aName_0 db 'a;b',0 ; comment"), (0, 'aName_0', 'db', "'a;b',0"))

    def test_ida_listing_without_instruction_addresses(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'ida.asm'
            database = Path(folder) / 'ida.sqlite'
            source.write_text("""sub_100 proc near
push ebp
call sub_200
retn
sub_100 endp
sub_200 proc near
retn
sub_200 endp
""", encoding='utf-8')
            build(source, database)
            with closing(sqlite3.connect(database)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM instructions').fetchone()[0], 4)
                self.assertEqual(db.execute('SELECT count(*) FROM instructions WHERE address IS NULL').fetchone()[0], 4)
                self.assertEqual(db.execute('SELECT source_address,source_line,target_address,kind FROM refs').fetchall(), [(None, 3, 0x200, 'call')])
                self.assertEqual(db.execute("SELECT instruction_count,outgoing_calls FROM function_summary WHERE name='sub_100'").fetchone(), (3, 1))
                self.assertEqual(dict(db.execute('SELECT * FROM metadata'))['schema_version'], '2')
            args = argparse.Namespace(db=database, limit=10, offset=0, command='callers', expression='sub_200')
            self.assertEqual(query(args)['rows'][0]['source_line'], 3)
            self.assertIsNone(query(args)['rows'][0]['source_address'])
            args.command, args.expression = 'callees', 'sub_100'
            self.assertEqual(query(args)['rows'][0]['target_symbol'], 'sub_200')

    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'sample.asm'
            database = Path(folder) / 'sample.sqlite'
            source.write_text("""dword_0 dd 0
00000100 sub_100 proc near
00000100 mov eax, dword_0 ; call sub_200 is just a comment
00000105 call sub_200
0000010A call dword ptr [dword_0]
00000110 jnz short loc_118
00000112 mov eax, offset dword_0+4
00000118 loc_118: retn
00000118 sub_100 endp
00000120 mov eax, 1
00000200 sub_200 proc near
00000200 retn
00000200 sub_200 endp
""", encoding='utf-8')
            build(source, database)
            with closing(sqlite3.connect(database)) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
                self.assertEqual(db.execute('SELECT count(*) FROM functions').fetchone()[0], 2)
                self.assertEqual(db.execute('SELECT count(*) FROM instructions WHERE function_id IS NULL').fetchone()[0], 1)
                self.assertEqual(db.execute('SELECT source_address,target_address FROM calls').fetchall(), [(0x105, 0x200)])
                self.assertEqual(db.execute('SELECT is_indirect FROM instructions WHERE address=266').fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT kind FROM refs WHERE source_address=272").fetchone()[0], 'jump')
                self.assertEqual(db.execute("SELECT target_address,kind FROM refs WHERE source_address=274").fetchone(), (0, 'address'))
                self.assertEqual(db.execute('SELECT count(*) FROM source_fts WHERE source_fts MATCH ?', ('"dword_0"',)).fetchone()[0], 4)
            args = argparse.Namespace(db=database, limit=2, offset=0, command='function', expression='sub_100')
            result = query(args)
            self.assertTrue(result['truncated'])
            self.assertEqual(len(result['rows']), 2)
            args.command, args.expression = 'sql', "DELETE FROM annotations"
            with self.assertRaises(sqlite3.OperationalError):
                query(args)
            with self.assertRaises(SystemExit):
                build(source, database)


if __name__ == '__main__':
    unittest.main()
