#!/usr/bin/env python3
"""Restore only this production unit's exact inputs from pinned GitHub parts."""
import argparse, concurrent.futures, hashlib, json, os, time, urllib.request
from pathlib import Path, PurePosixPath

INDEX=Path(__file__).with_name('RESTORE_INPUTS.json')

def sha(data):return hashlib.sha256(data).hexdigest()

def safe(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '\\' in name or '..' in p.parts or ':' in p.parts[0]:
        raise ValueError('Unsafe input path')
    return p

def restore(output, cache):
    index=json.loads(INDEX.read_text());output=Path(output).resolve();cache=Path(cache).resolve()
    output.mkdir(parents=True,exist_ok=True);cache.mkdir(parents=True,exist_ok=True)
    parts={p['index']-1:p for p in index['parts']};split=index['split_size_bytes']
    def fetch(item):
        i,p=item;target=cache/f'{i+1:06d}'
        if target.exists():
            data=target.read_bytes()
            if len(data)==p['bytes'] and sha(data)==p['sha256']:return i
        url='https://raw.githubusercontent.com/AAcer-mk/-/'+p['ref']+'/'+p['path']
        for attempt in range(3):
            try:
                data=urllib.request.urlopen(url,timeout=30).read()
                if len(data)!=p['bytes'] or sha(data)!=p['sha256']:
                    raise ValueError('Part size/SHA256 mismatch: '+p['path'])
                gitsha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                if gitsha!=p['git_blob_sha']:raise ValueError('Git object mismatch')
                temp=target.with_suffix('.partial');temp.write_bytes(data);os.replace(temp,target)
                return i
            except Exception:
                if attempt==2:raise
                time.sleep(.5*(attempt+1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for n,_ in enumerate(pool.map(fetch,sorted(parts.items())),1):
            if n%25==0 or n==len(parts):print('Verified parts',n,'/',len(parts),flush=True)
    receipts=[]
    for m in index['members']:
        offset,remaining=m['data_offset'],m['size'];chunks=[]
        while remaining:
            i,within=divmod(offset,split);data=(cache/f'{i+1:06d}').read_bytes()
            take=min(remaining,len(data)-within)
            if take<=0:raise ValueError('Invalid member extent')
            chunks.append(data[within:within+take]);offset+=take;remaining-=take
        data=b''.join(chunks)
        if sha(data)!=m['payload_sha256']:raise ValueError('Member mismatch: '+m['path'])
        target=output.joinpath(*safe(m['path']).parts)
        if not target.resolve().is_relative_to(output):raise ValueError('Path escapes output')
        if target.exists():
            if target.read_bytes()!=data:raise FileExistsError('Conflicting existing file: '+str(target))
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_suffix(target.suffix+'.partial')
            with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(temp,target)
        receipts.append({'path':m['path'],'bytes':m['size'],'sha256':sha(data)})
    receipt=output/'SOL61_060902_RESTORE_RECEIPT.json'
    receipt.write_text(json.dumps({'scope':'SELECTED_INPUTS_NOT_FULL_ARCHIVE',
        'verified_parts':len(parts),'verified_files':receipts},indent=2))
    print('Restored',len(receipts),'exact original inputs')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--cache',required=True)
    a=p.parse_args();restore(a.output,a.cache)
