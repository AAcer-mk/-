#!/usr/bin/env python3
"""Restore R3's pinned, SHA-verified binary payload without full film recovery."""
import argparse, concurrent.futures, hashlib, io, json, tarfile, urllib.request
from pathlib import Path, PurePosixPath

def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--ref',default='production/sol61-resume-20261014-060902')
    args=p.parse_args();root=Path(__file__).resolve().parent
    manifest=json.loads((root/'PAYLOAD_MANIFEST.json').read_text())
    args.cache.mkdir(parents=True,exist_ok=True)
    def part(row):
        path=root/row['path'];cache=args.cache/row['sha256']
        if path.is_file():data=path.read_bytes()
        elif cache.is_file():data=cache.read_bytes()
        else:
            url='https://raw.githubusercontent.com/AAcer-mk/-/'+args.ref+'/production/sol61_r3/'+row['path']
            data=urllib.request.urlopen(url,timeout=45).read()
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],row['path']
        if not cache.exists():cache.write_bytes(data)
        return data
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        data=b''.join(pool.map(part,manifest['parts']))
    assert len(data)==manifest['bytes'] and hashlib.sha256(data).hexdigest()==manifest['sha256']
    wanted={r['path']:r for r in manifest['members']}
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as archive:
        assert set(archive.getnames())==set(wanted)
        for member in archive:
            assert member.isfile() and '..' not in PurePosixPath(member.name).parts
            dst=root/member.name;assert dst.resolve().is_relative_to(root.resolve())
            payload=archive.extractfile(member).read();row=wanted[member.name]
            assert len(payload)==row['bytes'] and hashlib.sha256(payload).hexdigest()==row['sha256']
            if dst.exists():assert dst.read_bytes()==payload,'Existing data differs: '+str(dst)
            else:dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(payload)
    print('Restored',len(wanted),'verified files; all payload parts and members matched SHA-256.')

if __name__=='__main__':main()
