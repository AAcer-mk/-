#!/usr/bin/env python3
"""Curate small Git-ready deliveries, retaining re-renderable physical scenes.

Frame caches stay local; source scene, all dynamic textures, all frame hashes,
selected decoded keyframes and final video bytes are retained in the delivery.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

PORTABLE = '''
import bpy,json,sys
from pathlib import Path
opts=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
destination=Path(opts['destination'])
for image in bpy.data.images:
    if image.source in {'FILE','SEQUENCE'}:
        candidate=destination/'textures'/Path(image.filepath).name
        if candidate.exists():
            image.filepath='//textures/'+candidate.name
            if len(list((destination/'textures').glob('*.png')))>1:
                image.source='SEQUENCE'
                for material in bpy.data.materials:
                    if material.use_nodes:
                        for node in material.node_tree.nodes:
                            if node.type=='TEX_IMAGE' and node.image==image:
                                node.image_user.frame_duration=opts['frames']
                                node.image_user.frame_start=1
                                node.image_user.use_auto_refresh=True
bpy.context.scene.render.filepath='//rerender/'
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(destination/'scene.blend'),relative_remap=False)
'''


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def copy_verified(src,dst):
    if dst.exists():
        if sha(src)!=sha(dst):raise ValueError('Use a new delivery directory: '+str(dst))
    else:
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)


def main():
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();state=json.loads(args.state.read_text())
    if not state.get('picture') or state['picture'].get('full_decode')!='PASS':
        raise ValueError('Only completed, decoded renders can be exported')
    src=args.state.parent;dst=args.output.resolve();dst.mkdir(parents=True,exist_ok=True)
    for name in ['state.json','validation.json']:
        if (src/name).exists():copy_verified(src/name,dst/name)
    for file in src.glob('*.mp4*'):
        if file.is_file() and file.suffix in ['.mp4','.json','.png']:copy_verified(file,dst/file.name)
    if (src/'conformed').exists():
        for file in (src/'conformed').iterdir():
            if file.is_file():copy_verified(file,dst/file.name)
    if (src/'textures').exists():
        for file in (src/'textures').glob('*.png'):copy_verified(file,dst/'textures'/file.name)
    copy_verified(src/'frames/timing.json',dst/'timing.json')
    # The cache's immutable PNG hashes stay in state.json. Retain actual preview
    # frames too; these are source renders, distinct from encoded/browser grabs.
    for index in [1,max(1,state['config']['frames']//2),state['config']['frames']]:
        copy_verified(src/'frames'/f'{index:06d}.png',dst/'keyframes'/f'{index:06d}.png')
    source_scene=src/'frames/scene.blend';marker=dst/'SCENE_SOURCE.json'
    portable=False
    if (dst/'scene.blend').exists():
        if marker.exists():
            recorded=json.loads(marker.read_text())
            portable=recorded['source_sha256']==sha(source_scene) and recorded['portable_sha256']==sha(dst/'scene.blend')
            if not portable:raise ValueError('Existing scene manifest differs; use a new delivery directory')
        elif sha(dst/'scene.blend')==sha(source_scene):
            # Preserve the earlier unmodified source copy before path rebasing.
            copy_verified(dst/'scene.blend',dst/'scene-source.blend');(dst/'scene.blend').unlink()
        else:raise ValueError('Existing scene is not the expected source; use a new delivery directory')
    if not portable:
        with tempfile.TemporaryDirectory() as temp:
            script=Path(temp)/'portable.py';script.write_text(PORTABLE)
            options=Path(temp)/'options.json';options.write_text(json.dumps({'destination':str(dst),'frames':state['config']['frames']}))
            subprocess.run(['blender','-b',str(src/'frames/scene.blend'),'--python',str(script),'--',str(options)],check=True)
        marker.write_text(json.dumps({'source_sha256':sha(source_scene),'portable_sha256':sha(dst/'scene.blend')},indent=2))
    files=[]
    for file in sorted(dst.rglob('*')):
        if file.is_file() and file.name!='DELIVERY.json':files.append({'path':str(file.relative_to(dst)),'bytes':file.stat().st_size,'sha256':sha(file)})
    receipt={'shot':state['config']['shot'],'type':'TECHNICAL_TEST' if state['config']['sample'] else 'AUTHORED_TIMELINE_PRODUCTION_RENDER',
             'configuration':state['config'],'all_files':files,'final_film':False,'director_final_acceptance':False,
             'source_scene_portable':True,'all_dynamic_textures_included':True,
             'native_frame_cache_retained_locally':True}
    (dst/'DELIVERY.json').write_text(json.dumps(receipt,indent=2))
    print('Exported',state['config']['shot'],len(files),'files',sum(x['bytes'] for x in files),'bytes')


if __name__=='__main__':main()
