#!/usr/bin/env python3
"""F7 workprint from reviewed local-motion endpoints and inherited F7-02.

No AI video generation or phoneme lip sync is claimed. Originals stay untouched.
"""
import argparse, functools, hashlib, importlib.util, json, math, subprocess
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parent
FPS=24; W,H=1920,1080
cv2.setNumThreads(4)

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def run(args):
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror']+args,check=True)

@functools.lru_cache(8)
def plate(name):
    with Image.open(ROOT/'assets'/name) as im:im.load();im=im.convert('RGB')
    size=(1670,942) if name.startswith('F7-01') else (1940,811)
    assert max(abs(a-b) for a,b in zip(im.size,size))<=1,(name,im.size,size)
    return im if im.size==size else im.resize(size,Image.Resampling.LANCZOS)

class Motion:
    def __init__(self,a,b,polygon):
        self.a=np.asarray(a);self.b=np.asarray(b)
        assert self.a.shape==self.b.shape
        h,w=self.a.shape[:2];sw=835;sh=round(h*sw/w)
        small=[cv2.cvtColor(cv2.resize(x,(sw,sh)),cv2.COLOR_RGB2GRAY) for x in (self.a,self.b)]
        flows=[]
        for i in (0,1):
            dis=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
            dis.setFinestScale(0);dis.setGradientDescentIterations(50)
            dis.setVariationalRefinementIterations(20)
            flows.append(dis.calc(small[i],small[1-i],None))
        self.flows=[cv2.resize(f,(w,h))*np.array([w/sw,h/sh],np.float32) for f in flows]
        self.grid=np.stack(np.meshgrid(np.arange(w,dtype=np.float32),np.arange(h,dtype=np.float32)),axis=-1)
        mask=Image.new('L',(w,h));ImageDraw.Draw(mask).polygon(polygon,fill=255)
        self.mask=np.asarray(mask.filter(ImageFilter.GaussianBlur(1.8)),dtype=np.float32)[:,:,None]/255
    def frame(self,u):
        u=max(0,min(1,u));u=u*u*(3-2*u)
        if u==0:return Image.fromarray(self.a.copy())
        if u==1:blend=self.b
        else:
            ma=self.grid-self.flows[0]*u;mb=self.grid-self.flows[1]*(1-u)
            a=cv2.remap(self.a,ma[:,:,0],ma[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT)
            b=cv2.remap(self.b,mb[:,:,0],mb[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT)
            # Broad endpoint dissolves produced doubled hands/eyes in R3-v2.
            # Select the closest endpoint's warped texture, with only a narrow
            # handoff at the midpoint; both paths describe the same position.
            handoff=max(0,min(1,(u-.475)/.05))
            blend=a.astype(np.float32)*(1-handoff)+b.astype(np.float32)*handoff
        return Image.fromarray(np.clip(blend*self.mask+self.a*(1-self.mask),0,255).astype(np.uint8))

def writing(im,font_path):
    ink=Image.new('RGBA',(600,600));d=ImageDraw.Draw(ink)
    font=ImageFont.truetype(str(font_path),98)
    for i,line in enumerate(['不要相信','任何会','回答你的','东西']):
        d.text((300,42+i*126),line,font=font,fill=(70,58,43,172),anchor='mt')
    ink=ink.rotate(-1.4,resample=Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(.45))
    destination=[(188,503),(317,488),(343,627),(215,646)]
    source=[(0,0),(600,0),(600,600),(0,600)]
    matrix=[];rhs=[]
    for (x,y),(u,v) in zip(destination,source):
        matrix.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);rhs.extend([u,v])
    coeff=np.linalg.solve(np.asarray(matrix),np.asarray(rhs))
    layer=ink.transform(im.size,Image.Transform.PERSPECTIVE,tuple(coeff),Image.Resampling.BICUBIC)
    return Image.alpha_composite(im.convert('RGBA'),layer).convert('RGB')

def letterbox(im,wide=False,brightness=.87):
    im=ImageEnhance.Color(im).enhance(.80)
    im=ImageEnhance.Brightness(im).enhance(brightness)
    if wide:
        canvas=Image.new('RGB',(W,H));canvas.paste(im.resize((W,804),Image.Resampling.LANCZOS),(0,138));return canvas
    im=im.resize((W,H),Image.Resampling.LANCZOS);d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,137),fill='black');d.rectangle((0,942,W,H),fill='black');return im

