#!/usr/bin/env python3
"""Deterministic R5 USTAR payload with source originals and selected delivery."""
import hashlib,io,json,tarfile
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    q=ROOT/'render-v2';qa=json.loads((q/'R5_QA.json').read_text())
    movies=[f'E7-{s}_WORKPRINT_r5_{ending}' for s in ['01','08','09'] for ending in ['MASTER.mkv','1080P_BILINGUAL.mp4']]
    movies+=['E7_SEVEN_SHOT_NONCONTIGUOUS_REEL_r5_1080P_BILINGUAL.mp4']
    files=list((ROOT/'assets').glob('*.png'))+[q/x for x in movies]
    files+=list(q.glob('*.jpg'))+list(q.glob('*MASK.png'))+list(q.glob('*_local_bilingual.ass'))
    files += [q/'R5_QA.json',q/'E7_SEVEN_SHOT_REEL_bilingual.ass']
    files=sorted(set(files));reports={x['path']:x for x in qa['outputs']}
    records={x['output']:x for x in json.loads((ROOT/'generation_records.json').read_text())}
    members=[];b=io.BytesIO()
    with tarfile.open(fileobj=b,mode='w',format=tarfile.USTAR_FORMAT) as archive:
        for f in files:
            data=f.read_bytes();path=f.relative_to(ROOT).as_posix();h=digest(data)
            if f.name in reports:assert h==reports[f.name]['sha256'],f
            if path in records:assert h==records[path]['sha256'],f
            if f.suffix.lower() in ['.png','.jpg']:
                with Image.open(io.BytesIO(data)) as im:im.load()
            info=tarfile.TarInfo(path);info.size=len(data);info.mode=0o644;info.mtime=0
            archive.addfile(info,io.BytesIO(data));members.append({'path':path,'bytes':len(data),'sha256':h})
    payload=b.getvalue();size=393216;parts=[];dest=ROOT/'payload/round-r5';dest.mkdir(parents=True,exist_ok=False)
    for i,offset in enumerate(range(0,len(payload),size),1):
        data=payload[offset:offset+size];path=f'payload/round-r5/part-{i:04d}.bin';(ROOT/path).write_bytes(data)
        assert (ROOT/path).read_bytes()==data
        parts.append({'path':path,'bytes':len(data),'sha256':digest(data),
            'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    manifest={'schema':'silent-protocol-r5-payload','format':'deterministic USTAR','bytes':len(payload),
        'sha256':digest(payload),'split_size_bytes':size,'parts':parts,'members':members}
    (ROOT/'PAYLOAD_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    paths=['README.md','PRODUCTION_STATE.json','generation_records.json','build_r5.py','package_r5.py',
        'restore_r5.py','verify_remote.py','PAYLOAD_MANIFEST.json']+[p['path'] for p in parts]
    uploads=[]
    for name in paths:
        data=(ROOT/name).read_bytes();uploads.append({'path':'production/sol61_r5/'+name,'bytes':len(data),
            'encoding':'base64' if name.endswith('.bin') else 'utf-8',
            'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    (ROOT/'UPLOAD_LIST.json').write_text(json.dumps(uploads,indent=2))
    print('R5 package:',len(payload),'bytes,',len(parts),'parts,',len(members),'members; image loads and source/video hashes PASS.')
if __name__=='__main__':main()
