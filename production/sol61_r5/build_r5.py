#!/usr/bin/env python3
"""Authored E7 light switch/radio workprints; paper holds remain references.

No actor pickup/walk animation, new voice synthesis or director approval.
"""
import argparse,hashlib,importlib.util,json,math,subprocess,wave
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageEnhance,ImageFilter,ImageOps
ROOT=Path(__file__).resolve().parent
W,H,FPS=1920,1080,24

def loadmod(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def source(name,size=None):
    with Image.open(ROOT/'assets'/name) as im:im.load();im=im.convert('RGB')
    if size:
        assert max(abs(a-b) for a,b in zip(im.size,size))<=1,(name,im.size,size)
        if im.size!=size:im=im.resize(size,Image.Resampling.LANCZOS)
    return im

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--inherited',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();original=a.source.resolve();old=a.inherited.resolve();out=a.output.resolve()
    if out.exists():raise FileExistsError('Use a new revision directory; preserve prior evidence.')
    out.mkdir(parents=True)
    h=loadmod('r4_helpers',ROOT.parent/'sol61_r4/build_r4.py');h.SOURCE=original
    check=loadmod('r2_checks',ROOT.parent/'sol61_r2/build_continuation.py')
    timeline=json.loads((original/'project/full_picture_timeline.json').read_text());lookup={x['id']:x for x in timeline}
    records=json.loads((ROOT/'generation_records.json').read_text())
    for r in records:
        f=ROOT/r['output'];r.update(bytes=f.stat().st_size,sha256=h.sha(f),dimensions=list(Image.open(f).size))
    (ROOT/'generation_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))

    # Locked unlit source is the entire frame. Transfer only positive light
    # contribution in reviewed facade and plaza support; no whole-scene morph.
    unlit=source('E7-01_v2_UNLIT.png');lit=source('E7-01_v1_LIT.png',unlit.size)
    w,hh=unlit.size;off=np.asarray(unlit);on=np.asarray(lit)
    support=Image.new('L',(w,hh));d=ImageDraw.Draw(support)
    d.polygon([(360,94),(1441,281),(1434,769),(338,765)],fill=255)
    d.polygon([(174,235),(365,87),(348,768),(149,768)],fill=255)
    d.polygon([(307,773),(1386,773),(1430,931),(228,931)],fill=255)
    yoff=np.asarray(unlit.convert('L')).astype(float);yon=np.asarray(lit.convert('L')).astype(float)
    contribution=np.clip((yon-yoff-4)/10,0,1)*np.asarray(support)/255
    mask=Image.fromarray((contribution*255).astype('uint8')).filter(ImageFilter.GaussianBlur(.65))
    light=Image.composite(lit,unlit,mask)
    mask.save(out/'E7-01_LIGHT_TRANSFER_MASK.png')
    assert np.array_equal(np.asarray(light)[np.asarray(mask)==0],off[np.asarray(mask)==0])
    # First sharp energy transient in inherited E7-01 mix is at local ~.20s.
    # One global state change at frame5, .208333s. No sequential floor cascade.
    switch_frame=5
    def building_frames():
        for i in range(180):
            im=unlit if i<switch_frame else light
            im=ImageEnhance.Color(im).enhance(.30)
            yield ImageOps.fit(im,(W,H),Image.Resampling.LANCZOS)
    building=out/'E7-01_PICTURE_r5_1080P.mp4'
    h.encoder(building,180,building_frames())

    radio=source('E7-09_v1.png');receiving=source('E7-09_v3_RECEIVING.png',radio.size)
    led=Image.new('L',radio.size);ImageDraw.Draw(led).ellipse((746,374,764,392),fill=255)
    led=led.filter(ImageFilter.GaussianBlur(1.8))
    active=Image.composite(receiving,radio,led)
    receive_start=.55;receive_end=3.95
    def radio_frames():
        for i in range(113):
            im=active if receive_start<=i/FPS<receive_end else radio
            im=ImageEnhance.Color(im).enhance(.30)
            yield ImageOps.fit(im,(W,H),Image.Resampling.LANCZOS)
    radio_movie=out/'E7-09_PICTURE_r5_1080P.mp4';h.encoder(radio_movie,113,radio_frames())

    # Standing shot: actor and architecture are locked source pixels. DIS
    # reconstructs movement ONLY within four reviewed paper outlet masks.
    motionlib=loadmod('r3_motion',ROOT.parent/'sol61_r3/build_f7.py')
    import sys
    sys.path.insert(0,str(original/'project'))
    import native_scenes as native
    sea=source('E7-08_v1.png',(1670,942));end=source('E7-08_v2.png',sea.size)
    motion=motionlib.Motion(sea,end,[(0,0),(1670,0),(1670,942),(0,942)])
    paper_polygons=[[(73,468),(210,469),(325,700),(300,762),(115,755),(85,544)],
        [(1417,492),(1580,484),(1570,574),(1478,757),(1348,759),(1384,666)],
        [(638,424),(673,420),(699,497),(681,520),(641,503)],
        [(1060,424),(1114,422),(1110,487),(1070,524),(1054,499)]]
    paper_mask=Image.new('L',sea.size)
    for polygon in paper_polygons:ImageDraw.Draw(paper_mask).polygon(polygon,fill=255)
    paper_mask=paper_mask.filter(ImageFilter.GaussianBlur(1.8));motion.mask=np.asarray(paper_mask,dtype=np.float32)[:,:,None]/255
    glyph=Image.new('RGBA',(400,400));native.mark(ImageDraw.Draw(glyph),'glm',48,48,304)
    glyph_quad=[(1380,130),(1411,120),(1411,162),(1378,174)]
    ink=h.project(glyph,sea.size,glyph_quad)
    def sea_frames():
        for i in range(180):
            u=i/179;im=motion.frame(u*.95)
            assert np.array_equal(np.asarray(im)[np.asarray(paper_mask)==0],np.asarray(sea)[np.asarray(paper_mask)==0])
            im=Image.alpha_composite(im.convert('RGBA'),ink).convert('RGB')
            im=h.zoom(im,1-u,.048)
            im=ImageEnhance.Color(im).enhance(.30)
            yield ImageOps.fit(im,(W,H),Image.Resampling.LANCZOS)
    sea_movie=out/'E7-08_PICTURE_r5_1080P.mp4';h.encoder(sea_movie,180,sea_frames())
    paper_mask.save(out/'E7-08_PAPER_MOTION_MASK.png')

    # Typography previews of a POST-pick hold, never a finished 180f action shot.
    paperfiles=[]
    for v in range(1,4):
        im=source(f'E7-06_v{v}.png',(1670,942));layer=Image.new('RGBA',(900,1200));draw=ImageDraw.Draw(layer)
        draw.text((100,140),'申请事项',font=h.font(67),fill=(39,38,32,230))
        draw.rectangle((100,255,805,390),fill=(17,17,17,255))
        draw.text((100,540),'批准意见',font=h.font(67),fill=(39,38,32,230))
        draw.text((100,688),'同意。',font=h.font(92),fill=(31,30,25,245))
        draw.text((100,831),'立即执行。',font=h.font(92),fill=(31,30,25,245))
        quad=[(862,212),(1325,285),(1181,862),(686,741)]
        ink=h.project(layer,im.size,quad);preview=Image.alpha_composite(im.convert('RGBA'),ink).convert('RGB')
        preview=ImageEnhance.Color(preview).enhance(.30);f=out/f'E7-06_TYPED_HOLD_REFERENCE_v{v}.jpg';preview.save(f,quality=95,subsampling=0);paperfiles.append(f)
    h.contact(paperfiles,out/'E7-06_TYPED_REFERENCE_CONTACT.jpg',[f'E7-06 v{v}: POST-PICK REFERENCE ONLY' for v in range(1,4)])
    previews=[];labels=[]
    for r in records:
        previews.append(ROOT/r['output']);labels.append(r['shot']+' / source'+str(r['variant']))
    h.contact(previews,out/'R5_SOURCE_CONTACT.jpg',labels)

    jobs={'E7-01':(17016,17196,building),'E7-08':(18187,18367,sea_movie),'E7-09':(18367,18480,radio_movie)}
    mix=original/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'
    reports=[];masters={};original_pcm={}
    for name,(first,last,picture) in jobs.items():
        n=last-first;wav=out/(name+'_source_mix.wav')
        h.run(['-i',mix,'-af',f'atrim=start_sample={first*2000}:end_sample={last*2000},asetpts=PTS-STARTPTS','-c:a','pcm_s24le',wav])
        ref=check.pcm(wav);assert len(ref)==n*2000*8;original_pcm[name]=ref
        ass=out/(name+'_local_bilingual.ass');events=check.subtitles(original,first/24,last/24,ass)
        master=out/(name+'_WORKPRINT_r5_MASTER.mkv')
        h.run(['-i',picture,'-i',wav,'-map','0:v:0','-map','1:a:0','-vf','setpts=N/(24*TB)','-r','24',
            '-c:v','libx264','-crf','18','-preset','veryfast','-threads','4','-pix_fmt','yuv420p','-frames:v',n,'-c:a','flac',master])
        reports.append(check.validate(master,n,ref));masters[name]=master
        for suffix in ['CLEAN','BILINGUAL']:
            f=out/(name+'_WORKPRINT_r5_1080P_'+suffix+'.mp4');vf='setpts=N/(24*TB)'
            if suffix=='BILINGUAL':vf+=f',ass={ass.as_posix()}:fontsdir={(original/"graphics/fonts").as_posix()}'
            h.run(['-i',master,'-vf',vf,'-r','24','-c:v','libx264','-crf','18','-preset','veryfast','-threads','4',
                '-pix_fmt','yuv420p','-video_track_timescale','24000','-frames:v',n,'-c:a','aac','-b:a','192k','-movflags','+faststart',f])
            reports.append(check.validate(f,n,ref))
        print(name,n,'frames; original PCM PASS; subtitle events',len(events),flush=True)

    parts=[('E7-CARD',old/'E7_CARD_WORKPRINT_r4_MASTER.mkv',16920,17016),
        ('E7-01',masters['E7-01'],17016,17196),
        ('E7-04/05',old/'E7_APPROVAL_INSERTS_WORKPRINT_r4_MASTER.mkv',17557,17872),
        ('E7-07',old/'E7_PRINTER_LCD_WORKPRINT_r4_MASTER.mkv',18052,18187),
        ('E7-08',masters['E7-08'],18187,18367),
        ('E7-09',masters['E7-09'],18367,18480)]
    concat=out/'E7_SEVEN_SHOT_REEL_concat.txt';concat.write_text(''.join("file '"+str(f)+"'\n" for _,f,_,_ in parts))
    n=sum(last-first for _,_,first,last in parts);assert n==1019
    ref=b''.join(check.pcm(f) for _,f,_,_ in parts);assert len(ref)==n*2000*8
    wav=out/'E7_SEVEN_SHOT_REEL_source_pcm.wav'
    with wave.open(str(wav),'wb') as wavefile:wavefile.setnchannels(2);wavefile.setsampwidth(4);wavefile.setframerate(48000);wavefile.writeframes(ref)
    master=out/'E7_SEVEN_SHOT_NONCONTIGUOUS_REEL_r5_MASTER.mkv'
    h.run(['-f','concat','-safe','0','-i',concat,'-i',wav,'-map','0:v:0','-map','1:a:0','-vf','setpts=N/(24*TB)','-r','24',
        '-c:v','libx264','-crf','18','-preset','veryfast','-threads','4','-pix_fmt','yuv420p','-frames:v',n,'-c:a','flac',master])
    reports.append(check.validate(master,n,ref))
    # Each range's subtitle offsets are based on reel frame positions. We
    # explicitly retain discontinuities in the range table, not the film clock.
    lines=[];header=None;cursor=0;ranges=[]
    for sid,f,first,last in parts:
        ass=out/(sid.replace('/','_')+'_reel_source_subtitles.ass');events=check.subtitles(original,first/24,last/24,ass)
        header=header or ass.read_text().split('Dialogue:',1)[0]
        for event in events:
            fields=event.split(',',9)
            def sec(s):
                h0,m0,t0=s.split(':');return int(h0)*3600+int(m0)*60+float(t0)
            fields[1]=check.clock(sec(fields[1])+cursor/24);fields[2]=check.clock(sec(fields[2])+cursor/24);lines.append(','.join(fields))
        ranges.append({'id':sid,'original_frame_range':[first,last],'reel_frame_range':[cursor,cursor+last-first]});cursor+=last-first
    ass=out/'E7_SEVEN_SHOT_REEL_bilingual.ass';ass.write_text(header+'\n'.join(lines)+'\n')
    final=out/'E7_SEVEN_SHOT_NONCONTIGUOUS_REEL_r5_1080P_BILINGUAL.mp4'
    h.run(['-i',master,'-vf',f'setpts=N/(24*TB),ass={ass.as_posix()}:fontsdir={(original/"graphics/fonts").as_posix()}',
        '-r','24','-c:v','libx264','-crf','18','-preset','veryfast','-threads','4','-pix_fmt','yuv420p',
        '-video_track_timescale','24000','-frames:v',n,'-c:a','aac','-b:a','192k','-movflags','+faststart',final])
    reports.append(check.validate(final,n,ref))
    samplefiles=[];samplelabels=[]
    for name,indices in [('E7-01',[0,4,5,15,179]),('E7-08',[0,45,90,135,179]),('E7-09',[0,12,24,60,100,112])]:
        f=out/(name+'_WORKPRINT_r5_1080P_BILINGUAL.mp4')
        for i in indices:
            dst=out/f'{name}_decoded_frame{i:03d}.jpg'
            h.run(['-i',f,'-vf',f'select=eq(n\\,{i})','-frames:v',1,dst]);samplefiles.append(dst);samplelabels.append(f'{name} / frame{i}')
    h.contact(samplefiles,out/'R5_ACTUAL_ENCODED_CONTACT.jpg',samplelabels)
    before=np.asarray(Image.open(out/'E7-01_decoded_frame004.jpg').convert('L'))
    after=np.asarray(Image.open(out/'E7-01_decoded_frame005.jpg').convert('L'))
    rois=[(368,115,436,178),(368,204,436,272),(368,295,436,360),(368,386,436,451),
          (368,477,436,549),(368,611,436,683),(368,687,436,752)]
    measures=[]
    for i,box in enumerate(rois):
        x0,y0,x1,y1=[round(z*k) for z,k in zip(box,[W/w,H/hh,W/w,H/hh])]
        pre=float(before[y0:y1,x0:x1].mean());post=float(after[y0:y1,x0:x1].mean())
        assert post-pre>8,(i,pre,post)
        measures.append({'floor_from_top':i+1,'source_ROI':box,'encoded_mean_luma_before':pre,'after':post,'delta':post-pre,'switch_frame':5})
    deps=[Path(__file__),ROOT.parent/'sol61_r4/build_r4.py',ROOT.parent/'sol61_r2/build_continuation.py',
          original/'docs/ORIGINAL_CREATIVE_BRIEF.txt',original/'project/full_picture_timeline.json',mix,
          original/'graphics/fonts/NotoSansMonoCJKsc-Regular.otf']+[f for _,f,_,_ in parts]
    qa={'schema':'silent-protocol-r5-qa','outputs':reports,'new_unique_picture_frames':473,'new_unique_picture_seconds':473/24,
        'E7_present_shots':['E7-CARD','E7-01','E7-04','E7-05','E7-07','E7-08','E7-09'],'E7_workprint_frames':1019,
        'E7_workprint_seconds':1019/24,'E7_missing_picture_frames':541,'E7_complete':False,
        'E7_missing_physical_shots':['E7-02','E7-03','E7-06'],'reel_ranges':ranges,
        'E7-08':{'frames':180,'paper_only_local_DIS_motion':True,'AI_actor_video_generated':False,'actor_and_background_locked_outside_paper_masks':True,
            'paper_polygons':paper_polygons,'GLM_glyph_quad':glyph_quad,'camera':'4.8percent slow pullback, original wide shot',
            'audio_status':'Inherited working mix; heartbeat-stop sound design needs formal final review'},
        'E7-01':{'switch_frame':5,'relative_switch_seconds':5/24,'absolute_switch_seconds':709+5/24,
            'source_first_energy_transient_seconds':.20,'sync_offset_seconds':5/24-.20,'floor_encoded_luma_checks':measures,
            'all_floors_one_state_change':True,'outside_lighting_mask_pre_encode_RGB_unchanged':True,
            'audio_status':'Inherited working mix, sample-exact; repeated ~1s percussive bed observed; single-stamp/M7 separation still needs final sound review'},
        'E7-09':{'original_voice_line':'韩师傅，您的退休申请也已批准。','voice_interval_absolute_seconds':[765.94,769.19],
            'receive_LED_interval_relative_seconds':[.55,3.95],'new_voice_generated':False,'formal_voice_acceptance':False},
        'E7-06':{'new_source_references':3,'selected':1,'typed_post_pick_hold_previews_only':True,'actual_picking_action_generated':False,
            'paper_native_quad':[[862,212],[1325,285],[1181,862],[686,741]],'visible_reply':'同意。立即执行。','request_value':'opaque black rectangle; no generated hidden text'},
        'actual_encoded_visual_review':'PENDING','generation':'built-in image_gen source stills; local Pillow/numpy/ffmpeg video composition',
        'input_fingerprints':[{'path':str(x),'sha256':h.sha(x)} for x in deps],
        'director_changes':[],'formal_actor_and_voice_acceptance':False,'final_film_completed':False}
    (out/'R5_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    print('R5 TECHNICAL PASS:',n,'reelframes; new473; original audio retained; seven floors change atframe5.',flush=True)

if __name__=='__main__':main()
