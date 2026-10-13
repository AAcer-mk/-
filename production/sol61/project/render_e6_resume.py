"""Render the approved E6 timeline without synthesizing missing action footage.

This creates a contiguous CARD--E6-06 workprint and an independent E6-09.
E6-07 and E6-08 are deliberately not rendered. Original files are read-only.
"""
from pathlib import Path
from functools import lru_cache
import argparse, hashlib, json, math, os, subprocess, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
SOURCE=REPO/'source-b10'
sys.path.insert(0,str(SOURCE/'project'))
import film_compositor as original

W,H,FPS=1920,1080,24
TL=json.loads((SOURCE/'project/full_picture_timeline.json').read_text())
LOOKUP={s['id']:s for s in TL}
PART_A=['E6-CARD','E6-01','E6-02','E6-03','E6-04','E6-05','E6-06']
COLOR='#d0d3ce';MUTED='#868e88'

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

@lru_cache(40)
def font(n):return ImageFont.truetype(str(SOURCE/'graphics/fonts/NotoSansMonoCJKsc-Regular.otf'),n)

@lru_cache(16)
def image(p):
    with Image.open(p) as im:im.load();return im.convert('RGB')

def label(d,x,y,t,n=28,color=COLOR):d.text((x,y),t,font=font(n),fill=color)

def blank_phone():
    return Image.new('RGB',(608,1080),'#111817')

