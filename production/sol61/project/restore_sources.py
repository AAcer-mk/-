"""SHA-verified, selective restore from the three pinned GitHub migration branches.

Default: only inputs needed to reproduce this E6 production round. Optional
arguments are archive path prefixes. Never rebuilds the 1.13 GB TAR.
"""
from pathlib import Path
import concurrent.futures,hashlib,json,os,sys,time,urllib.request

ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
PINS=json.loads((ROOT/'state/source_pins.json').read_text())
CACHE=REPO/'.restore-cache';CACHE.mkdir(exist_ok=True)
DEST=REPO/'source-b10';DEST.mkdir(exist_ok=True)
URL='https://raw.githubusercontent.com/AAcer-mk/-/'

def verified_download(url,target,digest):
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==digest:return target.read_bytes()
    for attempt in range(4):
        try:
            data=urllib.request.urlopen(url,timeout=35).read()
            assert hashlib.sha256(data).hexdigest()==digest, str(target)
            target.parent.mkdir(parents=True,exist_ok=True)
            temporary=target.with_name(target.name+'.'+str(os.getpid())+'.tmp')
            temporary.write_bytes(data);temporary.replace(target);return data
        except Exception:
            if attempt==3:raise
            time.sleep(.5*(attempt+1))

def selected(m):
    p=m['path']
    if len(sys.argv)>1:return any(p.startswith(x) for x in sys.argv[1:])
    return (p.startswith(('project/','subtitles/','graphics/fonts/','art/candidates/E6'))
            or p in ['docs/ORIGINAL_CREATIVE_BRIEF.txt','state/checkpoint.json','output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'])

def restore():
    manifest=json.loads(verified_download(URL+PINS['manifest_ref']+'/transfer/manifest.json',CACHE/'manifest.json',PINS['manifest_sha256']))
    structure=json.loads(verified_download(URL+PINS['structure_ref']+'/transfer/rebuild-handoff/TAR_STRUCTURE.json',CACHE/'structure.json',PINS['structure_sha256']))
    assert manifest['archive_sha256']==structure['archive_sha256']==PINS['archive_sha256']
    split=manifest['split_size_bytes'];members=[m for m in structure['members'] if selected(m)]
    needed=set()
    for m in members:
        if m['size']:needed.update(range(m['data_offset']//split,(m['data_offset']+m['size']-1)//split+1))
    def part(i):
        entry=manifest['parts'][i];ref=next(r['ref'] for r in PINS['ranges'] if r['first']<=i+1<=r['last'])
        data=verified_download(URL+ref+'/'+entry['path'],CACHE/'parts'/f'{i+1:06d}',entry['sha256'])
        assert len(data)==entry['bytes'];return i
    print('Required members',len(members),'parts',len(needed),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for k,i in enumerate(pool.map(part,sorted(needed)),1):
            if k%25==0 or k==len(needed):print('Verified',k,'/',len(needed),flush=True)
    receipt=[]
    for m in members:
        cursor=m['data_offset'];remaining=m['size'];buffers=[]
        while remaining:
            i,offset=divmod(cursor,split);data=(CACHE/'parts'/f'{i+1:06d}').read_bytes();take=min(remaining,len(data)-offset)
            buffers.append(data[offset:offset+take]);remaining-=take;cursor+=take
        payload=b''.join(buffers);assert hashlib.sha256(payload).hexdigest()==m['payload_sha256']
        target=DEST/m['path'];assert target.resolve().is_relative_to(DEST.resolve())
        if target.exists():assert target.read_bytes()==payload,'Existing source differs: '+m['path']
        else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
        receipt.append({'path':m['path'],'bytes':m['size'],'sha256':m['payload_sha256']})
    (CACHE/'source_restore_receipt.json').write_text(json.dumps(receipt,indent=2))
    print('Restored',len(receipt),'original files without rebuilding TAR',flush=True)

if __name__=='__main__':restore()
