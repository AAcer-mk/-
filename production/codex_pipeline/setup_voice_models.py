#!/usr/bin/env python3
"""Reproduce the film's recorded Kokoro models with exact size/SHA checks."""
import argparse
import hashlib
from pathlib import Path
import urllib.request
from voice_models import EXPECTED


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    for name,(size,want) in EXPECTED.items():
        dst=args.output/name
        if dst.exists():
            with dst.open('rb') as f:have=hashlib.file_digest(f,'sha256').hexdigest()
            if dst.stat().st_size!=size or have!=want:raise ValueError('Existing model differs; preserve it and choose another directory: '+str(dst))
            print('Verified cached model:',name);continue
        temporary=dst.with_name(dst.name+'.download')
        if temporary.exists():raise FileExistsError('Preserve incomplete download and choose a new revision: '+str(temporary))
        url='https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/'+name
        digest=hashlib.sha256();count=0
        with urllib.request.urlopen(url,timeout=60) as response,temporary.open('xb') as output:
            for data in iter(lambda:response.read(1024*1024),b''):
                output.write(data);digest.update(data);count+=len(data)
        if count!=size or digest.hexdigest()!=want:raise ValueError('Downloaded model checksum failed: '+name)
        temporary.replace(dst);print('Downloaded and verified:',name)


if __name__=='__main__':main()
