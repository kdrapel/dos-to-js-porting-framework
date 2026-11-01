"""Bounded read-only comparison of indexed routines; similarity is not equivalence."""
import argparse
import difflib
import json
from pathlib import Path
import re
import sqlite3
from contextlib import closing


def instructions(database, name, limit):
    with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        rows=db.execute('SELECT i.address,i.line_number,i.mnemonic,i.operands FROM instructions i '
                        'JOIN functions f ON f.id=i.function_id WHERE f.name=? ORDER BY i.line_number LIMIT ?',
                        (name,limit+1)).fetchall()
    if not rows: raise ValueError(f'no indexed instructions for {name}')
    if len(rows)>limit: raise ValueError('routine exceeds bounded comparison limit')
    return [f'{mnemonic} {operands}'.strip() for _,_,mnemonic,operands in rows]


def compare_routines(left_db,left,right_db,right,limit=10000):
    a,b=instructions(left_db,left,limit),instructions(right_db,right,limit)
    def normalize(line):
        line=re.sub(r'\b(?:sub|loc|off|byte|word|dword|qword)_[0-9A-Fa-f]+\b','<address>',line)
        return re.sub(r'\b(?:0x[0-9a-fA-F]+|[0-9][0-9a-fA-F]*h|\d+)\b','<constant>',line)
    return {'left':left,'right':right,'instruction_counts':[len(a),len(b)],
            'normalized_similarity':difflib.SequenceMatcher(a=list(map(normalize,a)),b=list(map(normalize,b)),autojunk=False).ratio(),
            'raw_diff':list(difflib.unified_diff(a,b,fromfile=left,tofile=right,lineterm=''))[:120],
            'limits':'Candidate shared code only. Constants, rounding, aliases and reachable variants must be verified against bytes and real-input tests before sharing an engine.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',required=True)
    p.add_argument('--other-db');p.add_argument('--left',required=True);p.add_argument('--right',required=True)
    p.add_argument('--limit',type=int,default=10000);a=p.parse_args()
    print(json.dumps(compare_routines(a.db,a.left,a.other_db or a.db,a.right,a.limit),indent=2))
