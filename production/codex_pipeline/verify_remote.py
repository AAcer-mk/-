#!/usr/bin/env python3
"""Fresh Git object-store readback, not a read of already-local tracking refs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def git(store,*args,input=None):
    return subprocess.check_output(['git','-C',str(store),*args],input=input)


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--store',type=Path,required=True);p.add_argument('--commit',required=True)
    p.add_argument('--prefix',default='production/codex_pipeline/deliverables')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.commit=git(args.repo,'rev-parse','--verify',args.commit+'^{commit}').decode().strip()
    if not (args.store/'HEAD').exists():
        args.store.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','init','--bare','-q',str(args.store)],check=True)
        git(args.store,'remote','add','origin','https://github.com/AAcer-mk/-.git')
        git(args.store,'config','remote.origin.promisor','true')
        git(args.store,'config','remote.origin.partialclonefilter','blob:none')
    git(args.store,'fetch','--quiet','--depth=1','--filter=blob:none','--no-tags','origin',args.commit)
    assert git(args.store,'rev-parse','FETCH_HEAD').decode().strip()==args.commit
    files=[]
    for line in git(args.store,'ls-tree','-r',args.commit,'--',args.prefix).decode().splitlines():
        meta,name=line.split('\t',1);oid=meta.split()[2];files.append((oid,name))
    if not files:raise ValueError('No remotely committed files for prefix')
    # Fetch reachable blobs as a single batch, rather than thousands of requests.
    git(args.store,'fetch','--quiet','--no-tags','--stdin','origin',input=('\n'.join(sorted(set(oid for oid,_ in files)))+'\n').encode())
    cat=subprocess.Popen(['git','-C',str(args.store),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    rows=[]
    try:
        for oid,name in files:
            cat.stdin.write((oid+'\n').encode());cat.stdin.flush()
            header=cat.stdout.readline().decode().split();assert header[1]=='blob'
            data=cat.stdout.read(int(header[2]));assert cat.stdout.read(1)==b'\n'
            local=args.repo/name
            with local.open('rb') as f:expected=hashlib.file_digest(f,'sha256').hexdigest()
            actual=hashlib.sha256(data).hexdigest()
            assert actual==expected and len(data)==local.stat().st_size,name
            rows.append({'path':name,'bytes':len(data),'sha256':actual,'git_blob':oid})
    finally:
        cat.stdin.close();cat.wait()
    report={'commit':args.commit,'verified_remote_files':len(rows),'verified_bytes':sum(r['bytes'] for r in rows),
            'fresh_bare_store':str(args.store),'readback':'NATIVE_GIT_NEW_OBJECT_STORE',
            'all_bytes_match_local':True,'files':rows}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2))
    print('Verified fresh remote readback:',len(rows),'files;',report['verified_bytes'],'bytes')


if __name__=='__main__':main()
