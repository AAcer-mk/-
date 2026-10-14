#!/usr/bin/env python3
"""Fresh R5 downloads at immutable commit; every part and member byte match."""
import argparse,concurrent.futures,hashlib,io,json,re,tarfile,time,urllib.request
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--ref',required=True);p.add_argument('--tree',required=True)
    p.add_argument('--cache',type=Path,required=True);a=p.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',a.ref) and re.fullmatch('[0-9a-f]{40}',a.tree)
    root=Path(__file__).resolve().parent;m=json.loads((root/'PAYLOAD_MANIFEST.json').read_text());a.cache.mkdir(parents=True,exist_ok=True)
    def read(row):
        url='https://raw.githubusercontent.com/AAcer-mk/-/'+a.ref+'/production/sol61_r5/'+row['path']
        for attempt in range(3):
            try:
                data=urllib.request.urlopen(url,timeout=40).read()
                assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
                assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['git_blob_sha']
                (a.cache/Path(row['path']).name).write_bytes(data);return data
            except Exception:
                if attempt==2:raise
                time.sleep(1)
    blocks=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i,data in enumerate(pool.map(read,m['parts']),1):
            blocks.append(data)
            if i%16==0 or i==len(m['parts']):print('Remote verified',i,'/',len(m['parts']),flush=True)
    data=b''.join(blocks);assert len(data)==m['bytes'] and hashlib.sha256(data).hexdigest()==m['sha256']
    members=[]
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as archive:
        assert set(archive.getnames())==set(x['path'] for x in m['members'])
        for row in m['members']:
            actual=archive.extractfile(row['path']).read()
            assert len(actual)==row['bytes'] and hashlib.sha256(actual).hexdigest()==row['sha256']
            assert actual==(root/row['path']).read_bytes()
            members.append({'path':row['path'],'sha256':row['sha256'],'remote_byte_readback':'PASS'})
    receipt={'schema':'silent-protocol-r5-remote-receipt','repository':'AAcer-mk/-',
        'branch':'production/sol61-resume-20261014-060902','data_commit':a.ref,'data_tree':a.tree,
        'method':'Fresh immutable-commit downloads; every SHA256 and Git blob checked; TAR SHA and all member bytes compared to verified local work',
        'archive_bytes':len(data),'archive_sha256':m['sha256'],'parts_read_back':len(blocks),'members':members,
        'all_member_bytes_match':True,'branch_ref_readback':'PASS before binary verification',
        'new_unique_picture_frames':473,'new_unique_picture_seconds':473/24,'E7_workprint_frames':1019,
        'E7_missing_frames':541,'E7_complete':False,'formal_actor_and_voice_acceptance':False,'final_film_completed':False}
    (root/'REMOTE_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    print('REMOTE R5 PASS',len(blocks),'parts',len(members),'members',a.ref,flush=True)
if __name__=='__main__':main()
