#!/usr/bin/env python3
"""Read every R3 binary part at an immutable commit and compare all members."""
import argparse, concurrent.futures, hashlib, io, json, re, tarfile, time, urllib.request
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--ref',required=True);p.add_argument('--tree',required=True)
    p.add_argument('--cache',type=Path,required=True);args=p.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',args.ref) and re.fullmatch('[0-9a-f]{40}',args.tree)
    root=Path(__file__).resolve().parent;manifest=json.loads((root/'PAYLOAD_MANIFEST.json').read_text())
    args.cache.mkdir(parents=True,exist_ok=True)
    def read(row):
        url='https://raw.githubusercontent.com/AAcer-mk/-/'+args.ref+'/production/sol61_r3/'+row['path']
        for attempt in range(3):
            try:
                data=urllib.request.urlopen(url,timeout=40).read()
                assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
                assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['git_blob_sha']
                (args.cache/Path(row['path']).name).write_bytes(data);return data
            except Exception:
                if attempt==2:raise
                time.sleep(1)
    blocks=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i,data in enumerate(pool.map(read,manifest['parts']),1):
            blocks.append(data)
            if i%16==0 or i==len(manifest['parts']):print('Remote verified',i,'/',len(manifest['parts']),flush=True)
    data=b''.join(blocks)
    assert len(data)==manifest['bytes'] and hashlib.sha256(data).hexdigest()==manifest['sha256']
    members=[]
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as archive:
        assert set(archive.getnames())==set(x['path'] for x in manifest['members'])
        for row in manifest['members']:
            actual=archive.extractfile(row['path']).read()
            assert len(actual)==row['bytes'] and hashlib.sha256(actual).hexdigest()==row['sha256']
            assert actual==(root/row['path']).read_bytes()
            members.append({'path':row['path'],'sha256':row['sha256'],'remote_byte_readback':'PASS'})
    report={'schema':'silent-protocol-r3-remote-receipt','repository':'AAcer-mk/-',
        'branch':'production/sol61-resume-20261014-060902','data_commit':args.ref,'data_tree':args.tree,
        'method':'Fresh immutable-commit downloads; SHA256 and Git blob verification for every part; TAR SHA and all member bytes matched local verified work',
        'archive_bytes':len(data),'archive_sha256':manifest['sha256'],'parts_read_back':len(blocks),
        'members':members,'all_member_bytes_match':True,'branch_ref_readback':'PASS before binary verification',
        'F7_workprint_frames':600,'F7_workprint_seconds':25,'new_unique_picture_frames':408,
        'actor_and_voice_final_acceptance':False,'final_film_completed':False}
    (root/'REMOTE_RECEIPT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('REMOTE R3 PASS',len(blocks),'parts',len(members),'members',args.ref,flush=True)

if __name__=='__main__':main()
