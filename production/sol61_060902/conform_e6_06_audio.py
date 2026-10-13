#!/usr/bin/env python3
"""Sample-exact E6-06 conform using recovered working mix, not new voiceover."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
import numpy as np

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def seconds(t):
    h,m,s=t.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)

def ass_time(t):
    cent=round(t*100);return f'{cent//360000}:{cent//6000%60:02d}:{cent//100%60:02d}.{cent%100:02d}'

def srt_time(t):
    ms=round(t*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'

def main(source, output):
    source,output=Path(source).resolve(),Path(output).resolve()
    s=next(x for x in json.loads((source/'project/full_picture_timeline.json').read_text()) if x['id']=='E6-06')
    picture=output/'E6-06_picture_sol61_060902_v1_1080p.mp4'
    master=source/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'
    start,end=s['start_frame']*2000,s['end_frame']*2000
    wav=output/'E6-06_working_mix_sample_exact.wav'
    clean=output/'E6-06_workprint_sol61_060902_v1_clean.mp4'
    bilingual=output/'E6-06_workprint_sol61_060902_v1_bilingual.mp4'
    ass=output/'E6-06_local_bilingual.ass';srt=output/'E6-06_local_bilingual.srt'
    for p in [wav,clean,bilingual,ass,srt]:
        if p.exists():raise FileExistsError(p)
    filter=f'atrim=start_sample={start}:end_sample={end},asetpts=PTS-STARTPTS'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(master),
        '-af',filter,'-c:a','pcm_s24le',str(wav)],check=True)
    cues=[]
    for b in re.split(r'\n\s*\n',(source/'subtitles/SILENT_PROTOCOL_AUDIO_SYNC.srt').read_text().strip()):
        ls=b.splitlines();a,z=map(seconds,ls[1].split(' --> '))
        if a<s['end'] and z>s['start']:
            cues.append({'start':max(0,a-s['start']),'end':min(s['end']-s['start'],z-s['start']),
                'zh':ls[2],'en':' '.join(ls[3:])})
    assert len(cues)==1 and cues[0]['en']=="Relax, it's just a joke. Probably."
    header=(source/'subtitles/SILENT_PROTOCOL_BILINGUAL.ass').read_text().split('Dialogue:',1)[0]
    lines=[];srt_lines=[]
    for i,c in enumerate(cues,1):
        for lang in ('ZH','EN'):
            lines.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},{lang},,0,0,0,,{c[lang.lower()]}")
        srt_lines.append(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['zh']}\n{c['en']}\n")
    ass.write_text(header+'\n'.join(lines)+'\n');srt.write_text('\n'.join(srt_lines))
    subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(picture),'-i',str(wav),
        '-map','0:v','-map','1:a','-c:v','copy','-c:a','flac','-strict','-2',
        '-movflags','+faststart',str(clean)],check=True)
    vf=f"ass={ass.as_posix()}:fontsdir={(source/'graphics/fonts').as_posix()}"
    subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(clean),'-vf',vf,
        '-c:v','libx264','-crf','18','-preset','fast','-threads','3','-pix_fmt','yuv420p',
        '-c:a','copy','-strict','-2','-movflags','+faststart',str(bilingual)],check=True)
    def pcm(p):
        return subprocess.check_output(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(p),
            '-map','0:a','-f','s32le','pipe:1'])
    reference=pcm(wav);assert len(reference)==(end-start)*8
    decoded=[]
    for p in (clean,bilingual):
        r=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(p),'-f','null','-'],capture_output=True)
        assert r.returncode==0,r.stderr
        actual=pcm(p);assert actual==reference
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
        v=next(x for x in probe['streams'] if x['codec_type']=='video')
        assert int(v['nb_frames'])==180 and v['avg_frame_rate']=='24/1'
        decoded.append({'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'full_decode_exit':r.returncode,
            'audio_bit_exact_to_selected_master':True,'frames':180,'probe':probe})
    a=np.frombuffer(reference,dtype='<i4').reshape(-1,2)/2147483648
    report={'status':'AUDIO_CONFORMED_WORKPRINT_NOT_FINAL_MIX','master_sha256':sha(master),
        'source_sample_range':[start,end],'sample_rate':48000,'stereo_sample_frames':end-start,
        'decoded_peak_dbfs':float(20*np.log10(max(abs(a).max(),1e-12))),
        'clipped_samples':int(np.count_nonzero(abs(a)>=1)),'local_cues':cues,'outputs':decoded,
        'subtitle_alignment':'Recovered timing, quantized only to ASS centiseconds',
        'voice_performance_review':'PENDING; prior ASR is historical supporting evidence, not a fresh audition',
        'scope':'No change to full master or any adjacent section'}
    (output/'E6-06_audio_conform.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('E6-06 clean and bilingual conformed; 360000 stereo sample frames preserved')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();main(a.source,a.output)
