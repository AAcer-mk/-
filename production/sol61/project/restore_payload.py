"""Reassemble and verify committed payload parts into production/sol61.

Usage: python production/sol61/project/restore_payload.py artwork_manifest.json
       python production/sol61/project/restore_payload.py renders_manifest.json
"""
from pathlib import Path,PurePosixPath
import hashlib,json,sys,tarfile,tempfile
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]

def restore(name):
    manifest=json.loads((ROOT/'state'/name).read_text())
    with tempfile.TemporaryFile() as archive:
        digest=hashlib.sha256();total=0
        for part in manifest['parts']:
            data=(REPO/part['path']).read_bytes();assert len(data)==part['bytes']
            assert hashlib.sha256(data).hexdigest()==part['sha256'],part['path']
            archive.write(data);digest.update(data);total+=len(data)
        assert total==manifest['archive_bytes'] and digest.hexdigest()==manifest['archive_sha256']
        archive.seek(0)
        with tarfile.open(fileobj=archive,mode='r:') as t:
            expected={e['path']:e for e in manifest['files']}
            assert {m.name for m in t.getmembers()}==set(expected)
            for m in t.getmembers():
                rel=PurePosixPath(m.name);assert not rel.is_absolute() and '..' not in rel.parts and m.isfile()
                data=t.extractfile(m).read();e=expected[m.name]
                assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256']
                path=ROOT/m.name
                if path.exists():assert path.read_bytes()==data,'Use a new revision; existing file differs.'
                else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print('Verified and restored',len(manifest['files']),'files')

if __name__=='__main__':
    for arg in sys.argv[1:]:restore(arg)
