#!/usr/bin/env python3
"""E7 authored sound conform. Preserve old mix and all film audio outside E7.

Procedural original foley/score; inherited radio line EQ, not new voice acting.
"""
import argparse,hashlib,importlib.util,json,math,os,subprocess
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfilt,sosfiltfilt,resample_poly
ROOT=Path(__file__).resolve().parent
SR=48000;SECONDS=65;N=SR*SECONDS

def atomic_run(args):
    args=list(map(str,args));target=Path(args[-1]);save=target.suffix.lower() in ['.flac','.mkv','.mp4','.wav']
    if save:
        if target.exists():raise FileExistsError(target)
        tmp=target.with_name(target.stem+'.pending'+target.suffix);args[-1]=str(tmp)
    r=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror']+args,capture_output=True,text=True)
    assert r.returncode==0 and not r.stderr,(r.returncode,r.stderr[:1000])
    if save:
        with tmp.open('rb') as f:os.fsync(f.fileno())
        tmp.rename(target)

def mod(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def pcm(path,start=None,end=None):
    args=['ffmpeg','-nostdin','-v','error','-xerror','-i',str(path)]
    if start is not None:args+=['-af',f'atrim=start_sample={start}:end_sample={end},asetpts=PTS-STARTPTS']
    return subprocess.check_output(args+['-f','s32le','pipe:1'])
def window_hash(path,first,last):
    p=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(path),'-af',
        f'atrim=start_sample={first}:end_sample={last},asetpts=PTS-STARTPTS','-f','s32le','pipe:1'],stdout=subprocess.PIPE)
    h=hashlib.sha256();n=0;nonzero=0
    while b:=p.stdout.read(4*1024*1024):
        h.update(b);n+=len(b);nonzero+=int(np.count_nonzero(np.frombuffer(b,dtype='<i4')))
    p.stdout.close();assert p.wait()==0
    return {'sample_frames':n//8,'pcm_sha256':h.hexdigest(),'nonzero_samples':nonzero}
def put(dst,t,sound,gain=1,pan=0):
    i=round(t*SR);count=min(len(sound),len(dst)-i)
    if count<=0:return
    # Constant power stereo; deterministic clean machinery, no glitch layer.
    dst[i:i+count,0]+=sound[:count]*gain*math.sqrt((1-pan)/2)
    dst[i:i+count,1]+=sound[:count]*gain*math.sqrt((1+pan)/2)
def rms(a):return float(np.sqrt(np.mean(np.asarray(a,dtype=np.float64)**2)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--picture',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();original=a.source.resolve();picture=a.picture.resolve();out=a.output.resolve()
    if out.exists():raise FileExistsError('Use a new output directory; preserve every prior version.')
    out.mkdir(parents=True)
    helper=mod('r4_io',ROOT.parent/'sol61_r4/build_r4.py');check=mod('r2_check',ROOT.parent/'sol61_r2/build_continuation.py')
    run=atomic_run
    mix=original/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'
    tl=json.loads((original/'project/full_picture_timeline.json').read_text());lookup={x['id']:x for x in tl}
    rng=np.random.default_rng(20261014)
    stems={name:np.zeros((N,2),np.float32) for name in ['ROOM_DRONE','PRINTERS','FOOTSTEPS','STAMPS','HEARTBEAT','RADIO_SOURCE_FILTERED']}
    cues=[]
    def cue(layer,t,snd,gain,pan,shot,kind):
        put(stems[layer],t,snd,gain,pan);cues.append({'layer':layer,'shot':shot,'kind':kind,'relative_seconds':t,
            'absolute_seconds':705+t,'sample':round(t*SR),'duration_seconds':len(snd)/SR,'gain':gain,'pan':pan})
    # No melody. Quiet room/low drone anchors the scene without imposing the
    # old one-second percussive loop on the exterior and title card.
    t=np.arange(N,dtype=np.float64)/SR
    mono=.0045*np.sin(2*np.pi*41*t)+.0025*np.sin(2*np.pi*61.7*t)+.0016*np.sin(2*np.pi*83.3*t)
    room=np.ones(N);room[:round(11.5*SR)]=.23
    room[round(11.5*SR):round(12*SR)]=np.linspace(.23,1,round(.5*SR))
    room[:round(.12*SR)]*=np.linspace(0,1,round(.12*SR))
    stems['ROOM_DRONE'][:,0]=(mono*room).astype(np.float32)
    stems['ROOM_DRONE'][:,1]=(mono*room*.97).astype(np.float32)
    # Impact has woody/rubber contact, not a bass drum. Same source for stamp
    # events, changing timing/gain connects the montage to the cardiac score.
    u=np.arange(round(.43*SR))/SR
    noise=sosfilt(butter(3,[500,2400],btype='bandpass',fs=SR,output='sos'),rng.normal(0,1,len(u)))
    stamp=(.32*np.sin(2*np.pi*112*u)*np.exp(-u*21)+.18*np.sin(2*np.pi*287*u)*np.exp(-u*36)
           +.09*np.sin(2*np.pi*690*u)*np.exp(-u*65)+.35*noise*np.exp(-u*95))
    stamp*=np.minimum(1,u/.0008);stamp/=np.max(np.abs(stamp))
    cue('STAMPS',4.2,stamp,.25,-.05,'E7-01','ONE exterior stamp, frame5 sync')
    cue('STAMPS',lookup['E7-04']['start']-705+.15,stamp,.23,0,'E7-04','ONE approval stamp')
    for frame in [0,45,90,132]:
        cue('STAMPS',lookup['E7-05']['start']-705+frame/24+.10,stamp,.20,0,'E7-05','Approval-montage cut stamp')
    # Heels/toes on stone, only during the two authored walking shots.
    u=np.arange(round(.28*SR))/SR
    grit=sosfilt(butter(3,[160,1900],btype='bandpass',fs=SR,output='sos'),rng.normal(0,1,len(u)))
    step=(.42*np.sin(2*np.pi*94*u)*np.exp(-u*26)+.10*grit*np.exp(-u*44));step*=np.minimum(1,u/.003);step/=max(abs(step))
    for sid in ['E7-02','E7-03']:
        first,last=lookup[sid]['start']-705,lookup[sid]['end']-705
        times=np.arange(first+.2,last-.25,.72)
        for i,at in enumerate(times):cue('FOOTSTEPS',float(at),step,.068 if sid=='E7-02' else .056,-.18 if i%2==0 else .18,sid,'Guard stone-floor heel/toe')
    # Clean, fault-free laser printer rhythm: drive motor + rollers + page
    # friction. More spatially distinct engines enter through the corridor.
    u=np.arange(round(.57*SR))/SR
    friction=sosfilt(butter(3,[700,4800],btype='bandpass',fs=SR,output='sos'),rng.normal(0,1,len(u)))
    env=np.sin(np.pi*np.clip(u/.57,0,1))**1.5
    printer=(.70*np.sin(2*np.pi*173*u)+.22*np.sin(2*np.pi*346*u)+.12*friction)*env
    printer/=max(abs(printer))
    for engine,(pan,phase) in enumerate([(-.72,0),(.72,.31),(-.35,.56),(.35,.80)]):
        at=11.7+phase
        while at<65-.65:
            gain=.007 if at<17.125 else .010+min(.008,max(0,(at-17.125)/9.4166667)*.008)
            if at>=32.1667:gain*=.67
            if at>=60.125:gain*=.86
            if engine>=2 and at<18.8:at+=1.38;continue
            cue('PRINTERS',at,printer,gain,pan,'E7-02..09','Engine'+str(engine+1)+' continuous clean page feed')
            at+=1.38 if at<26.5417 else 1.12
    # Cardiac pattern grows out of stamp rhythm; beat layer alone stops
    # abruptly four frames before E7-08 end. Printers/room continue.
    u=np.arange(round(.42*SR))/SR
    lub=np.sin(2*np.pi*(72*u-19*u*u))*np.exp(-u*15)*np.minimum(1,u/.002)
    dub=np.sin(2*np.pi*(91*u-22*u*u))*np.exp(-u*24)*np.minimum(1,u/.0015)
    stop=60.125;stop_sample=round(stop*SR);at=36.45
    while at<stop:
        progress=min(1,(at-36.45)/6);gain=.042+.033*progress
        cue('HEARTBEAT',at,lub,gain,0,'E7-05..08','Lub')
        cue('HEARTBEAT',at+.19,dub,gain*.65,0,'E7-05..08','Dub')
        at+=.91-.21*min(1,(at-36.45)/14)
    edge=round(.002*SR);stems['HEARTBEAT'][stop_sample-edge:stop_sample]*=np.linspace(1,0,edge)[:,None]
    stems['HEARTBEAT'][stop_sample:]=0
    assert not np.any(stems['HEARTBEAT'][stop_sample:]) and rms(stems['PRINTERS'][stop_sample:])>0
    # The archive has a working full mix, not an isolated E7 voice stem. Keep
    # exact authored line/timing, use a transparent documented radio-band EQ.
    # This is NOT claimed to be clean source separation or a new voice take.
    start,end=60.90,64.30
    raw=pcm(mix,round((705+start)*SR),round((705+end)*SR))
    voice=np.frombuffer(raw,dtype='<i4').reshape(-1,2).astype(np.float64)/2**31
    candidates=[]
    for v,(lo,hi) in enumerate([(160,4200),(240,3600),(320,3200)],1):
        filt=butter(4,[lo,hi],btype='bandpass',fs=SR,output='sos')
        processed=sosfiltfilt(filt,voice,axis=0).astype(np.float32)
        ramp=round(.012*SR);processed[:ramp]*=np.linspace(0,1,ramp)[:,None];processed[-ramp:]*=np.linspace(1,0,ramp)[:,None]
        candidates.append(processed)
        f=out/f'RADIO_EQ_CANDIDATE_v{v}.flac';write_audio(f,processed)
    voice=candidates[1];stems['RADIO_SOURCE_FILTERED'][round(start*SR):round(end*SR)]=voice
    write_audio(out/'RADIO_ORIGINAL_MIX_WINDOW.flac',np.frombuffer(raw,dtype='<i4').reshape(-1,2).astype(np.float64)/2**31)
    cues.append({'layer':'RADIO_SOURCE_FILTERED','shot':'E7-09','kind':'Inherited line, radio-band EQ; not source-separated',
        'relative_seconds':start,'absolute_seconds':705+start,'sample':round(start*SR),'duration_seconds':end-start,
        'subtitle_voice_absolute_interval':[765.94,769.19],'selected_candidate':2,'EQ_Hz':[240,3600]})
    audio=sum(stems.values());assert max(abs(audio.ravel()))<.75
    files=[]
    for name,data in stems.items():
        f=out/(name+'_r6.flac');write_audio(f,data);files.append(f)
    mixed=out/'E7_SOUND_CONFORM_r6_65S.flac';write_audio(mixed,audio)
    ref=pcm(mixed);assert len(ref)==N*8
    # Old mix kept beside new E7 segment for concrete A/B comparison.
    old=out/'E7_INHERITED_REFERENCE_65S.flac'
    run(['-i',mix,'-af',f'atrim=start_sample={705*SR}:end_sample={770*SR},asetpts=PTS-STARTPTS','-c:a','flac',old])
    ranges=[(16920,17016),(17016,17196),(17557,17872),(18052,18187),(18187,18367),(18367,18480)]
    reel_pcm=b''.join(ref[(first-16920)*2000*8:(last-16920)*2000*8] for first,last in ranges)
    rawfile=out/'REEL_PCM.s32';rawfile.write_bytes(reel_pcm)
    reel_audio=out/'E7_SEVEN_SHOT_SOUND_r6.flac'
    run(['-f','s32le','-ar',48000,'-ac',2,'-i',rawfile,'-c:a','flac',reel_audio]);assert pcm(reel_audio)==reel_pcm
    master=out/'E7_SEVEN_SHOT_SOUND_CONFORM_r6_MASTER.mkv'
    run(['-i',picture,'-i',reel_audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','flac',master])
    mp4=out/'E7_SEVEN_SHOT_SOUND_CONFORM_r6_1080P_BILINGUAL.mp4'
    run(['-i',picture,'-i',reel_audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',mp4])
    reports=[check.validate(master,1019,reel_pcm),check.validate(mp4,1019,reel_pcm)]
    def video_hash(path):return hashlib.sha256(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0','-c:v','copy','-f','h264','pipe:1'])).hexdigest()
    vhash=video_hash(picture);assert video_hash(master)==video_hash(mp4)==vhash
    # Reconstruct the full-film sound candidate without changing any sample
    # outside E7, including END-03's protected hard six-second zero interval.
    full=out/'SILENT_PROTOCOL_MIX_E7_SOUND_r6_18M15S.flac'
    fc=f'[0:a]asplit=2[pre][post];[pre]atrim=end_sample={705*SR},asetpts=PTS-STARTPTS[A];[post]atrim=start_sample={770*SR},asetpts=PTS-STARTPTS[C];[1:a]asetpts=PTS-STARTPTS[B];[A][B][C]concat=n=3:v=0:a=1[out]'
    run(['-i',mix,'-i',mixed,'-filter_complex',fc,'-map','[out]','-c:a','flac','-sample_fmt','s32','-bits_per_raw_sample',24,full])
    pre=[window_hash(x,0,705*SR) for x in [mix,full]];post=[window_hash(x,770*SR,1095*SR) for x in [mix,full]]
    assert pre[0]==pre[1] and post[0]==post[1]
    silence=window_hash(full,round(977.5*SR),round(983.5*SR));assert silence['sample_frames']==288000 and silence['nonzero_samples']==0
    for f in files+[mixed,old,full,reel_audio]:run(['-i',f,'-f','null','-'])
    # Clear evidence: one isolated exterior stamp event, heartbeat zero after
    # the hard stop, room/printing nonzero, no full-track mute.
    checkstop=pcm(out/'HEARTBEAT_r6.flac',stop_sample,N);assert not np.any(np.frombuffer(checkstop,dtype='<i4'))
    peak=float(abs(audio).max());radio_after=stems['RADIO_SOURCE_FILTERED'][round(start*SR):round(end*SR)]
    oversample_peak=float(np.max(np.abs(resample_poly(audio,4,1,axis=0))))
    qa={'schema':'silent-protocol-r6-sound','outputs':reports,'source_mix_sha256':sha(mix),
        'new_picture_frames':0,'picture_H264_elementary_sha256':vhash,'picture_stream_byte_identical':True,
        'E7_audio_sample_frames':N,'E7_audio_seconds':65,'E7_original_global_seconds':[705,770],
        'exterior_stamp_count':1,'exterior_stamp_absolute_seconds':709.2,'lights_first_ON_seconds':709+5/24,
        'stamp_to_picture_offset_seconds':5/24-.2,'heartbeat_hard_stop_seconds':705+stop,'heartbeat_stop_sample':stop_sample,
        'heartbeat_samples_after_stop_all_zero':True,'printing_after_stop_RMS':rms(stems['PRINTERS'][stop_sample:]),
        'mix_peak_dBFS':20*math.log10(peak),'four_times_oversampled_peak_dBFS':20*math.log10(oversample_peak),
        'clipped_samples':int(np.count_nonzero(np.abs(audio)>=1)),
        'radio_source':'Inherited mixed window, same Chinese line and time; 240–3600Hz EQ and12ms edge ramp; NOT isolated dialogue or new voice acting',
        'radio_candidates':3,'selected_radio_candidate':2,'radio_residual_background_final_QA':'PENDING',
        'outside_E7_PCM_exact':True,'before_region':pre[0],'after_region':post[0],'END_03':silence,
        'full_mix':'Verified local regenerable derivative, not duplicated in binary delivery; script reconstructs from original B10 plus saved E7 segment',
        'cue_count':len(cues),'cues':cues,'formal_director_sound_acceptance':False,'subjective_listening_final_QA':'PENDING',
        'E7_picture_frames':1019,'E7_missing_picture_frames':541,'E7_complete':False,'final_film_completed':False,
        'dependencies':[{'path':str(x),'sha256':sha(x)} for x in [Path(__file__),mix,picture,original/'docs/ORIGINAL_CREATIVE_BRIEF.txt',original/'project/full_picture_timeline.json']]}
    (out/'SOUND_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    (out/'CUE_SHEET.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2))
    print('E7 SOUND PASS:65s, isolated heartbeat-stop, exterior ONE stamp; R5picture byte-exact; outside-E7 PCM and END-03 PASS.',flush=True)

def write_audio(path,data):
    if path.exists():raise FileExistsError(path)
    tmp=path.with_name(path.stem+'.pending.flac')
    p=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-f','f32le','-ar','48000','-ac','2','-i','pipe:0',
        '-c:a','flac','-sample_fmt','s32','-bits_per_raw_sample','24',str(tmp)],stdin=subprocess.PIPE)
    p.communicate(np.asarray(data,dtype='<f4').tobytes());assert p.returncode==0
    with tmp.open('rb') as f:os.fsync(f.fileno())
    r=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(tmp),'-f','null','-'],capture_output=True,text=True)
    assert r.returncode==0 and not r.stderr,(r.returncode,r.stderr[:1000]);tmp.rename(path)

if __name__=='__main__':main()
