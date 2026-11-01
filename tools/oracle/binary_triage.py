"""Inventory original binaries before deciding what to unpack or disassemble."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def inspect_file(path):
    path=Path(path)
    data=path.read_bytes()
    row={'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
         'format':'unidentified','candidates':[]}
    if data[:2]==b'MZ' and len(data)>=28:
        header=struct.unpack_from('<14H',data)
        row.update(format='MZ', header_bytes=header[4]*16,
                   load_relative_entry={'cs':header[11],'ip':header[10]},
                   relocation_count=header[3])
        if len(data)>=64:
            offset=int.from_bytes(data[60:64],'little')
            signature=data[offset:offset+4]
            if signature[:2] in (b'LE',b'LX',b'NE') or signature==b'PE\0\0':
                row['extended_header']={'offset':offset,'signature':signature.rstrip(b'\0').decode('ascii')}
    elif data[:4]==b'\x7fELF':
        row.update(format='ELF',elf_class=data[4] if len(data)>4 else None)
    for signature,label in ((b'RNC','possible RNC-packed block'),(b'SCRM','possible S3M header'),
                            (b'Extended Module:','possible XM header'),(b'IMPM','possible IT header')):
        positions=[]; start=0
        while len(positions)<32:
            at=data.find(signature,start)
            if at<0: break
            positions.append(at);start=at+len(signature)
        if positions: row['candidates'].append({'kind':label,'offsets':positions,'verified':False})
    row['limits']='Signatures are hypotheses, not format validation or proof of code reachability. Preserve originals; validate unpacking and loader relocation separately.'
    return row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('original',type=Path)
    args=parser.parse_args()
    paths=sorted(p for p in args.original.rglob('*') if p.is_file()) if args.original.is_dir() else [args.original]
    print(json.dumps([inspect_file(p) for p in paths],indent=2))
