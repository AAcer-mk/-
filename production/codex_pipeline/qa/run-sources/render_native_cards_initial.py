#!/usr/bin/env python3
"""Render the two unrendered authored cards using the inherited card function.

Appropriate native typography, explicitly 2D. No actor or location substitution.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image

HERE=Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def run(argv):subprocess.run(list(map(str,argv)),check=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);args=p.parse_args()
    sys.dont_write_bytecode=True;sys.path.insert(0,str(args.source/'project'))
    original=args.source/'project/film_compositor.py'
    spec=importlib.util.spec_from_file_location('original_compositor',original)
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    timeline=json.loads((args.source/'project/full_picture_timeline.json').read_text())
    for shot in ['E8-CARD','E9-CARD']:
        row=next(s for s in timeline if s['id']==shot);count=row['end_frame']-row['start_frame']
        config={'shot':shot,'mode':'native_card','frames':count,'width':1920,'height':1080,'fps':24,
                'original_card_source_sha256':sha(original),'original_marks_source_sha256':sha(args.source/'project/native_scenes.py'),
                'font_sha256':sha(args.source/'graphics/fonts/NotoSansMonoCJKsc-Regular.otf'),
                'timeline_sha256':sha(args.source/'project/full_picture_timeline.json'),
                'runner_sha256':sha(Path(__file__)),'sample':False}
        identity=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:12]
        cache=HERE/'output'/shot/identity;frames=cache/'frames';frames.mkdir(parents=True,exist_ok=True)
        state_path=cache/'state.json';state=json.loads(state_path.read_text()) if state_path.exists() else {'config':config,'verified_frames':{}}
        for frame in range(1,count+1):
            path=frames/f'{frame:06d}.png'
            if path.exists():
                if state['verified_frames'].get(path.name)!=sha(path):raise ValueError('Cached frame differs')
                with Image.open(path) as im:im.load()
            else:
                im=native.card(row,(frame-1)/max(1,count-1));temporary=path.with_suffix('.pending.png');im.save(temporary);temporary.replace(path)
            state['verified_frames'][path.name]=sha(path)
            temp=state_path.with_suffix('.pending.json');temp.write_text(json.dumps(state,indent=2));temp.replace(state_path)
        picture=cache/(shot+'_PICTURE.mp4')
        if not picture.exists():
            temp=cache/(shot+'.pending.mp4')
            run(['ffmpeg','-v','error','-n','-framerate','24','-i',frames/'%06d.png','-frames:v',count,
                 '-c:v','libx264','-crf','17','-preset','medium','-threads','1','-pix_fmt','yuv420p',
                 '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-video_track_timescale','24000','-movflags','+faststart',temp]);temp.replace(picture)
        run([sys.executable,HERE/'conform_audio.py','--source',args.source,'--shot',shot,'--picture',picture,'--output',cache/'conformed','--output-label','2D'])
        run(['node',HERE/'browser_playback.cjs',cache/'conformed'/(shot+'_2D_REVIEW.mp4')])
        destination=HERE/'deliverables'/shot
        if (destination/'DELIVERY.json').exists():raise FileExistsError('Preserve earlier delivery; choose a new revision')
        destination.mkdir(parents=True,exist_ok=True)
        for file in [picture,state_path,*list((cache/'conformed').iterdir())]:shutil.copy2(file,destination/file.name)
        (destination/'keyframes').mkdir(exist_ok=True)
        for frame in [1,count//2,count]:shutil.copy2(frames/f'{frame:06d}.png',destination/'keyframes'/f'{frame:06d}.png')
        files=[{'path':str(f.relative_to(destination)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(destination.rglob('*')) if f.is_file()]
        receipt={'shot':shot,'type':'AUTHORED_NATIVE_GRAPHICS','configuration':config,
                 'motion_type':'PROGRAMMATIC_2D_TYPEWRITING','source_method':'Unmodified recovered film_compositor.card',
                 'all_files':files,'final_film':False,'director_final_acceptance':False}
        (destination/'DELIVERY.json').write_text(json.dumps(receipt,indent=2));print('DELIVERED',shot,flush=True)


if __name__=='__main__':main()
