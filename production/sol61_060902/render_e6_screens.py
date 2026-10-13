#!/usr/bin/env python3
"""E6 screen-shot derivatives, pinned to recovered B10 frame boundaries.

No recovered file is changed. E6-02 uses the actual reviewed ceiling-camera
plate, never a character contact sheet. A later moving CCTV insert can replace
the still plate through --live-video without redesigning this interface.
"""
import argparse, hashlib, json, math, subprocess
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
W, H, FPS = 1920, 1080, 24
CAPTION = '这哥们凌晨三点还不睡，猜猜他在看什么 😂'
SHOT_IDS = ('E6-02', 'E6-06', 'E6-09')

def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def run(args, **kw):
    return subprocess.run(args, check=True, **kw)

class Screens:
    def __init__(self, source, live_video=None):
        self.source = Path(source)
        self.font_path = self.source/'graphics/fonts/NotoSansMonoCJKsc-Regular.otf'
        self.emoji_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        self.plate_path = self.source/'art/candidates/E6-04_v2.png'
        with Image.open(self.plate_path) as im:
            im.load()
            self.plate = ImageEnhance.Color(im.convert('RGB')).enhance(.50)
        self.live_video = live_video
        self.live_frames = None
        if live_video:
            raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error',
                '-xerror', '-i', str(live_video), '-vf', 'fps=24,scale=720:540',
                '-t', '7.5', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'])
            a = np.frombuffer(raw, np.uint8)
            self.live_frames = a.reshape(-1, 540, 720, 3)
            if len(self.live_frames) < 180:
                raise ValueError('Moving CCTV insert must cover all 180 frames')

    @lru_cache(40)
    def font(self, n):
        return ImageFont.truetype(str(self.font_path), n)

    def text(self, d, xy, text, n, fill='#d8ddd8', anchor=None):
        d.text(xy, text, font=self.font(n), fill=fill, anchor=anchor)

    def portrait(self, frame):
        im = Image.new('RGB', (720,1280), '#0e1312')
        d = ImageDraw.Draw(im)
        self.text(d, (36,32), '直播', 30)
        d.ellipse((633,39,645,51),fill='#b7bcb5')
        self.text(d, (658,33), '•••', 19)
        d.line((24,96,696,96),fill='#39413c',width=1)
        if self.live_frames is not None:
            plate = Image.fromarray(self.live_frames[frame])
        else:
            plate = ImageOps.fit(self.plate,(720,540),Image.Resampling.LANCZOS)
            # Display refresh variation only; this is not claimed as actor motion.
            plate = ImageEnhance.Brightness(plate).enhance(1+.008*math.sin(frame*.081))
        # Surveillance frame remains 4:3 within the 9:16 phone recording.
        im.paste(plate,(0,124))
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((25,147,142,188),radius=7,fill='#18221dc9')
        d.ellipse((38,161,49,172),fill='#d1d7ca')
        self.text(d,(60,154),'LIVE',21)
        self.text(d,(36,726),'这哥们凌晨三点还不睡，',35)
        self.text(d,(36,778),'猜猜他在看什么',35)
        emoji=ImageFont.truetype(str(self.emoji_path),37)
        d.text((319,779),'😂',font=emoji,fill='#d7d9c0')
        d.line((36,887,684,887),fill='#39413c',width=1)
        self.text(d,(36,922),'直播中',24,'#89958e')
        self.text(d,(555,923),'转发',24,'#acb8ad')
        d.rounded_rectangle((28,1129,692,1200),radius=22,fill='#202923')
        self.text(d,(54,1146),'说点什么…',25,'#9ba59d')
        d.rounded_rectangle((265,1242,455,1247),radius=2,fill='#aeb5af')
        return im

    def frame(self, shot, index, count):
        if shot=='E6-02':
            im=Image.new('RGB',(W,H),'black')
            # 608/1080 is the nearest even-pixel approximation to 9:16.
            im.paste(self.portrait(index).resize((608,H),Image.Resampling.LANCZOS),(656,0))
            return im
        im=Image.new('RGB',(W,H),'#101311')
        d=ImageDraw.Draw(im)
        if shot=='E6-06':
            # Ranked countdown: the #1 entry deliberately has no title/explanation.
            self.text(d,(224,127),'热搜',45,'#b9c2b8')
            self.text(d,(1700,149),'↗',35,'#acb8ab',anchor='rt')
            d.line((220,221,1700,221),fill='#53614f',width=2)
            self.text(d,(225,331),'1',66,'#bcb69c')
            self.text(d,(1009,398),'00:47:13',125,anchor='mt')
            d.line((341,596,1688,596),fill='#414d40',width=1)
            # Reposts appear without inventing other trending stories or explanations.
            n=min(3,1+index//60)
            for k in range(n):
                y=682+k*74
                self.text(d,(377,y),'↗',30,'#82937d')
                self.text(d,(447,y),'00:47:13',29,'#93a08d')
                self.text(d,(1550,y),'转发',26,'#7e8d7c',anchor='rt')
        else:
            # Match the previous counter typography; no ticking, fade, explanation,
            # grain movement or audio on this last hold. The one-second change is
            # intentionally across the two separated shots, not a real-time clock.
            self.text(d,(W/2,450),'00:47:12',126,anchor='mt')
        return im

def render(source, output, live_video=None):
    source,output=Path(source),Path(output)
    output.mkdir(parents=True,exist_ok=True)
    timeline=json.loads((source/'project/full_picture_timeline.json').read_text())
    shots={s['id']:s for s in timeline}
    screen=Screens(source,live_video)
    records=[]
    for shot in SHOT_IDS:
        s=shots[shot]; count=s['end_frame']-s['start_frame']
        target=output/f'{shot}_picture_sol61_060902_v1_1080p.mp4'
        if target.exists(): raise FileExistsError(target)
        partial=target.with_suffix('.partial.mp4')
        if partial.exists(): raise FileExistsError(partial)
        cmd=['ffmpeg','-nostdin','-v','error','-f','rawvideo','-pix_fmt','rgb24',
            '-s','1920x1080','-r','24','-i','pipe:0','-an','-c:v','libx264',
            '-crf','18','-preset','fast','-threads','3','-pix_fmt','yuv420p',
            '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',
            '-movflags','+faststart',str(partial)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for i in range(count):
                f=screen.frame(shot,i,count)
                proc.stdin.write(f.tobytes())
                if i in (0,count//2,count-1):
                    f.save(output/f'{shot}_source_frame_{i:04d}.png')
        finally: proc.stdin.close()
        if proc.wait(): raise RuntimeError('Encoder failed')
        partial.rename(target)
        decode=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',
            str(target),'-f','null','-'],capture_output=True,text=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error',
            '-show_streams','-show_format','-of','json',str(target)]))
        v=probe['streams'][0]
        assert decode.returncode==0,decode.stderr
        assert int(v['nb_frames'])==count and v['avg_frame_rate']=='24/1'
        assert abs(float(v['duration'])-count/FPS)<.000001
        if shot=='E6-09':
            silent=output/f'{shot}_silent_sol61_060902_v1_1080p.mp4'
            if silent.exists():raise FileExistsError(silent)
            # Lossless 48 kHz stereo: exact silence including container decoding.
            run(['ffmpeg','-nostdin','-v','error','-i',str(target),'-f','lavfi',
                '-i','anullsrc=r=48000:cl=stereo','-t',str(count/FPS),
                '-map','0:v','-map','1:a','-c:v','copy','-c:a','flac',
                '-strict','-2','-movflags','+faststart',str(silent)])
            raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-xerror',
                '-i',str(silent),'-map','0:a','-f','s32le','pipe:1'])
            samples=np.frombuffer(raw,dtype='<i4').reshape(-1,2)
            assert len(samples)==round(count/FPS*48000)
            assert np.count_nonzero(samples)==0
            silence={'path':str(silent.name),'sha256':digest(silent),
                'sample_rate':48000,'stereo_sample_frames':len(samples),
                'nonzero_samples':0,'codec':'flac','decoded_exact_silence':True}
        else: silence=None
        records.append({'shot':shot,'picture':target.name,'sha256':digest(target),
            'bytes':target.stat().st_size,'start_frame':s['start_frame'],
            'end_frame':s['end_frame'],'frames':count,'duration':count/FPS,
            'full_decode_exit':decode.returncode,'probe':probe,'silence':silence,
            'status':'PICTURE_WORKPRINT_AUDIO_PENDING' if shot!='E6-09'
                else 'SILENT_SHOT_TECHNICALLY_VERIFIED',
            'creative_review':'PENDING_DECODED_FRAME_REVIEW',
            'live_insert':'moving_video' if live_video else 'reviewed_static_CCTV_plate',
            'plate_sha256':digest(screen.plate_path) if shot=='E6-02' else None})
        print(shot,'encoded',count,'frames',flush=True)
    report={'schema':'silent-protocol-e6-screens-sol61-v1',
        'not_final_film':True,'original_timeline_sha256':digest(source/'project/full_picture_timeline.json'),
        'caption_verbatim':CAPTION,'shots':records,
        'font_sha256':digest(screen.font_path),
        'limitations':['E6-02 needs final moving CCTV insert and canned laughter',
            'E6-06 dialogue/mix and bilingual subtitles remain to be conformed',
            'No E6-07 action or E6-08 replay is manufactured by this renderer']}
    (output/'E6_screen_encoding.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True)
    p.add_argument('--output',required=True);p.add_argument('--live-video')
    a=p.parse_args();render(a.source,a.output,a.live_video)
