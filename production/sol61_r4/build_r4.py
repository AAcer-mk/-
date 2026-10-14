#!/usr/bin/env python3
"""E7 native inserts and a narrow F6 video patch; preserve original evidence.

No generated actor motion, lip sync, full E7 sequence, or director approval.
"""
import argparse, functools, hashlib, importlib.util, io, json, math, os, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parent
W,H,FPS=1920,1080,24
SOURCE=None

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def run(args):
    args=list(map(str,args));target=Path(args[-1])
    atomic=target.suffix.lower() in ['.mp4','.mkv','.wav','.jpg']
    if atomic:
        if target.exists():raise FileExistsError(target)
        partial=target.with_name(target.stem+'.pending'+target.suffix);args[-1]=str(partial)
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror']+args,check=True)
    if atomic:
        with partial.open('rb') as f:os.fsync(f.fileno())
        partial.rename(target)

def save_png(im,path):
    # Validate the complete in-memory encoding before exposing the artifact.
    b=io.BytesIO();im.save(b,format='PNG');data=b.getvalue()
    with Image.open(io.BytesIO(data)) as check:check.load()
    temp=path.with_suffix('.tmp')
    with temp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    assert temp.read_bytes()==data
    temp.replace(path)
    with Image.open(path) as check:check.load()

@functools.lru_cache(40)
def font(n):return ImageFont.truetype(str(SOURCE/'graphics/fonts/NotoSansMonoCJKsc-Regular.otf'),n)

def project(layer,size,quad):
    src=[(0,0),(layer.width,0),(layer.width,layer.height),(0,layer.height)]
    mat=[];rhs=[]
    for (x,y),(u,v) in zip(quad,src):
        mat.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);rhs.extend([u,v])
    coeff=np.linalg.solve(np.asarray(mat),np.asarray(rhs))
    return layer.transform(size,Image.Transform.PERSPECTIVE,tuple(coeff),Image.Resampling.BICUBIC)

def zoom(im,p,amount=.025):
    z=1+amount*p;cw,ch=round(im.width/z),round(im.height/z)
    x,y=(im.width-cw)//2,(im.height-ch)//2
    return im.crop((x,y,x+cw,y+ch)).resize(im.size,Image.Resampling.BICUBIC)