def widescreen(phone):
    im=Image.new('RGB',(W,H),'black');im.paste(phone,((W-608)//2,0));return im

def bars(d,y=50):
    d.line((20,y,588,y),fill='#303832',width=1)

def share(d,x,y,size=26,color=MUTED):
    d.line([(x,y+size*.7),(x+size*.43,y+size*.22),(x+size*.43,y),(x+size,y+size*.42),(x+size*.43,y+size*.81),(x+size*.43,y+size*.54),(x,y+size*.9)],fill=color,width=2)

def laugh_emoji(d,x,y):
    # Original vector rendering of the script's U+1F602 glyph, not a platform asset.
    d.ellipse((x,y,x+32,y+32),fill='#c9b673')
    for dx in (7,20):d.arc((x+dx-2,y+6,x+dx+7,y+14),180,360,fill='#3c392d',width=2)
    d.pieslice((x+8,y+14,x+25,y+27),0,180,fill='#343229')
    d.ellipse((x-4,y+14,x+4,y+27),fill='#7ba6b6');d.ellipse((x+29,y+14,x+37,y+27),fill='#7ba6b6')

def cctv_plate():
    pic=image(ROOT/'assets/E6-04_v3.png')
    return ImageEnhance.Color(pic).enhance(.50)

@lru_cache(16)
def feed_plate(kind):
    if kind=='cody':return ImageOps.fit(cctv_plate(),(576,432),method=Image.Resampling.LANCZOS)
    pic=image(ROOT/'assets/E6-05_v2.png');w,h=pic.size
    # These two real panel boundaries were visually reviewed, not guessed from a montage label.
    box=(0,0,w,round(h*.493)) if kind=='kitchen' else (0,round(h*.502),w,h)
    return ImageEnhance.Color(ImageOps.fit(pic.crop(box),(576,510),method=Image.Resampling.LANCZOS)).enhance(.50)

def feed_card(kind,t=0):
    tile=Image.new('RGB',(608,805),'#111817');d=ImageDraw.Draw(tile)
    d.ellipse((20,18,30,28),fill='#b39478');label(d,45,8,'直播',23)
    plate=feed_plate(kind).copy()
    # Local display modulation only. No fabricated human action or simulated throw.
    if kind=='cody':plate=ImageEnhance.Brightness(plate).enhance(1+.008*math.sin(t*2.1))
    tile.paste(plate,(16,58));d=ImageDraw.Draw(tile)
    if kind=='cody':
        label(d,25,520,'这哥们凌晨三点还不睡，',27)
        label(d,25,562,'猜猜他在看什么',27);laugh_emoji(d,437,564)
    elif kind=='kitchen':
        label(d,25,603,'这位大姐在厨房哭，',28)
        label(d,25,646,'原因竟然是——',28)
    else:
        label(d,25,603,'这对夫妻已经三天没说话了，',25)
        label(d,25,646,'第四天会怎样？',28)
    share(d,552,746);d.line((20,793,588,793),fill='#343b35',width=1)
    return tile

def livestream(p):
    phone=blank_phone();d=ImageDraw.Draw(phone)
    label(d,25,25,'推荐',30);label(d,510,29,'直播',22);bars(d,80)
    phone.paste(feed_card('cody',p*7.5),(0,132));d=ImageDraw.Draw(phone)
    share(d,43,1006);label(d,85,1000,'转发',23)
    return widescreen(phone)

def global_feed(p):
    phone=blank_phone();d=ImageDraw.Draw(phone);label(d,25,25,'推荐',30);bars(d,80)
    # Eight increasing-speed transitions, with readable holds before each movement.
    progress=7.8*p**1.28;index=int(progress);phase=progress-index
    amount=0 if phase<.48 else ((phase-.48)/.52)**2*(3-2*((phase-.48)/.52))
    seq=['kitchen','couple']
    current=feed_card(seq[index%2]);following=feed_card(seq[(index+1)%2])
    strip=Image.new('RGB',(608,1610),'#111817');strip.paste(current,(0,0));strip.paste(following,(0,805))
    phone.paste(strip.crop((0,round(amount*805),608,round(amount*805)+910)),(0,94))
    d=ImageDraw.Draw(phone);share(d,43,1035);label(d,85,1027,'转发',23)
    return widescreen(phone)

def trending(p):
    phone=blank_phone();d=ImageDraw.Draw(phone);label(d,26,30,'热搜',33);bars(d,90)
    label(d,27,184,'1',27,'#bc956d')
    timer='00:47:13';n=62
    label(d,96,153,timer,n);share(d,543,185)
    d.line((24,269,584,269),fill='#3b433c',width=1)
    # Unnamed reposts all show the same unlabelled countdown. No invented topic is added.
    count=2+int(p*5)
    for i in range(count):
        y=317+i*118
        if y>989:break
        d.ellipse((25,y+9,39,y+23),fill='#606963')
        label(d,66,y,timer,37,'#a1a69e');share(d,546,y+14)
        d.line((24,y+87,584,y+87),fill='#29332d',width=1)
    return widescreen(phone)

def last_countdown(p):
    # Remains fixed for the entire approved last shot; nothing explains the timer.
    im=original.native.panel('',1);d=ImageDraw.Draw(im)
    d.text((W/2,450),'00:47:12',font=font(126),fill=COLOR,anchor='mt')
    return im

def frame(s,p):
    sid=s['id']
    if sid=='E6-02':return livestream(p)
    if sid=='E6-05':return global_feed(p)
    if sid=='E6-06':return trending(p)
    if sid=='E6-09':return last_countdown(p)
    if sid=='E6-04':
        pic=ImageOps.fit(cctv_plate(),(1440,1080),method=Image.Resampling.LANCZOS)
        im=Image.new('RGB',(W,H),'black');im.paste(pic,(240,0));return im
    if sid in ['E6-01','E6-03']:
        original.CHOICES.update({'E6-01':2,'E6-03':1})
    return original.frame(s,p,(s['start_frame']+p*(s['end_frame']-s['start_frame']))/FPS)

def check_output(path,count,audio=False,zero=False):
    r=subprocess.run(['ffprobe','-v','error']+(['-count_frames'] if path.suffix=='.mkv' else [])+['-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,check=True)
    probe=json.loads(r.stdout);video=next(s for s in probe['streams'] if s['codec_type']=='video')
    decode=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(path),'-f','null','-'],capture_output=True,text=True)
    assert decode.returncode==0,decode.stderr
    assert int(video.get('nb_frames',video.get('nb_read_frames','0')))==count and video['r_frame_rate']=='24/1'
    assert abs(float(video.get('duration',probe['format']['duration']))-count/FPS)<.004
    report={'path':str(path.relative_to(ROOT)),'sha256':sha(path),'bytes':path.stat().st_size,'expected_frames':count,'probe':probe,'decode_exit':decode.returncode,'decode_errors':decode.stderr,'technical_status':'PASS','creative_status':'WORKPRINT_REVIEW_PENDING'}
    if audio:
        pcm=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-f','s32le','-acodec','pcm_s32le','pipe:1'],capture_output=True,check=True).stdout
        values=np.frombuffer(pcm,dtype='<i4');expected=count*2000*2
        report['decoded_pcm']={'interleaved_samples':len(values),'expected_interleaved_samples':expected,'sample_count_match':len(values)==expected,'absolute_peak':int(np.abs(values.astype(np.int64)).max()) if len(values) else 0,'all_zero':bool(np.all(values==0))}
        lossless=next(s for s in probe['streams'] if s['codec_type']=='audio')['codec_name']=='flac'
        report['decoded_pcm']['codec_padding_interleaved_samples']=len(values)-expected
        assert len(values)==expected if lossless else expected<=len(values)<expected+4096
        if zero:assert np.all(values==0)
    return report

def render_shot(s,revision):
    target=ROOT/'output'/f"{s['id']}_PICTURE_{revision}_1080P.mp4";count=s['end_frame']-s['start_frame']
    if target.exists():return check_output(target,count)
    partial=target.with_name(target.stem+'.partial.mp4')
    if partial.exists():raise FileExistsError('Interrupted evidence exists; use a new revision: '+str(partial))
    filters='null' if s['id'].endswith('CARD') else 'noise=alls=1:allf=t+u,chromashift=cbh=1:crh=-1'
    cmd=['ffmpeg','-nostdin','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','24','-i','pipe:0','-an','-vf',filters,'-c:v','libx264','-crf','19','-preset','veryfast','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(partial)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE);start=time.monotonic()
    try:
        for i in range(count):proc.stdin.write(frame(s,i/max(1,count-1)).tobytes())
    finally:proc.stdin.close()
    assert proc.wait()==0
    with partial.open('rb') as f:os.fsync(f.fileno())
    partial.rename(target);report=check_output(target,count);report['render_seconds']=time.monotonic()-start
    print(s['id'],count,'frames PASS',flush=True);return report

def atomic_ffmpeg(args,target):
    if target.exists():return
    partial=target.with_name(target.stem+'.partial'+target.suffix)
    if partial.exists():raise FileExistsError('Retain interrupted output and use a new revision: '+str(partial))
    subprocess.run(['ffmpeg','-nostdin','-v','error']+args+[str(partial)],check=True)
    with partial.open('rb') as f:os.fsync(f.fileno())
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(partial),'-f','null','-'],check=True)
    partial.rename(target)

def assemble(revision,picture_revision=None):
    picture_revision=picture_revision or revision
    count=sum(LOOKUP[s]['end_frame']-LOOKUP[s]['start_frame'] for s in PART_A)
    concat=ROOT/'output'/f'E6_PART_A_{revision}_concat.txt'
    concat.write_text(''.join("file '"+s+f"_PICTURE_{picture_revision}_1080P.mp4'\n" for s in PART_A))
    output=ROOT/'output'/f'E6_PART_A_WORKPRINT_{revision}_MASTER.mkv'
    mix=SOURCE/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'
    if not output.exists():
        atomic_ffmpeg(['-f','concat','-safe','0','-i',str(concat),'-i',str(mix),'-filter_complex',f'[1:a]atrim=start_sample={14760*2000}:end_sample={15847*2000},asetpts=PTS-STARTPTS[a]','-map','0:v:0','-map','[a]','-c:v','copy','-c:a','flac'],output)
    reports=[check_output(output,count,audio=True)]
    bilingual=ROOT/'output'/f'E6_PART_A_WORKPRINT_{revision}_1080P_BILINGUAL.mp4'
    ass=ROOT/'output'/f'E6_PART_A_{revision}.ass'
    subs=[s for s in original.SUBS if 615<=s['start']<15847/24]
    def clock(t):
        c=round(t*100);return f'{c//360000}:{c//6000%60:02d}:{c//100%60:02d}.{c%100:02d}'
    ass.write_text('[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Noto Sans Mono CJK SC,42,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,45,45,92,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'+''.join(f"Dialogue: 0,{clock(s['start']-615)},{clock(s['end']-615)},Default,,0,0,0,,{s['zh']}\\N{{\\fs28}}{s['en']}\n" for s in subs))
    if not bilingual.exists():
        atomic_ffmpeg(['-i',str(output),'-vf',f"ass={ass}:fontsdir={SOURCE/'graphics/fonts'}",'-c:v','libx264','-preset','veryfast','-crf','19','-threads','4','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart'],bilingual)
    reports.append(check_output(bilingual,count,audio=True))
    clean=ROOT/'output'/f'E6_PART_A_WORKPRINT_{revision}_1080P_CLEAN.mp4'
    atomic_ffmpeg(['-i',str(output),'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart'],clean)
    reports.append(check_output(clean,count,audio=True))
    # E6-09 has an encoded zero-valued AAC track, independently redecoded below.
    zero=ROOT/'output'/f'E6-09_SILENT_WORKPRINT_{revision}_1080P.mp4'
    if not zero.exists():
        atomic_ffmpeg(['-i',str(ROOT/'output'/f'E6-09_PICTURE_{picture_revision}_1080P.mp4'),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-af','atrim=end_sample=226000','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart'],zero)
    reports.append(check_output(zero,113,audio=True,zero=True));return reports

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',default='v1');parser.add_argument('--frames-only',action='store_true');parser.add_argument('--assemble-only',action='store_true');parser.add_argument('--picture-revision');args=parser.parse_args()
    (ROOT/'output').mkdir(exist_ok=True);(ROOT/'qa').mkdir(exist_ok=True)
    for s in ['E6-01','E6-03']:
        for v in [1,2,3]:image(SOURCE/'art/candidates'/f'{s}_v{v}.png').load()
    for p in [ROOT/'assets/E6-04_v3.png']+[ROOT/'assets'/f'E6-05_v{v}.png' for v in [1,2,3]]:image(p).load()
    if args.frames_only:
        for sid in PART_A+['E6-09']:frame(LOOKUP[sid],.60).save(ROOT/'qa'/f'{sid}_frame.png')
        return
    picture_revision=args.picture_revision or args.revision
    reports=[check_output(ROOT/'output'/f'{sid}_PICTURE_{picture_revision}_1080P.mp4',LOOKUP[sid]['end_frame']-LOOKUP[sid]['start_frame']) if args.assemble_only else render_shot(LOOKUP[sid],picture_revision) for sid in PART_A+['E6-09']]
    reports+=assemble(args.revision,picture_revision)
    report={'revision':args.revision,'source_timeline_sha256':sha(SOURCE/'project/full_picture_timeline.json'),'original_direction_sha256':sha(SOURCE/'docs/ORIGINAL_CREATIVE_BRIEF.txt'),'renderer_sha256':sha(Path(__file__)),'part_A_frames':1087,'part_A_duration':1087/24,'missing_E6_shots':['E6-07','E6-08'],'working_mix_reused':str((SOURCE/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac').relative_to(REPO)),'reports':reports,'final_film_completed':False}
    (ROOT/'qa'/f'E6_RENDER_{args.revision}.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
