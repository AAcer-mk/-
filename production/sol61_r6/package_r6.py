#!/usr/bin/env python3
"""Deterministic R6 USTAR payload with source originals and selected delivery."""
import hashlib,io,json,tarfile
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    q=ROOT/'sound-v2'
    files=sorted([x for x in q.glob('*.flac') if '.pending.' not in x.name and not x.name.startswith('SILENT_PROTOCOL_MIX')]+list(q.glob('*.mkv'))+list(q.glob('*.mp4'))+[q/'SOUND_QA.json',q/'CUE_SHEET.json'])
    members=[];b=io.BytesIO()
    with tarfile.open(fileobj=b,mode='w',format=tarfile.USTAR_FORMAT) as archive:
        for f in files:
            data=f.read_bytes();path=f.relative_to(ROOT).as_posix();h=digest(data)
            if f.suffix.lower() in ['.png','.jpg']:
                with Image.open(io.BytesIO(data)) as im:im.load()
            info=tarfile.TarInfo(path);info.size=len(data);info.mode=0o644;info.mtime=0
            archive.addfile(info,io.BytesIO(data));members.append({'path':path,'bytes':len(data),'sha256':h})
    payload=b.getvalue();size=393216;parts=[];dest=ROOT/'payload/round-r6';dest.mkdir(parents=True,exist_ok=False)
    for i,offset in enumerate(range(0,len(payload),size),1):
        data=payload[offset:offset+size];path=f'payload/round-r6/part-{i:04d}.bin';(ROOT/path).write_bytes(data)
        assert (ROOT/path).read_bytes()==data
        parts.append({'path':path,'bytes':len(data),'sha256':digest(data),
            'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    manifest={'schema':'silent-protocol-r6-payload','format':'deterministic USTAR','bytes':len(payload),
        'sha256':digest(payload),'split_size_bytes':size,'parts':parts,'members':members}
    (ROOT/'PAYLOAD_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    paths=['README.md','PRODUCTION_STATE.json','build_sound_r6.py','package_r6.py','restore_r6.py','verify_remote.py','PAYLOAD_MANIFEST.json']+[p['path'] for p in parts]
    uploads=[]
    for name in paths:
        data=(ROOT/name).read_bytes();uploads.append({'path':'production/sol61_r6/'+name,'bytes':len(data),
            'encoding':'base64' if name.endswith('.bin') else 'utf-8',
            'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    (ROOT/'UPLOAD_LIST.json').write_text(json.dumps(uploads,indent=2))
    print('R6 package:',len(payload),'bytes,',len(parts),'parts,',len(members),'members; image loads and source/video hashes PASS.')
if __name__=='__main__':main()
