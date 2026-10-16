#!/usr/bin/env python3
"""Build real asset references and per-shot dependency/stage records.

Asset presence, readability, motion method and creative acceptance are separate.
Unknown jobs never acquire generated placeholders through this graph.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);args=p.parse_args()
    source=args.source.resolve();audit=json.loads((REPO/'production/SHOT_AUDIT.json').read_text())
    image_qa=json.loads((HERE/'qa/inherited/images.json').read_text())
    media_qa=json.loads((HERE/'qa/inherited/media.json').read_text())
    for folder in (HERE/'qa').iterdir():
        if not folder.is_dir() or folder.name=='inherited':continue
        for name,destination in [('images.json',image_qa),('media.json',media_qa)]:
            file=folder/name
            if file.exists():destination.extend(json.loads(file.read_text()))
    def resolved(ref):
        path=Path(ref);return str((path if path.is_absolute() else REPO/path).resolve())
    checks={resolved(r['path']):r.get('decode',r.get('full_decode','UNVERIFIED')) for r in image_qa+media_qa}
    assets={}
    def register(ref,expected=None):
        if ref in assets:return ref
        path=source/ref.removeprefix('baseline/') if ref.startswith('baseline/') else REPO/ref
        kind={'.png':'STATIC_IMAGE','.jpg':'STATIC_IMAGE','.svg':'VECTOR_GRAPHIC',
              '.mp4':'VIDEO_NOT_AUTOMATICALLY_ANIMATION','.mkv':'VIDEO_NOT_AUTOMATICALLY_ANIMATION',
              '.flac':'AUDIO','.wav':'AUDIO','.blend':'NATIVE_3D_SCENE','.obj':'BASE_MESH',
              '.mhw':'SKIN_WEIGHTS','.mhskel':'SKELETON','.bvh':'SKELETAL_MOTION'}.get(path.suffix.lower(),'SOURCE_DATA')
        exists=path.is_file();actual=sha(path) if exists else None
        if expected and (not exists or actual!=expected['sha256'] or path.stat().st_size!=expected['bytes']):raise ValueError('Original changed: '+ref)
        readability=checks.get(str(path.resolve()),'NOT_MEDIA_OR_UNVERIFIED')
        assets[ref]={'path':ref,'kind':kind,'exists':exists,'bytes':path.stat().st_size if exists else None,
                     'sha256':actual,'readability':readability,'excluded':readability=='FAIL',
                     'file_presence_is_not_creative_approval':True}
        return ref
    recovery=json.loads((HERE/'qa/recovery/baseline_recovery.json').read_text())
    for row in recovery['files']:register('baseline/'+row['path'],row)
    for path in sorted((HERE/'assets/makehuman').rglob('*')):
        if path.is_file():register(str(path.relative_to(REPO)))
    development=[]
    study=HERE/'deliverables/character-rig-study/DELIVERY.json'
    if study.exists():
        data=json.loads(study.read_text())
        for row in data['all_files']:register(str((study.parent/row['path']).relative_to(REPO)),row)
        development.append({'manifest':str(study.relative_to(REPO)),'type':data['type'],'film_output':False,'identity_matched':False})
    jobs=[]
    motion_needed={'E6-07','E6-08','E7-02','E7-03','E7-06'}
    for row in audit['shots']:
        shot=row['id'];inputs=[register(ref) for ref in row['candidate_paths']+row['inherited_decoded_media']]
        result=row.get('new_render');delivery=None;outputs=[]
        if result:
            manifest=REPO/result['manifest'];delivery=json.loads(manifest.read_text())
            for item in delivery['all_files']:
                if Path(item['path']).suffix in ['.mp4','.mkv','.blend']:
                    outputs.append(register(str((manifest.parent/item['path']).relative_to(REPO))))
        if delivery:
            content='PROGRAMMATIC_2D_TYPEWRITING' if delivery['configuration']['mode']=='native_card' else 'NATIVE_3D_ANIMATION'
            stages={'assets':'HASH_VERIFIED','scene_animation':'RENDERED','picture':'FULL_DECODE_PASS',
                    'audio':'EXACT_INHERITED_PCM_CONFORM','playback':'ACTUAL_CHROMIUM_PASS',
                    'performance_context_final_QC':'PENDING'}
        else:
            content=row['motion_type'];stages={'assets':'PARTIAL' if inputs else 'MISSING_SHOT_ASSETS',
                    'scene_animation':'AUTHORED_STILLNESS' if row.get('intentional_stillness') else 'UNVERIFIED_OR_REWORK_REQUIRED',
                    'picture':'INHERITED_WORKPRINT' if row['inherited_decoded_media'] else 'MISSING_VERIFIED_RENDER',
                    'audio':'INHERITED_MIX_NOT_FINAL','playback':'SEE_INHERITED_MEDIA_QA','performance_context_final_QC':'PENDING'}
        blockers=[]
        if shot in motion_needed:blockers=['Identity-consistent character assets','Continuous authored action and object contact','Performance and continuity QC']
        elif not delivery and row['audit_status']=='完全缺失画面资产':blockers=['Create the authored scene and movable assets','Render and inspect the original frame range']
        elif not delivery and not row.get('intentional_stillness'):blockers=['Review or replace inherited image motion','Complete performance and context QC']
        jobs.append({'shot':shot,'frames':[row['start_frame'],row['end_frame']],
                     'frame_count':row['end_frame']-row['start_frame'],'fps':24,
                     'inputs':inputs,'outputs':outputs,'content_method':content,'stages':stages,
                     'production_status':row['audit_status'],'intentional_stillness':row.get('intentional_stillness'),
                     'new_delivery':result['manifest'] if result else None,'blockers':blockers,
                     'final_film_accepted':False})
    payload={'schema':1,'source_archive_sha256':recovery['archive_sha256'],
             'assets':list(assets.values()),'development_assets':development,
             'counts_by_kind':dict(collections.Counter(a['kind'] for a in assets.values()))}
    (REPO/'production/ASSET_INDEX.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    graph={'schema':1,'timeline_frames':26280,'fps':24,'jobs':jobs,
           'dependency_order':['ASSETS','SCENE','ANIMATION','RENDER','COMPOSITE','AUDIO','QC','FINAL'],
           'final_film_completed':False,'missing_data_policy':'NO_AUTOMATIC_PLACEHOLDER_SUBSTITUTION'}
    (REPO/'production/JOB_GRAPH.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'assets':len(assets),'timeline_jobs':len(jobs),'new_verified_deliveries':sum(bool(j['new_delivery']) for j in jobs),'final_film_completed':False}))


if __name__=='__main__':main()