def encode(path,n,frame):
    if path.exists():raise FileExistsError(path)
    partial=path.with_name(path.stem+'.partial.mp4')
    proc=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-f','rawvideo','-pix_fmt','rgb24',
        '-s','1920x1080','-r','24','-i','pipe:0','-an','-vf','noise=alls=1:allf=t+u,chromashift=cbh=1:crh=-1',
        '-c:v','libx264','-crf','19','-preset','veryfast','-threads','4','-pix_fmt','yuv420p',
        '-video_track_timescale','24000','-movflags','+faststart',str(partial)],stdin=subprocess.PIPE)
    try:
        for i in range(n):proc.stdin.write(frame(i).tobytes())
    finally:proc.stdin.close()
    assert proc.wait()==0
    run(['-i',str(partial),'-f','null','-']);partial.rename(path)

def probe(p,frames,audio=False):
    run(['-i',str(p),'-f','null','-'])
    r=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(p)]))
    v=next(x for x in r['streams'] if x['codec_type']=='video')
    assert v['width']==W and v['height']==H and int(v['nb_read_frames'])==frames
    assert v['avg_frame_rate']=='24/1'
    return {'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p),'frames':frames,'fps':24,
        'duration':frames/FPS,'decode':'PASS','resolution':[W,H],'audio':audio}

