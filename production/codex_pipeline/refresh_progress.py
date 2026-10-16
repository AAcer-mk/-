#!/usr/bin/env python3
"""Reconcile actual portable deliveries and live frame locks with the ledger.

Never awards creative acceptance. Existing deliveries are immutable; a changed
variant needs a different delivery directory. Historical source rows are kept.
"""
import argparse
import collections
import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def verified_delivery(folder):
    manifest=folder/'DELIVERY.json'
    if not manifest.exists():return None
    data=json.loads(manifest.read_text())
    for entry in data['all_files']:
        file=folder/entry['path']
        if not file.resolve().is_relative_to(folder.resolve()):raise ValueError('Unsafe delivery path')
        if not file.is_file() or file.stat().st_size!=entry['bytes'] or sha(file)!=entry['sha256']:
            raise ValueError('Delivery content differs: '+str(file))
    shot=data['shot'];cfg=data['configuration']
    conform=json.loads((folder/(shot+'_AUDIO_CONFORM.json')).read_text())
    label='2D' if cfg['mode']=='native_card' else '3D'
    playback=json.loads((folder/(shot+'_'+label+'_REVIEW.mp4.playback.json')).read_text())
    if conform['full_decode']!='PASS' or not conform['lossless_PCM_exact']:raise ValueError('Audio conform incomplete')
    if not playback['ended'] or playback['error'] or playback['decodedFrames']!=cfg['frames']:raise ValueError('Playback incomplete')
    return {'shot':shot,'frames':cfg['frames'],'manifest':str(manifest.relative_to(HERE.parents[1])),
            'full_decode':'PASS','actual_browser_playback':playback['status'],
            'decoded_frames':playback['decodedFrames'],'dropped_frames':playback['droppedFrames'],
            'original_audio_PCM_exact':True,'all_delivered_file_hashes':'PASS',
            'director_final_acceptance':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--export-completed',action='store_true')
    args=parser.parse_args();repo=HERE.parents[1];ledger=repo/'production/PROGRESS.json'
    progress=json.loads(ledger.read_text());completed=[];graphics=[];running=[];interrupted=[]
    for shot in progress['queue_implemented']:
        destination=HERE/'deliverables'/shot
        result=verified_delivery(destination)
        for state_file in sorted((HERE/'output'/shot).glob('*/state.json')):
            state=json.loads(state_file.read_text());picture=state.get('picture',{})
            path=Path(picture.get('path',''))
            if result is None and args.export_completed and picture.get('full_decode')=='PASS' and path.is_file() and sha(path)==picture['sha256']:
                conform=state_file.parent/'conformed'
                if (conform/(shot+'_AUDIO_CONFORM.json')).exists() and (conform/(shot+'_3D_REVIEW.mp4.playback.json')).exists():
                    subprocess.run([sys.executable,HERE/'export_deliverable.py','--state',state_file,'--output',destination],check=True)
                    result=verified_delivery(destination)
            if state['status']=='RENDERING':
                record={'shot':shot,'state':str(state_file.relative_to(repo)),
                        'frames_required':state['config']['frames'],
                        'verified_frame_cache_count':len(state.get('verified_frames',{})),
                        'not_final_output':True}
                with (state_file.parent/'render.lock').open('r') as lock:
                    try:
                        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        record['status']='STALE_RENDER_STATE_NO_ACTIVE_LOCK';interrupted.append(record)
                    except BlockingIOError:
                        record['status']='RENDERING_LOCK_HELD';running.append(record)
        if result:completed.append(result)
    for shot in ['E8-CARD','E9-CARD']:
        result=verified_delivery(HERE/'deliverables'/shot)
        if result:graphics.append(result)
    progress.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    completed_production_renders=completed,
                    completed_native_graphics=graphics,
                    new_native_2D_render_frames=sum(r['frames'] for r in graphics),
                    new_native_3D_render_frames=sum(r['frames'] for r in completed),
                    new_native_3D_render_seconds=sum(r['frames'] for r in completed)/24,
                    active_render=running[0] if running else None,
                    interrupted_render_states=interrupted,
                    production_queue='RENDERING' if running else 'NO_ACTIVE_RENDER_LOCK',
                    automatic_cross_session_execution=False)
    pending=ledger.with_suffix('.pending.json');pending.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n');pending.replace(ledger)
    audit_path=repo/'production/SHOT_AUDIT.json';audit=json.loads(audit_path.read_text())
    for record in completed+graphics:
        row=next(r for r in audit['shots'] if r['id']==record['shot'])
        row['new_render']=record
        if row['audit_status'] in ['完全缺失画面资产','仅有配置，未渲染']:
            row['audit_status']='部分完成';row['reason']='新增三维工作渲染通过技术校验，创作终验待完成'
    audit['status_counts']=dict(collections.Counter(r['audit_status'] for r in audit['shots']))
    audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'delivered_shots':[r['shot'] for r in completed],
                      'delivered_native_cards':[r['shot'] for r in graphics],
                      'delivered_frames':progress['new_native_3D_render_frames'],
                      'active_render':progress['active_render'],'stale_states':interrupted,
                      'final_film_completed':False},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