@functools.lru_cache(16)
def paper(kind,variant):
    rng=np.random.default_rng(7420+variant)
    base=np.clip(rng.normal(199,1.15,(960,1500,1))+np.asarray([3,0,-9]),0,255).astype('uint8')
    im=Image.fromarray(base);d=ImageDraw.Draw(im)
    d.rectangle((70,80,1430,888),outline=(94,91,82),width=2)
    if kind:
        d.text((120,114),'申请事项',font=font(46),fill=(46,44,39))
        d.text((530,111),kind,font=font(56),fill=(35,35,31))
        d.line((120,225,1380,225),fill=(86,83,74),width=2)
        d.text((120,278),'申请人',font=font(46),fill=(46,44,39))
        # The applicant value is deliberately empty: no names or placeholder.
        d.line((530,351,1350,351),fill=(85,82,73),width=2)
        d.line((120,423,1380,423),fill=(86,83,74),width=2)
    stamp=Image.new('RGBA',(800,270));sd=ImageDraw.Draw(stamp)
    sd.rectangle((19,19,781,251),outline=(137,51,46,230),width=9)
    sd.text((400,117),'已批准',font=font(146),fill=(137,51,46,235),anchor='mm')
    # Small ink gaps are deterministic printed texture, never damaged glyphs.
    a=np.asarray(stamp).copy();dots=rng.random(a.shape[:2])<.009;a[dots,3]=0
    stamp=Image.fromarray(a).rotate([-5,-3,4][variant-1],Image.Resampling.BICUBIC,expand=True)
    im=im.convert('RGBA');im.alpha_composite(stamp,(640-stamp.width//2,570-stamp.height//2))
    return im

@functools.lru_cache(16)
def paper_plate(kind,variant):
    with Image.open(SOURCE/'art/scenes/beijing_restored.png') as src:
        back=ImageOps.fit(src.convert('RGB'),(W,H)).filter(ImageFilter.GaussianBlur(18))
    back=ImageEnhance.Color(back).enhance(.30)
    back=ImageEnhance.Brightness(back).enhance(.40).convert('RGBA')
    quad=[(215,87),(1724,30),(1794,997),(139,1047)]
    dx=[0,-27,31][variant-1];quad=[(x+dx,y) for x,y in quad]
    layer=project(paper(kind,variant),(W,H),quad)
    shadow=Image.new('RGBA',(W,H));shadow.putalpha(layer.getchannel('A'))
    shadow=shadow.filter(ImageFilter.GaussianBlur(21))
    shifted=Image.new('RGBA',(W,H));shifted.alpha_composite(shadow,(16,22))
    back=Image.alpha_composite(back,shifted);back=Image.alpha_composite(back,layer)
    return back.convert('RGB')

@functools.lru_cache(3)
def printer(variant):
    with Image.open(ROOT/'assets'/f'E7-07_printer_v{variant}.png') as src:im=src.convert('RGB')
    quads={1:[(597,306),(1091,318),(1109,419),(598,415)],
           2:[(595,336),(1029,338),(1050,446),(594,444)],
           3:[(677,325),(1123,327),(1140,420),(679,419)]}
    writing=Image.new('RGBA',(1000,230));d=ImageDraw.Draw(writing)
    d.text((500,105),'剩余任务 ∞',font=font(122),fill=(22,30,21,230),anchor='mm')
    layer=project(writing,im.size,quads[variant])
    im=Image.alpha_composite(im.convert('RGBA'),layer).convert('RGB')
    # Original E7 presentation is 16:9. Crop the wide photographic source,
    # keeping the physical LCD, buttons and nearby tray in the frame.
    im=ImageOps.fit(im,(W,H),Image.Resampling.LANCZOS,centering=(.5,.45))
    return ImageEnhance.Color(im).enhance(.30)

def card(native,p,shot):
    im=Image.new('RGB',(W,H));d=ImageDraw.Draw(im)
    key,city,clock,name=shot['model'];native.mark(d,key,84,716,120,'white')
    line=f'{city} · 2028-03-14 {clock} UTC · {name} · STATUS: UNRESPONSIVE'
    d.text((82,903),line[:int(min(1,p/.82)*len(line))],font=font(24),fill='white')
    return im

def encoder(path,frames,iterator,filters='noise=alls=1:allf=t+u,chromashift=cbh=1:crh=-1'):
    if path.exists():raise FileExistsError(path)
    partial=path.with_name(path.stem+'.partial.mp4')
    enc=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-f','rawvideo','-pix_fmt','rgb24',
        '-s',f'{W}x{H}','-r','24','-i','pipe:0','-an','-vf',filters,'-c:v','libx264',
        '-crf','18','-preset','veryfast','-threads','4','-pix_fmt','yuv420p',
        '-video_track_timescale','24000','-frames:v',str(frames),'-movflags','+faststart',str(partial)],stdin=subprocess.PIPE)
    try:
        n=0
        for im in iterator:enc.stdin.write(im.tobytes());n+=1
        assert n==frames,(n,frames)
    finally:enc.stdin.close()
    assert enc.wait()==0
    run(['-i',partial,'-f','null','-'])
    with partial.open('rb') as f:os.fsync(f.fileno())
    partial.rename(path)

def frames(path):
    dec=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(path),'-map','0:v:0',
        '-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
    try:
        while True:
            data=dec.stdout.read(W*H*3)
            if not data:break
            assert len(data)==W*H*3
            yield Image.frombytes('RGB',(W,H),data)
    finally:dec.stdout.close()
    assert dec.wait()==0

def transformed_patch(im,p,is_mask=False):
    im=ImageOps.fit(im,(W,H),Image.Resampling.LANCZOS)
    z=1+.048*p;cw,ch=round(W/z),round(H/z)
    x=round((W-cw)*(.35+.3*p));y=round((H-ch)*.48)
    im=im.crop((x,y,x+cw,y+ch)).resize((W,H),Image.Resampling.BICUBIC)
    if not is_mask:
        im=ImageEnhance.Color(im).enhance(.80)
        im=ImageEnhance.Brightness(im).enhance(.896*(.94 if p*5>=1.6 else 1))
    return im

