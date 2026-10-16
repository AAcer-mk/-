#!/usr/bin/env python3
"""Use the recovered director's actual geometric mark, not a redesigned logo."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from PIL import Image,ImageDraw


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--frames',type=int,required=True)
    args=p.parse_args();sys.dont_write_bytecode=True
    canonical=args.source/'project/native_scenes.py'
    spec=importlib.util.spec_from_file_location('inherited_native_scenes',canonical)
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    args.output.mkdir(parents=True,exist_ok=True)
    for frame in range(1,args.frames+1):
        phase=(frame-1)/max(1,args.frames-1)
        # Projection at the current lens stays below 180 px in a 1080p frame.
        size=96+10*math.sin(phase*6*math.pi)
        scale=4;im=Image.new('RGB',(1024*scale,600*scale),'#090f0e')
        native.mark(ImageDraw.Draw(im),'minimax',(512-size/2)*scale,(300-size/2)*scale,size*scale)
        im=im.resize((1024,600),Image.Resampling.LANCZOS)
        dst=args.output/f'{frame:06d}.png';temp=dst.with_name(dst.stem+'.pending.png');im.save(temp);temp.replace(dst)
    (args.output/'CANONICAL_SCREEN.json').write_text(json.dumps({
        'source':'baseline/project/native_scenes.py:mark(minimax)',
        'source_sha256':hashlib.sha256(canonical.read_bytes()).hexdigest(),
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'frames':args.frames,'glyph_geometry':'INHERITED_UNCHANGED','texture_max_glyph_size_px':106,
        'target_container_max_glyph_size_px':180},indent=2))


if __name__=='__main__':main()
