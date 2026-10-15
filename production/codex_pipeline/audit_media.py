#!/usr/bin/env python3
"""Decode media, inspect temporal motion, and retain reproducible review evidence.

Optical-flow residuals are diagnostic signals, never actor-animation acceptance.
Film grain, subtitles and morphing can all produce residuals.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw


def probe(path):
    proc=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True)
    if proc.returncode:
        return {'path':str(path),'probe':'FAIL','error':proc.stderr.decode(errors='replace')[-1200:]}
    return {'path':str(path),'probe':'PASS',**json.loads(proc.stdout)}


def motion(path):
    raw=subprocess.run(['ffmpeg','-v','error','-threads','1','-i',str(path),'-vf','fps=2,scale=480:270','-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True)
    if raw.returncode or len(raw.stdout)<2*480*270*3:
        return {'status':'NOT_ENOUGH_DECODED_FRAMES'}
    frames=np.frombuffer(raw.stdout,dtype=np.uint8).reshape(-1,270,480,3)
    stats=[]
    # Analyse active central image, excluding typical subtitles/letterbox.
    gray=[cv2.cvtColor(f,cv2.COLOR_RGB2GRAY)[40:225,30:450] for f in frames]
    for a,b in zip(gray,gray[1:]):
        features=cv2.goodFeaturesToTrack(a,300,.01,7)
        affine=None;inliers=0
        if features is not None and len(features)>8:
            tracked,ok,_=cv2.calcOpticalFlowPyrLK(a,b,features,None)
            mask=ok.ravel().astype(bool)
            if mask.sum()>8:
                affine,valid=cv2.estimateAffinePartial2D(features[mask],tracked[mask],method=cv2.RANSAC,ransacReprojThreshold=1.5)
                inliers=float(valid.mean()) if valid is not None else 0
        aligned=cv2.warpAffine(a,affine,(a.shape[1],a.shape[0])) if affine is not None else a
        flow=cv2.calcOpticalFlowFarneback(aligned,b,None,.5,3,15,3,5,1.2,0)
        mags=np.linalg.norm(flow[8:-8,8:-8],axis=2)
        stats.append({'raw_MAE':float(np.abs(a.astype(float)-b).mean()),
                      'affine_inlier_fraction':inliers,'residual_median_px':float(np.median(mags)),
                      'residual_over_0_7_px_fraction':float((mags>.7).mean())})
    result={'status':'MEASURED_NOT_CREATIVE_ACCEPTANCE','sampled_frames':len(frames),
            'pairs':len(stats),'raw_MAE_mean':float(np.mean([s['raw_MAE'] for s in stats])),
            'residual_motion_fraction_mean':float(np.mean([s['residual_over_0_7_px_fraction'] for s in stats])),
            'global_affine_explained_fraction_mean':float(np.mean([s['affine_inlier_fraction'] for s in stats])),
            'pairs_detail':stats}
    result['warning']='Low residual suggests static/whole-image motion; high residual can be UI, noise, cuts or morphs. Inspect actual frames.'
    return result


def check(path,out,decode=True):
    row=probe(path)
    row['bytes']=path.stat().st_size
    with path.open('rb') as f:row['sha256']=hashlib.file_digest(f,'sha256').hexdigest()
    if row['probe']!='PASS':return row
    streams=row.get('streams',[]);video=any(s['codec_type']=='video' for s in streams)
    if decode:
        proc=subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(path),'-f','null','-'],capture_output=True)
        row['full_decode']='PASS' if proc.returncode==0 else 'FAIL'
        if proc.stderr:row['decode_messages']=proc.stderr.decode(errors='replace')[-2000:]
    if video:
        row['motion']=motion(path)
        dur=float(row.get('format',{}).get('duration',0));tiles=[]
        for t in np.linspace(0,max(0,dur-.1),8):
            raw=subprocess.run(['ffmpeg','-v','error','-threads','1','-ss',str(t),'-i',str(path),'-frames:v','1','-vf','scale=320:180','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True)
            if len(raw.stdout)==320*180*3:
                im=Image.frombytes('RGB',(320,180),raw.stdout);ImageDraw.Draw(im).text((4,4),f'{t:.3f}s',fill='white',stroke_width=1,stroke_fill='black');tiles.append(im)
        if tiles:
            canvas=Image.new('RGB',(1280,360));
            for i,im in enumerate(tiles):canvas.paste(im,((i%4)*320,(i//4)*180))
            name=row['sha256'][:16]+'.jpg';canvas.save(out/name,quality=88);row['contact_sheet']=name
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('roots',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,default=2);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    paths=sorted({p for root in args.roots for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ['.mp4','.mkv','.m4a','.flac','.wav']})
    images=[]
    for root in args.roots:
        for path in root.rglob('*'):
            if path.suffix.lower() not in ['.png','.jpg','.jpeg']:continue
            try:
                with Image.open(path) as im:im.load();images.append({'path':str(path),'decode':'PASS','size':list(im.size)})
            except Exception as e:images.append({'path':str(path),'decode':'FAIL','error':str(e)})
    (args.output/'images.json').write_text(json.dumps(images,indent=2))
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(check,path,args.output):path for path in paths}
        for f in concurrent.futures.as_completed(futures):
            row=f.result();rows.append(row)
            (args.output/'media.json').write_text(json.dumps(sorted(rows,key=lambda x:x['path']),indent=2))
            print(len(rows),'/',len(paths),row['path'],row.get('full_decode',row['probe']),flush=True)


if __name__=='__main__':main()