def contact(files,target,labels):
    c=Image.new('RGB',(960,round(len(files)/2+.49)*305),'#171717');d=ImageDraw.Draw(c)
    for i,f in enumerate(files):
        with Image.open(f) as im:tile=ImageOps.fit(im.convert('RGB'),(480,270))
        x,y=(i%2)*480,(i//2)*305;c.paste(tile,(x,y));d.text((x+10,y+277),labels[i],font=font(16),fill='white')
    c.save(target,quality=94)

def main():
    global SOURCE
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();SOURCE=args.source.resolve();out=args.output.resolve()
    if out.exists():raise FileExistsError('Use a new revision directory; preserve earlier evidence.')
    out.mkdir(parents=True)
    sys.path.insert(0,str(SOURCE/'project'))
    import native_scenes as native
    helper_path=ROOT.parent/'sol61_r2/build_continuation.py'
    spec=importlib.util.spec_from_file_location('r2_helper',helper_path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    timeline=json.loads((SOURCE/'project/full_picture_timeline.json').read_text());lookup={s['id']:s for s in timeline}
    records=json.loads((ROOT/'generation_records.json').read_text())
    for r in records:
        f=ROOT/r['output'];r.update(bytes=f.stat().st_size,sha256=sha(f),dimensions=list(Image.open(f).size))
    (ROOT/'generation_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    candidate_files=[];candidate_labels=[]
    for variant in range(1,4):
        for sid,im in [('E7-04',paper_plate('',variant)),('E7-05',paper_plate('土地征用',variant)),('E7-07',printer(variant))]:
            f=out/f'{sid}_NATIVE_CANDIDATE_v{variant}.png';save_png(im,f)
            candidate_files.append(f);candidate_labels.append(f'{sid} / native candidate {variant}')
    contact(candidate_files,out/'E7_NATIVE_CANDIDATES.jpg',candidate_labels)
    pictures={};jobs={};reports=[]
    montage_cuts=[0,45,90,132,180]
    kinds=['土地征用','药品上市','人员调动','拆除许可']
    for sid in ['E7-CARD','E7-04','E7-05','E7-07']:
        s=lookup[sid];n=s['end_frame']-s['start_frame'];f=out/f'{sid}_PICTURE_r4_1080P.mp4'
        def shot_frames(sid=sid,s=s,n=n):
            for i in range(n):
                u=i/max(1,n-1)
                if sid=='E7-CARD':im=card(native,u,s)
                elif sid=='E7-04':im=zoom(paper_plate('',1),u,.026)
                elif sid=='E7-05':
                    k=next(j for j in range(4) if i<montage_cuts[j+1]);local=(i-montage_cuts[k])/(montage_cuts[k+1]-montage_cuts[k]-1)
                    im=zoom(paper_plate(kinds[k],1),local,.017)
                else:im=zoom(printer(1),u,.015)
                yield im
        encoder(f,n,shot_frames(),filters='null' if sid=='E7-CARD' else 'noise=alls=1:allf=t+u,chromashift=cbh=1:crh=-1')
        pictures[sid]=f;print(sid,n,'frames rendered',flush=True)
    jobs['E7_CARD']=(16920,17016,[pictures['E7-CARD']])
    jobs['E7_APPROVAL_INSERTS']=(17557,17872,[pictures['E7-04'],pictures['E7-05']])
    jobs['E7_PRINTER_LCD']=(18052,18187,[pictures['E7-07']])
    # F6 repair: same decoded original frame and unchanged action everywhere
    # outside the small extra-unit mask. No actor/monitor/command regeneration.
    old=SOURCE/'output/F6_SEQUENCE_REVIEW_v1_1080P_CLEAN.mp4'
    corrected=Image.open(ROOT/'assets/F6-04_extra_unit_removed_v1.png').convert('RGB')
    assert corrected.size==(1670,942)
    mask=Image.new('L',corrected.size);ImageDraw.Draw(mask).rectangle((898,531,955,674),fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(2.0))
    patch_movie=out/'F6_PATCH_COLOR_CAMERA_REFERENCE.mp4'
    encoder(patch_movie,120,(transformed_patch(corrected,i/119) for i in range(120)),filters='vignette=PI/5,chromashift=cbh=1:crh=-1')
    patch_stream=iter(frames(patch_movie));evidence=[]
    def repaired_frames():
        for i,original in enumerate(frames(old)):
            im=original
            if i>=480:
                p=(i-480)/119;replacement=next(patch_stream);m=transformed_patch(mask,p,is_mask=True)
                marray=np.asarray(m);oa=np.asarray(original);ra=np.asarray(replacement)
                # Match the patch exposure using the existing unchanged border.
                border=(marray>1)&(marray<20)
                offsets=np.median(oa[border].astype(float)-ra[border].astype(float),axis=0)
                ra=np.clip(ra.astype(float)+offsets,0,255).astype('uint8')
                im=Image.composite(Image.fromarray(ra),original,m)
                unchanged=np.asarray(im)[marray==0]
                assert np.array_equal(unchanged,oa[marray==0])
                if i in [480,509,518,519,552,599]:
                    original.save(out/f'F6_before_frame{i}.jpg',quality=95)
                    im.save(out/f'F6_after_compositor_frame{i}.jpg',quality=95)
                    evidence.append({'frame':i,'absolute_time':590+i/24,'patch_mask_bbox':m.getbbox(),
                        'outside_mask_rgb_identical_before_encoding':True,'exposure_offset_rgb':offsets.tolist()})
            yield im
    repaired=out/'F6_SEQUENCE_PICTURE_PATCH_r4_1080P.mp4'
    encoder(repaired,600,repaired_frames(),filters='null')
    try:next(patch_stream);raise AssertionError('Extra patch frame')
    except StopIteration:pass
    jobs['F6_SEQUENCE_PATCH']=(14160,14760,[repaired])
    audio_inputs=[]
    for name,(first,last,parts) in jobs.items():
        n=last-first;wav=out/(name+'_source_mix.wav')
        mix=SOURCE/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'
        run(['-i',mix,'-af',f'atrim=start_sample={first*2000}:end_sample={last*2000},asetpts=PTS-STARTPTS','-c:a','pcm_s24le',wav])
        ref=helper.pcm(wav);assert len(ref)==n*2000*8
        ass=out/(name+'_local_bilingual.ass');events=helper.subtitles(SOURCE,first/24,last/24,ass)
        if len(parts)==1:inputs=['-i',parts[0]]
        else:
            concat=out/(name+'_concat.txt');concat.write_text(''.join("file '"+str(f)+"'\n" for f in parts))
            inputs=['-f','concat','-safe','0','-i',concat]
        master=out/(name+'_WORKPRINT_r4_MASTER.mkv')
        run(inputs+['-i',wav,'-map','0:v:0','-map','1:a:0','-vf','setpts=N/(24*TB)','-r','24',
            '-c:v','libx264','-crf','18','-preset','veryfast','-threads','4','-pix_fmt','yuv420p',
            '-frames:v',str(n),'-c:a','flac',master])
        reports.append(helper.validate(master,n,ref))
        for suffix in ['CLEAN','BILINGUAL']:
            f=out/(name+'_WORKPRINT_r4_1080P_'+suffix+'.mp4')
            vf='setpts=N/(24*TB)'
            if suffix=='BILINGUAL':vf+=f',ass={ass.as_posix()}:fontsdir={(SOURCE/"graphics/fonts").as_posix()}'
            run(['-i',master,'-vf',vf,'-r','24','-c:v','libx264','-crf','18','-preset','veryfast','-threads','4',
                '-pix_fmt','yuv420p','-video_track_timescale','24000','-frames:v',str(n),'-c:a','aac','-b:a','192k','-movflags','+faststart',f])
            reports.append(helper.validate(f,n,ref))
        if name.startswith('E7'):audio_inputs.append((name,ref,master,n,first,last))
        print(name,n,'frames; source audio lossless PASS;',len(events),'subtitle events',flush=True)
    # Concatenated review reel explicitly excludes six missing physical shots.
    # This is a review of noncontiguous inserts, NEVER a complete 65s E7 scene.
    concat=out/'E7_INSERT_REEL_concat.txt';concat.write_text(''.join("file '"+str(x[2])+"'\n" for x in audio_inputs))
    reel=out/'E7_NONCONTIGUOUS_INSERT_REEL_r4_MASTER.mkv';n=sum(x[3] for x in audio_inputs)
    run(['-f','concat','-safe','0','-i',concat,'-vf','setpts=N/(24*TB)','-r','24','-c:v','libx264','-crf','18',
         '-preset','veryfast','-threads','4','-pix_fmt','yuv420p','-frames:v',str(n),'-c:a','flac',reel])
    reel_pcm=b''.join(x[1] for x in audio_inputs);reports.append(helper.validate(reel,n,reel_pcm))
    reel_mp4=out/'E7_NONCONTIGUOUS_INSERT_REEL_r4_1080P.mp4'
    run(['-i',reel,'-vf','setpts=N/(24*TB)','-r','24','-c:v','libx264','-crf','18','-preset','veryfast','-threads','4',
         '-pix_fmt','yuv420p','-video_track_timescale','24000','-frames:v',str(n),'-c:a','aac','-b:a','192k','-movflags','+faststart',reel_mp4])
    reports.append(helper.validate(reel_mp4,n,reel_pcm))
    sample_files=[];sample_labels=[]
    for name,times in [('E7_CARD',[3.85]),('E7_APPROVAL_INSERTS',[2.5,6.15,8.15,10.10,12.9]),('E7_PRINTER_LCD',[.3,5.4]),('F6_SEQUENCE_PATCH',[13,19,20,21.58,21.625,23,24.958])]:
        f=out/(name+'_WORKPRINT_r4_1080P_CLEAN.mp4')
        for t in times:
            dst=out/f'{name}_decoded_{t:.3f}.jpg';run(['-ss',t,'-i',f,'-frames:v','1',dst]);sample_files.append(dst);sample_labels.append(f'{name} / {t:.3f}s')
    contact(sample_files,out/'R4_ACTUAL_ENCODED_CONTACT.jpg',sample_labels)
    deps=[Path(__file__),helper_path,SOURCE/'docs/ORIGINAL_CREATIVE_BRIEF.txt',SOURCE/'project/full_picture_timeline.json',
        SOURCE/'project/native_scenes.py',SOURCE/'project/film_compositor.py',SOURCE/'graphics/fonts/NotoSansMonoCJKsc-Regular.otf',
        SOURCE/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac',old,SOURCE/'art/scenes/beijing_restored.png']
    qa={'schema':'silent-protocol-r4-qa','outputs':reports,'E7_new_unique_frames':546,'E7_new_unique_seconds':22.75,
        'E7_present_shots':['E7-CARD','E7-04','E7-05','E7-07'],'E7_missing_physical_shots':['E7-01','E7-02','E7-03','E7-06','E7-08','E7-09'],
        'E7_full_timeline_frames':1560,'E7_remaining_frames':1014,'E7_complete':False,
        'E7_review_reel':'NONCONTIGUOUS_INSERTS_ONLY; each independent master retains original timeline/audio',
        'E7_applicant_fields':'All four empty; no names, IDs, invented fill or placeholder',
        'E7_montage_cuts_frames':montage_cuts,'F6_patch':{'original_source_has_ten_units':True,'final_count_expected':9,
            'first_four_down_before_pull':True,'first_five_down_after_pull':True,'four_right_units_up_after_pull':True,
            'original_600_frames_and_audio_range_retained':True,'mask_source_rectangle':[898,531,955,674],
            'pre_encode_identity_evidence':evidence,'actual_encoded_creative_QA':'PENDING VISUAL READBACK'},
        'generation':'image_gen for four photographic stills; Pillow/numpy/ffmpeg native graphics and video composition',
        'input_fingerprints':[{'path':str(x),'sha256':sha(x)} for x in deps],
        'director_changes':[],'final_acting_or_voice_acceptance':False,'final_film_completed':False}
    (out/'R4_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    print('R4 ENCODING PASS; actual encoded visual review still required',flush=True)

if __name__=='__main__':main()
