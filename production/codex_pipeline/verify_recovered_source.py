#!/usr/bin/env python3
"""Check every expected recovered member; a sentinel file is insufficient."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--scope',choices=['all','baseline','rounds','old'],default='all');p.add_argument('--output',type=Path)
    args=p.parse_args();members=[]
    if args.scope in ['all','baseline']:
        data=json.loads((HERE/'qa/recovery/baseline_recovery.json').read_text())
        members.extend((args.source/r['path'],r) for r in data['files'])
    if args.scope in ['all','rounds']:
        for n in range(2,7):
            root=REPO/f'production/sol61_r{n}';data=json.loads((root/'PAYLOAD_MANIFEST.json').read_text())
            members.extend((root/r['path'],r) for r in data['members'])
    if args.scope in ['all','old']:
        root=REPO/'production/sol61'
        for name in ['artwork_manifest.json','renders_manifest.json']:
            data=json.loads((root/'state'/name).read_text());members.extend((root/r['path'],r) for r in data['files'])
    bad=[]
    for path,row in members:
        if not path.is_file() or path.stat().st_size!=row['bytes']:
            bad.append({'path':str(path),'reason':'MISSING_OR_SIZE_MISMATCH'});continue
        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=row['sha256']:bad.append({'path':str(path),'reason':'SHA256_MISMATCH_PRESERVE_EXISTING_DATA'})
    report={'scope':args.scope,'checked_members':len(members),'all_size_and_SHA256_match':not bad,
            'failures':bad,'archive_downloads':0,'archive_extractions':0}
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 1 if bad else 0


if __name__=='__main__':raise SystemExit(main())
