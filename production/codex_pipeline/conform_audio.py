#!/usr/bin/env python3
"""Attach exact existing PCM windows to newly rendered, frame-locked shots.

Never modifies the original mix. Lossless master and AAC listening copy have
separate validation. Reusing a mixed track does not certify voice performance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def run(args):
    return subprocess.check_output(list(map(str,args)))


def pcm(path,start=None,end=None):
    args=['ffmpeg','-v','error','-i',path]
    if start is not None:args+=['-af',f'atrim=start_sample={start}:end_sample={end},asetpts=PTS-STARTPTS']
    args+=['-vn','-ar','48000','-ac','2','-c:a','pcm_s32le','-f','s32le','-']
    return run(args)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--shot',required=True);p.add_argument('--picture',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--e7-mix',type=Path)
    p.add_argument('--output-label',default='3D',choices=['3D','2D'])
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    tl=json.loads((args.source/'project/full_picture_timeline.json').read_text());row=next(s for s in tl if s['id']==args.shot)
    start=row['start_frame']*2000;end=row['end_frame']*2000
    mix=args.source/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'
    if args.shot.startswith('E7-') and args.e7_mix:
        mix=args.e7_mix;start-=16920*2000;end-=16920*2000
    expected=pcm(mix,start,end);assert len(expected)==(end-start)*8
    master=args.output/(args.shot+'_'+args.output_label+'_MASTER.mkv');review=args.output/(args.shot+'_'+args.output_label+'_REVIEW.mp4')
    with tempfile.TemporaryDirectory(dir=args.output) as temp:
        stem=Path(temp)/'stem.flac'
        run(['ffmpeg','-v','error','-n','-i',mix,'-af',f'atrim=start_sample={start}:end_sample={end},asetpts=PTS-STARTPTS',
             '-c:a','flac','-sample_fmt','s32','-ar','48000',stem])
        if not master.exists():
            pending=args.output/(args.shot+'.pending.mkv')
            run(['ffmpeg','-v','error','-n','-i',args.picture,'-i',stem,'-map','0:v:0','-map','1:a:0','-c','copy',pending]);pending.replace(master)
        actual=pcm(master);assert actual==expected,'Lossless PCM changed'
        if not review.exists():
            pending=args.output/(args.shot+'.pending.mp4')
            run(['ffmpeg','-v','error','-n','-i',args.picture,'-i',stem,'-map','0:v:0','-map','1:a:0','-c:v','copy',
                 '-c:a','aac','-b:a','192k','-ar','48000','-video_track_timescale','24000','-movflags','+faststart',pending]);pending.replace(review)
    for path in [master,review]:
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],check=True)
        probe=json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',path]))
        video=next(s for s in probe['streams'] if s['codec_type']=='video')
        assert int(video['nb_read_frames'])==row['end_frame']-row['start_frame'] and video['r_frame_rate']=='24/1'
    report={'shot':args.shot,'timeline_frames':[row['start_frame'],row['end_frame']],
            'audio_source':str(mix),'source_local_sample_range':[start,end],
            'lossless_sample_frames':end-start,'lossless_PCM_sha256':hashlib.sha256(actual).hexdigest(),
            'lossless_PCM_exact':True,'fps':'24/1','full_decode':'PASS',
            'AAC_is_lossless':False,'voice_performance_acceptance':'INHERITED_WORK_MIX_NOT_FINAL',
            'outputs':[]}
    for path in [master,review]:
        with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        report['outputs'].append({'path':path.name,'sha256':digest,'bytes':path.stat().st_size})
    (args.output/(args.shot+'_AUDIO_CONFORM.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
