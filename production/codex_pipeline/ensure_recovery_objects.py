#!/usr/bin/env python3
"""Fetch only missing recovery objects, in one native Git batch.

Existing packfiles are enumerated without triggering promisor lazy downloads.
No re-fetch of the gigabyte archive when the local object cache is complete.
"""
import argparse
import json
from pathlib import Path
import subprocess
from recover_git import BASE,RANGES


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--scope',choices=['all','rounds','old'],default='all');p.add_argument('--output',type=Path)
    args=p.parse_args()
    def git(*argv,input=None):return subprocess.check_output(['git','-C',str(args.repo),*argv],input=input)
    selections=[]
    if args.scope=='all':
        selections.extend((ref,['transfer']) for _,ref in RANGES)
        selections.append(('c15958ff2701f9d41ac83044dd595eaf64ccae30',['transfer/rebuild-handoff/TAR_STRUCTURE.json']))
    paths=[]
    if args.scope in ['all','rounds']:paths.extend('production/sol61_r'+str(n) for n in range(2,7))
    if args.scope in ['all','old']:paths.append('production/sol61')
    selections.append((BASE,paths))
    commits=sorted(set(ref for ref,_ in selections));missing_commits=[]
    for ref in commits:
        if subprocess.run(['git','-C',str(args.repo),'cat-file','-e',ref+'^{commit}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:missing_commits.append(ref)
    if missing_commits:git('fetch','--quiet','--filter=blob:none','--no-tags','origin',*missing_commits)
    needed=set()
    for ref,paths in selections:
        for line in git('ls-tree','-r',ref,'--',*paths).decode().splitlines():
            meta,_=line.split('\t',1);_,kind,oid=meta.split()
            if kind=='blob':needed.add(oid)
    if not needed:raise ValueError('No recovery objects found')
    available=set(git('cat-file','--batch-all-objects','--batch-check=%(objectname)').decode().splitlines())
    missing=sorted(needed-available)
    if missing:git('fetch','--quiet','--no-tags','--stdin','origin',input=('\n'.join(missing)+'\n').encode())
    available=set(git('cat-file','--batch-all-objects','--batch-check=%(objectname)').decode().splitlines())
    if not needed<=available:raise ValueError('Recovery object batch remains incomplete')
    report={'scope':args.scope,'needed_blob_objects':len(needed),'existing_blobs_reused':len(needed)-len(missing),
            'missing_blobs_fetched':len(missing),'all_recovery_objects_present':True,'native_git_auth':True}
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
