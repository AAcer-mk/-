#!/usr/bin/env python3
"""Conform inherited E6 screens; render native F7-02. Never fill missing E6 action."""
import argparse, hashlib, importlib.util, json, re, subprocess
from pathlib import Path
import numpy as np
from PIL import ImageDraw

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def run(args):
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-xerror'] + args, check=True)

def pcm(p):
    return subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(p),
        '-map', '0:a:0', '-f', 's32le', 'pipe:1'])

def clock(t):
    c = round(t * 100)
    return f'{c//360000}:{c//6000%60:02d}:{c//100%60:02d}.{c%100:02d}'

def subtitles(source, start, end, target):
    raw = (source/'subtitles/SILENT_PROTOCOL_BILINGUAL.ass').read_text()
    header = raw.split('Dialogue:', 1)[0]
    events = []
    def seconds(s):
        h,m,t = s.split(':'); return int(h)*3600 + int(m)*60 + float(t)
    for line in raw.splitlines():
        if not line.startswith('Dialogue:'): continue
        row = line.split(',', 9)
        a,b = seconds(row[1]), seconds(row[2])
        if a < end and b > start:
            row[1],row[2] = clock(max(0,a-start)), clock(min(end-start,b-start))
            events.append(','.join(row))
    target.write_text(header + '\n'.join(events) + '\n')
    return events

def validate(p, frames, reference):
    run(['-i',str(p),'-f','null','-'])
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames',
        '-show_streams','-show_format','-of','json',str(p)]))
    v = next(x for x in probe['streams'] if x['codec_type']=='video')
    assert int(v['nb_read_frames']) == frames and v['avg_frame_rate']=='24/1'
    assert v['width']==1920 and v['height']==1080
    audio = next(x for x in probe['streams'] if x['codec_type']=='audio')
    data = pcm(p)
    expected = frames*2000*8
    if audio['codec_name']=='flac':
        assert len(data)==expected and data==reference
    else:
        assert expected <= len(data) < expected + 8192
    values = np.frombuffer(data,dtype='<i4').astype(np.float64)/2147483648
    return {'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p),'frames':frames,
        'seconds':frames/24,'resolution':[1920,1080],'fps':24,'decode':'PASS',
        'audio_codec':audio['codec_name'],'decoded_stereo_sample_frames':len(data)//8,
        'codec_padding_sample_frames':len(data)//8-frames*2000,
        'lossless_pcm_matches_source':data==reference if audio['codec_name']=='flac' else None,
        'peak_dbfs':float(20*np.log10(max(np.abs(values).max(),1e-12))),
        'clipped_samples':int(np.count_nonzero(np.abs(values)>=1)),
        'creative_status':'WORKPRINT_NOT_FINAL_ACTING_OR_DIRECTOR_ACCEPTANCE'}

