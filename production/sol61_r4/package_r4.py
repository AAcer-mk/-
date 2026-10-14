#!/usr/bin/env python3
"""Deterministic R4 payload: originals, selected delivery movies, QA evidence."""
import hashlib,io,json,tarfile
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    q=ROOT/'render-v3';qa=json.loads((q/'R4_QA.json').read_text())
    movies=['E7_CARD_WORKPRINT_r4_MASTER.mkv','E7_APPROVAL_INSERTS_WORKPRINT_r4_MASTER.mkv',
        'E7_PRINTER_LCD_WORKPRINT_r4_MASTER.mkv','F6_SEQUENCE_PATCH_WORKPRINT_r4_MASTER.mkv',
        'E7_NONCONTIGUOUS_INSERT_REEL_r4_1080P.mp4','F6_SEQUENCE_PATCH_WORKPRINT_r4_1080P_BILINGUAL.mp4']
    files=list((ROOT/'assets').glob('*.png'))+[q/x for x in movies]+list((q/'native_refs').glob('*.jpg'))
    files += [q/'R4_QA.json',q/'R4_ACTUAL_ENCODED_CONTACT.jpg',q/'E7_NATIVE_CANDIDATES.jpg',q/'E7-02_HAN_REFERENCE_CONTACT.jpg']
    files += list(q.glob('*_local_bilingual.ass'))+list(q.glob('*_decoded_*.jpg'))
    files += [q/'F6_before_frame599.jpg',q/'F6_after_compositor_frame599.jpg']
    files=sorted(set(files));assert len(files)==len(set(files))
    reports={x['path']:x for x in qa['outputs']}
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
    payload=b.getvalue();size=393216;parts=[];dest=ROOT/'payload/round-r4';dest.mkdir(parents=True,exist_ok=False)
    for i,offset in enumerate(range(0,len(payload),size),1):
        data=payload[offset:offset+size];path=f'payload/round-r4/part-{i:04d}.bin';(ROOT/path).write_bytes(data)
        assert (ROOT/path).read_bytes()==data
        parts.append({'path':path,'bytes':len(data),'sha256':digest(data),
            'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    manifest={'schema':'silent-protocol-r4-payload','format':'deterministic USTAR','bytes':len(payload),
        'sha256':digest(payload),'split_size_bytes':size,'parts':parts,'members':members}
    (ROOT/'PAYLOAD_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    paths=['README.md','PRODUCTION_STATE.json','generation_records.json','build_r4.py','package_r4.py',
           'restore_r4.py','verify_remote.py','PAYLOAD_MANIFEST.json']+[p['path'] for p in parts]
    uploads=[]
    for name in paths:
        data=(ROOT/name).read_bytes();uploads.append({'path':'production/sol61_r4/'+name,'bytes':len(data),
            'encoding':'base64' if name.endswith('.bin') else 'utf-8',
            'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    (ROOT/'UPLOAD_LIST.json').write_text(json.dumps(uploads,indent=2))
    print('R4 package:',len(payload),'bytes,',len(parts),'parts,',len(members),'members; all source hashes/image loads PASS.')
if __name__=='__main__':main()
