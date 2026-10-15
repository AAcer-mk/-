#!/usr/bin/env python3
"""Content-addressed Blender shot runner; all frame rates/timing come from B10.

Usage: pipeline.py --source /workspace/silent-protocol-source status
       pipeline.py --source ... render F4-01 --width 1920 --samples 32
       pipeline.py --source ... samples

No placeholder output can pass as a completed shot. Actor-dependent tasks remain
explicitly blocked until their assets and performance are actually available.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
MODES={'F4-01':'fan','E7-07':'printer','F9-04':'screen'}


def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.pending');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));temp.replace(path)


def run(args,log=None):
    subprocess.run(list(map(str,args)),check=True,stdout=log,stderr=subprocess.STDOUT if log else None)


def texture_sequence(source,folder,frames,kind):
    folder.mkdir(parents=True,exist_ok=True)
    font=source/'graphics/fonts/NotoSansMonoCJKsc-Regular.otf'
    if not font.exists():raise FileNotFoundError('Restore original Noto typeface first: '+str(font))
    face=ImageFont.truetype(str(font),44);small=ImageFont.truetype(str(font),24)
    for n in range(1,frames+1):
        dst=folder/f'{n:06d}.png'
        if dst.exists():continue
        im=Image.new('RGB',(1024,600),(9,15,14));d=ImageDraw.Draw(im);t=(n-1)/24
        if kind=='printer':
            d.text((65,80),'剩余任务',font=face,fill='#bec9ba')
            d.text((65,200),'∞',font=ImageFont.truetype(str(font),160),fill='#d7ded0')
            # No finite job count or invented narrative text.
            x=65+int(t*80)%830;d.rectangle((65,460,950,464),fill='#314239')
            d.rectangle((x,460,min(950,x+50),464),fill='#9aa990')
        elif kind=='mirror':
            # Original single mirrored waveform, nearly monochrome, no branding.
            points=[];mirror=[]
            for x in range(90,935):
                u=(x-512)/210;env=math.exp(-u*u/2)
                amp=(22+26*(.5+.5*math.sin(t*2.3)))*env
                y=amp*math.sin((x-90)*.065-t*4)
                points.append((x,300-y));mirror.append((x,300+y))
            d.line(points,fill='#c5c7ca',width=3);d.line(mirror,fill='#c5c7ca',width=3)
        else:
            d.text((64,62),'GENEVA / B4',font=face,fill='#bfc7b2')
            d.text((64,132),'LOCAL MONITOR',font=small,fill='#818e7c')
            for k in range(9):
                x=64+k*100;level=90+int(60*math.sin(t*1.7+k*.9))
                d.rectangle((x,420-level,x+42,420),fill='#6b866c')
            d.line([(64,480),(960,480)],fill='#53614f',width=2)
            d.text((64,515),f'03:03:{int(t)%60:02d} UTC',font=small,fill='#bbc3b3')
        im.save(dst)
    return folder/'000001.png'


def validate(path,frames,width,output):
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)]))
    stream=next(s for s in data['streams'] if s['codec_type']=='video')
    assert int(stream['nb_read_frames'])==frames
    assert stream['r_frame_rate']=='24/1'
    assert stream['width']==width
    run(['ffmpeg','-v','error','-xerror','-threads','2','-i',path,'-f','null','-'])
    receipt={'path':str(path),'sha256':digest(path),'bytes':path.stat().st_size,
             'frames':frames,'fps':'24/1','width':stream['width'],'height':stream['height'],
             'full_decode':'PASS','visual_acceptance':'PENDING_CONTACT_AND_TEMPORAL_REVIEW',
             'voice_acceptance':'NOT_EVALUATED','final_film':False}
    atomic_json(output/'validation.json',receipt)
    return receipt


def render(source,output,shot,mode,frames,width,samples,engine='CYCLES',sample=False):
    config={'shot':shot,'mode':mode,'frames':frames,'width':width,'samples':samples,'engine':engine,
            'scene_script':digest(HERE/'blender_scene.py'),'runner':digest(Path(__file__)),
            'timeline':digest(source/'project/full_picture_timeline.json'),'sample':sample}
    identity=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:12]
    folder=output/shot/identity;folder.mkdir(parents=True,exist_ok=True)
    with (folder/'render.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state_path=folder/'state.json'
        state=json.loads(state_path.read_text()) if state_path.exists() else {'config':config,'status':'PENDING','verified_frames':{}}
        assert state['config']==config
        frame_folder=folder/'frames';frame_folder.mkdir(exist_ok=True)
        # Verify cached frame bytes. Never trust presence alone.
        for frame in frame_folder.glob('*.png'):
            known=state['verified_frames'].get(frame.name)
            with Image.open(frame) as im:im.load();assert im.size==(width,round(width/2.39))
            if known and digest(frame)!=known:raise ValueError('Cached frame hash changed: '+str(frame))
        state['status']='RENDERING';atomic_json(state_path,state)
        args=['blender','-b','-t','4','--python',HERE/'blender_scene.py','--','--mode',mode,'--output',frame_folder,
              '--width',width,'--samples',samples,'--frames',frames,'--engine',engine]
        if mode in ['screen','printer']:
            texture=texture_sequence(source,folder/'textures',frames,'printer' if mode=='printer' else 'mirror' if shot=='F9-04' else 'sample')
            args+=['--texture',texture]
        start=time.monotonic()
        env=os.environ.copy();env['XDG_CACHE_HOME']=str(output/'runtime-cache')
        with (folder/'blender.log').open('a') as log:
            proc=subprocess.Popen(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,env=env)
            try:
                while proc.poll() is None:
                    for frame in frame_folder.glob('*.png'):
                        try:
                            with Image.open(frame) as im:im.load()
                        except Exception:continue # An actively written PNG is not a completed frame.
                        state['verified_frames'][frame.name]=digest(frame)
                    state['updated_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
                    atomic_json(state_path,state);time.sleep(2)
                if proc.returncode:raise RuntimeError('Blender failed; inspect '+str(folder/'blender.log'))
            except BaseException:
                if proc.poll() is None:proc.terminate();proc.wait()
                state['status']='INTERRUPTED_OR_FAILED';atomic_json(state_path,state);raise
        assert len(list(frame_folder.glob('*.png')))==frames
        state['verified_frames']={p.name:digest(p) for p in frame_folder.glob('*.png')}
        picture=folder/(shot+'_PICTURE.mp4')
        if not picture.exists():
            pending=folder/(shot+'_PICTURE.pending.mp4')
            # Preserve 1080p container; active image is a real 2.39:1 render.
            vf=f'pad={width}:{round(width*9/16)//2*2}:(ow-iw)/2:(oh-ih)/2,setsar=1'
            run(['ffmpeg','-v','error','-n','-framerate','24','-i',frame_folder/'%06d.png','-vf',vf,'-frames:v',frames,
                 '-c:v','libx264','-crf','17','-preset','medium','-threads','3','-pix_fmt','yuv420p',
                 '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-video_track_timescale','24000',
                 '-movflags','+faststart',pending])
            validate(pending,frames,width,folder);pending.replace(picture)
        receipt=validate(picture,frames,width,folder)
        state.update(status='TECHNICALLY_VERIFIED_PENDING_CREATIVE_REVIEW',render_wall_seconds=time.monotonic()-start,
                     picture=receipt,production_accepted=False)
        atomic_json(state_path,state)
        print(json.dumps({'folder':str(folder),'picture':str(picture),'frames':frames,'seconds':state['render_wall_seconds']},indent=2),flush=True)
    return folder


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,default=HERE/'output')
    commands=p.add_subparsers(dest='command',required=True)
    commands.add_parser('status');commands.add_parser('next')
    preview=commands.add_parser('samples');preview.add_argument('--width',type=int,default=640);preview.add_argument('--frames',type=int,default=48);preview.add_argument('--samples',type=int,default=12);preview.add_argument('--engine',default='BLENDER_EEVEE_NEXT',choices=['CYCLES','BLENDER_EEVEE_NEXT'])
    r=commands.add_parser('render');r.add_argument('shot',choices=list(MODES));r.add_argument('--width',type=int,default=1920);r.add_argument('--samples',type=int,default=32);r.add_argument('--engine',default='BLENDER_EEVEE_NEXT',choices=['CYCLES','BLENDER_EEVEE_NEXT'])
    args=p.parse_args();timeline=json.loads((args.source/'project/full_picture_timeline.json').read_text())
    if args.command in ['status','next']:
        print(json.dumps({'supported_shots':{r['id']:{'frames':r['end_frame']-r['start_frame'],'mode':MODES[r['id']]} for r in timeline if r['id'] in MODES},
                          'next':'F4-01','actor_rig_status':'UNAPPROVED_TECHNICAL_STUDY','final_film':False},indent=2));return
    if args.command=='samples':
        for mode in ['room','screen','interaction','lowlight','fan']:
            render(args.source,args.output,'TEST-'+mode,mode,args.frames,args.width,args.samples,engine=args.engine,sample=True)
    else:
        row=next(r for r in timeline if r['id']==args.shot)
        render(args.source,args.output,args.shot,MODES[args.shot],row['end_frame']-row['start_frame'],args.width,args.samples,engine=args.engine)


if __name__=='__main__':main()