def pcm(p):
    return subprocess.check_output(['ffmpeg','-v','error','-xerror','-i',str(p),'-map','0:a:0','-f','s32le','pipe:1'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--inherited',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();source=args.source.resolve();out=args.output.resolve()
    if out.exists():raise FileExistsError('Use a new revision directory; preserve existing evidence.')
    out.mkdir(parents=True)
    original=source/'project/native_scenes.py'
    spec=importlib.util.spec_from_file_location('original_native',original);native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    font=source/'graphics/fonts/NotoSansMonoCJKsc-Regular.otf'
    before=plate('F7-01_v1.png');after=plate('F7-01_v3.png')
    assert before.size==after.size==(1670,942)
    arm=Motion(before,after,[(744,480),(850,486),(955,532),(1052,525),(1058,697),(804,708),(743,649)])
    # Entire bank stays the initial photograph; only reviewed hands/sixth lever move.
    def lever(i):
        t=i/FPS
        if t<1:
            im=native.terminal('shutdown --cluster grok --confirm',min(1,t/.82),1)
            d=ImageDraw.Draw(im);d.rectangle((0,0,W,137),fill='black');d.rectangle((0,942,W,H),fill='black');return im
        im=arm.frame((t-1.2)/.4)
        # Hard state change on first video frame after the source mechanical click.
        if i>=39:im.paste(after.crop((899,341,1010,457)),(899,341))
        d=ImageDraw.Draw(im)
        for k,cx in enumerate([952,1081,1214,1342],5):
            if k>=(6 if i>=39 else 5):native.mark(d,native.KEYS[k],cx-25,376,50)
        return letterbox(im,brightness=.87 if i>=39 else .896)
    gaze=Motion(plate('F7-03_v1.png'),plate('F7-03_v4.png'),
        [(814,277),(1031,277),(1031,359),(814,359)])
    assert plate('F7-03_v1.png').size==(1940,811)
    def face(i):
        t=i/FPS
        im=gaze.frame((t-.20)/2.4)
        return letterbox(writing(im,font),wide=True)
    f1=out/'F7-01_PICTURE_r3_1080P.mp4';f3=out/'F7-03_PICTURE_r3_1080P.mp4'
    encode(f1,168,lever);print('F7-01',168,'frames encoded',flush=True)
    encode(f3,240,face);print('F7-03',240,'frames encoded',flush=True)
    inherited=args.inherited.resolve();assert probe(inherited,192)['decode']=='PASS'
    concat=out/'F7_concat.txt';concat.write_text(''.join("file '"+str(f)+"'\n" for f in [f1,inherited,f3]))
    mix=source/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'
    wav=out/'F7_source_mix.wav'
    run(['-i',str(mix),'-af','atrim=start_sample=32640000:end_sample=33840000,asetpts=PTS-STARTPTS','-c:a','pcm_s24le',str(wav)])
    reference=pcm(wav);assert len(reference)==1200000*8
    master=out/'F7_SEQUENCE_WORKPRINT_r3_MASTER.mkv'
    run(['-f','concat','-safe','0','-i',str(concat),'-i',str(wav),'-map','0:v','-map','1:a',
        '-vf','setpts=N/(24*TB)','-r','24','-c:v','libx264','-crf','18','-preset','veryfast','-threads','4',
        '-pix_fmt','yuv420p','-frames:v','600','-c:a','flac',str(master)])
    assert pcm(master)==reference
    spec=importlib.util.spec_from_file_location('r2_helpers',ROOT.parent/'sol61_r2/build_continuation.py')
    helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
    ass=out/'F7_local_bilingual.ass';events=helpers.subtitles(source,680,705,ass)
    reports=[probe(f1,168),probe(f3,240),probe(master,600,True)]
    for subtitle in [False,True]:
        name='BILINGUAL' if subtitle else 'CLEAN';target=out/f'F7_SEQUENCE_WORKPRINT_r3_1080P_{name}.mp4'
        vf='setpts=N/(24*TB)'
        if subtitle:vf+=f',ass={ass}:fontsdir={font.parent}'
        run(['-i',str(master),'-vf',vf,'-r','24','-c:v','libx264','-crf','18','-preset','veryfast',
            '-threads','4','-pix_fmt','yuv420p','-video_track_timescale','24000','-frames:v','600',
            '-c:a','aac','-b:a','192k','-movflags','+faststart',str(target)])
        report=probe(target,600,True);decoded=pcm(target)
        assert 1200000*8<=len(decoded)<1200000*8+8192
        report['aac_padding_stereo_sample_frames']=len(decoded)//8-1200000;reports.append(report)
    # Extract only decoded delivery frames, including the frame immediately around contact.
    for idx in [24,29,33,38,39,44,160,168,180,359,360,373,394,418,456,485,535,580]:
        run(['-i',str(out/'F7_SEQUENCE_WORKPRINT_r3_1080P_BILINGUAL.mp4'),'-vf',rf'select=eq(n\,{idx})',
            '-fps_mode','vfr','-frames:v','1',str(out/f'F7_decoded_frame_{idx:04d}.jpg')])
    # Count nine fixed display interiors by actual encoded pixels, not by filename.
    images=[np.asarray(Image.open(out/f'F7_decoded_frame_{i:04d}.jpg').convert('RGB')) for i in [38,39,160]]
    centers=[(323,401),(449,401),(579,401),(703,401),(828,373),(952,373),(1081,401),(1214,401),(1342,401)]
    states=[]
    for idx,im in zip([38,39,160],images):
        green=[];means=[]
        for x,y in centers:
            px,py=round(x*1920/1670),round(y*1080/942)
            a=im[py-8:py+8,px-8:px+8].mean(axis=(0,1));means.append(a.tolist());green.append(bool(a[1]>50 and a[1]>a[0]*1.7))
        expected=4 if idx<39 else 3;assert sum(green)==expected,(idx,means)
        states.append({'absolute_frame':16320+idx,'local_frame':idx,'green':green,'green_count':sum(green),'rgb_means':means})
    values=np.frombuffer(reference,dtype='<i4').astype(np.float64)/2147483648
    dep=[original,font,mix,source/'project/full_picture_timeline.json',source/'docs/ORIGINAL_CREATIVE_BRIEF.txt',inherited,
        ROOT/'build_f7.py']+sorted((ROOT/'assets').glob('F7-*.png'))
    report={'schema':'silent-protocol-f7-r3','base_commit':'7eed0bf58d268fcc5d223b0b65c058662bdb83b5',
        'shots':{'F7-01':{'frames':168,'range':[16320,16488],'selected_endpoints':[1,3]},
        'F7-02':{'frames':192,'range':[16488,16680],'source':'Inherited R2 picture, not rerendered'},
        'F7-03':{'frames':240,'range':[16680,16920],'selected_endpoints':[1,4],'motion_scope':'Eyes only; head/face/arms remain the original photograph; phoneme lip sync not produced'}},
        'frames':600,'seconds':25,'new_unique_frames':408,'new_unique_seconds':17,
        'motion':'Reviewed source photographs + bounded bidirectional optical-flow interpolation; not AI-video actor generation or phoneme lip sync',
        'manual_action_click_local_seconds':1.6,'actual_click_first_sample_above_0_15_local_seconds':1.6003333333333334,
        'first_sixth_screen_black_local_frame':39,'black_vs_click_seconds':.025,'encoded_display_checks':states,
        'audio_source_sample_range':[32640000,33840000],'lossless_master_pcm_identical':True,
        'stereo_sample_frames':1200000,'audio_peak_dbfs':float(20*np.log10(max(abs(values).max(),1e-12))),
        'clipped_samples':int(np.count_nonzero(abs(values)>=1)),
        'subtitle_events':events,'inherited_dialogue_gap_seconds':2.35,
        'voice_breath_terminal_pitch_and_lip_sync':'PENDING_CREATIVE_ACCEPTANCE',
        'note':'Exact original Chinese text projected onto photographed paper; right monitor back is not decorated with UI',
        'source_defects_preserved':'Original F6-04_v3 contains ten visible units; R3 F7-01_v2 has an extra phantom held unit and is rejected. F7-01 selects corrected v1/v3 only.',
        'dependencies':[{'path':str(f),'sha256':sha(f)} for f in dep],
        'opencv_version':cv2.__version__,'outputs':reports,'director_changes':[],'final_film_completed':False}
    report['source_size_normalization']='Up to one pixel of generator size drift normalized inside compositor only; source PNG bytes preserved.'
    (out/'F7_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('F7 600 frames; source PCM identical; encoded display states checked',flush=True)

if __name__=='__main__':main()