def main():
    p=argparse.ArgumentParser()
    for name in ['source','peer','screens','output']:p.add_argument('--'+name,required=True)
    args=p.parse_args();source,peer,screens,out=[Path(getattr(args,k)).resolve() for k in ['source','peer','screens','output']]
    if out.exists():raise FileExistsError('Use a new output directory; existing evidence is preserved.')
    out.mkdir(parents=True)
    timeline=json.loads((source/'project/full_picture_timeline.json').read_text())
    lookup={s['id']:s for s in timeline}
    mix=source/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'
    deps=[mix,source/'project/native_scenes.py',source/'project/full_picture_timeline.json',
        source/'docs/ORIGINAL_CREATIVE_BRIEF.txt',source/'graphics/fonts/NotoSansMonoCJKsc-Regular.otf',
        source/'subtitles/SILENT_PROTOCOL_BILINGUAL.ass',Path(__file__)]
    reports=[];segments={}
    spec=importlib.util.spec_from_file_location('inherited_native',source/'project/native_scenes.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    plate=native.render('F7-02',0,1)
    d=ImageDraw.Draw(plate);d.rectangle((0,0,1920,137),fill='black');d.rectangle((0,943,1920,1080),fill='black')
    plate.save(out/'F7-02_inherited_plate.png')
    s=lookup['F7-02'];assert s['start_frame']==16488 and s['end_frame']==16680
    picture=out/'F7-02_PICTURE_r2_1080P.mp4'
    run(['-loop','1','-framerate','24','-i',str(out/'F7-02_inherited_plate.png'),
        '-an','-frames:v','192','-vf','noise=alls=1:allf=t+u,chromashift=cbh=1:crh=-1',
        '-c:v','libx264','-crf','19','-preset','veryfast','-threads','4','-pix_fmt','yuv420p',
        '-movflags','+faststart',str(picture)])
    segments['F7-02']=(s['start_frame'],s['end_frame'],[picture])
    ids=['E6-CARD','E6-01','E6-02','E6-03','E6-04','E6-05','E6-06']
    parts=[]
    for sid in ids:
        if sid in ['E6-02','E6-06']:
            f=screens/(sid+'_picture_sol61_060902_v1_1080p.mp4')
        else:f=peer/(sid+'_PICTURE_v1_1080P.mp4')
        assert f.is_file(),f
        parts.append(f);deps.append(f)
    assert sum(lookup[sid]['end_frame']-lookup[sid]['start_frame'] for sid in ids)==1087
    segments['E6_PART_A']=(14760,15847,parts)
    for name,(first,last,parts) in segments.items():
        frames=last-first; start,end=first/24,last/24
        wav=out/(name+'_source_mix.wav')
        run(['-i',str(mix),'-af',f'atrim=start_sample={first*2000}:end_sample={last*2000},asetpts=PTS-STARTPTS',
            '-c:a','pcm_s24le',str(wav)])
        reference=pcm(wav); assert len(reference)==frames*2000*8
        ass=out/(name+'_local_bilingual.ass');events=subtitles(source,start,end,ass)
        master=out/(name+'_WORKPRINT_r2_MASTER.mkv')
        if len(parts)==1:
            input_args=['-i',str(parts[0])];enc=['-c:v','copy']
        else:
            concat=out/(name+'_concat.txt')
            concat.write_text(''.join("file '"+str(f)+"'\n" for f in parts))
            input_args=['-f','concat','-safe','0','-i',str(concat)]
            enc=['-c:v','libx264','-crf','18','-preset','veryfast','-threads','4','-pix_fmt','yuv420p']
        run(input_args+['-i',str(wav),'-map','0:v:0','-map','1:a:0']+enc+
            ['-frames:v',str(frames),'-c:a','flac',str(master)])
        reports.append(validate(master,frames,reference))
        clean=out/(name+'_WORKPRINT_r2_1080P_CLEAN.mp4')
        run(['-i',str(master),'-map','0:v:0','-map','0:a:0','-vf','setpts=N/(24*TB)',
            '-r','24','-c:v','libx264','-crf','18','-preset','veryfast','-threads','4',
            '-pix_fmt','yuv420p','-video_track_timescale','24000','-c:a','aac',
            '-b:a','192k','-frames:v',str(frames),'-movflags','+faststart',str(clean)])
        reports.append(validate(clean,frames,reference))
        bilingual=out/(name+'_WORKPRINT_r2_1080P_BILINGUAL.mp4')
        run(['-i',str(master),'-vf',f"setpts=N/(24*TB),ass={ass.as_posix()}:fontsdir={(source/'graphics/fonts').as_posix()}",
            '-c:v','libx264','-crf','18','-preset','veryfast','-threads','4','-pix_fmt','yuv420p',
            '-r','24','-video_track_timescale','24000','-c:a','aac','-b:a','192k',
            '-frames:v',str(frames),'-movflags','+faststart',str(bilingual)])
        reports.append(validate(bilingual,frames,reference))
        for sec in ([.2,1.8,4.0,7.9] if name=='F7-02' else [5,13,21,29,40,44]):
            run(['-ss',str(sec),'-i',str(bilingual),'-frames:v','1',str(out/f'{name}_decoded_{sec:.1f}.jpg')])
        print(name,frames,'frames; lossless source PCM PASS; subtitle events',len(events),flush=True)
    report={'schema':'silent-protocol-continuation-r2','parent':'d61c38c91107b154b8c33b6bd31f74ac2207b1ce',
        'input_fingerprints':[{'path':str(f),'sha256':sha(f)} for f in deps],
        'outputs':reports,'new_unique_picture_frames':192,'new_unique_picture_seconds':8,
        'E6_part_A_frames':1087,'E6_missing_action_frames':360,
        'F7_missing_shots':['F7-01','F7-03'],'F7_voice_performance':'INHERITED_MIX; BREATH_AND_TERMINAL_PITCH_CREATIVE_QA_PENDING',
        'audio_edit':'None; source mix retained sample-exact in lossless masters',
        'director_changes':[],'final_film_completed':False}
    (out/'CONTINUATION_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
