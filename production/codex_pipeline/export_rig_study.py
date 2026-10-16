#!/usr/bin/env python3
"""Export a verified anatomy study, explicitly excluded from film deliveries."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();src=args.source.resolve();dst=args.output.resolve()
    if (dst/'DELIVERY.json').exists():raise FileExistsError('Preserve prior study delivery')
    movie=src/'HAND_SKINNING_STUDY.mp4'
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(movie),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(movie)]))
    video=next(r for r in probe['streams'] if r['codec_type']=='video')
    assert int(video['nb_read_frames'])==24 and video['r_frame_rate']=='24/1'
    playback=json.loads((src/'HAND_SKINNING_STUDY.mp4.playback.json').read_text())
    assert playback['ended'] and not playback['error'] and playback['decodedFrames']==24
    hashes={}
    for n in range(1,25):
        file=src/f'{n:06d}.png'
        with Image.open(file) as im:im.load();assert im.size==(640,268)
        hashes[file.name]=sha(file)
    assert len(set(hashes.values()))==24
    dst.mkdir(parents=True,exist_ok=True)
    for name in ['HAND_SKINNING_STUDY.mp4','HAND_SKINNING_STUDY.mp4.playback.json','HAND_SKINNING_STUDY.mp4.playback.png','RIG_STUDY.json','generator_snapshot.py']:
        shutil.copy2(src/name,dst/name)
    (dst/'keyframes').mkdir(exist_ok=True)
    for n in [1,12,24]:shutil.copy2(src/f'{n:06d}.png',dst/'keyframes'/f'{n:06d}.png')
    (dst/'FRAME_SHA256.json').write_text(json.dumps(hashes,indent=2))
    with tempfile.TemporaryDirectory() as temp:
        script=Path(temp)/'portable.py'
        script.write_text("import bpy,json,sys\nfrom pathlib import Path\np=Path(sys.argv[sys.argv.index('--')+1])\nbpy.context.scene.frame_set(1)\nbpy.context.scene.render.filepath='//rerender/'\nbpy.ops.wm.save_as_mainfile(filepath=str(p/'scene.blend'),relative_remap=False)\n")
        subprocess.run(['blender','-b',str(src/'rig-study.blend'),'--python-exit-code','1','--python',str(script),'--',str(dst)],check=True)
    study=json.loads((dst/'RIG_STUDY.json').read_text())
    receipt={'type':'TECHNICAL_CHARACTER_RIG_STUDY','film_output':False,'identity_matched':False,
             'anatomy_review':'FLEXION_DIRECTION_CORRECTED_FROM_EULER_PROTOTYPE',
             'frames':24,'fps':24,'full_decode':'PASS','actual_browser_playback':'PASS',
             'source_scene_portable':True,'body_mesh_vertices':study['vertices'],'bones':study['bones'],
             'asset_source_manifest':'production/codex_pipeline/assets/makehuman/SOURCE.json',
             'limitations':['No established actor identity match','No finished costume, hair or skin detail','No prop contact or full body performance approval'],
             'all_files':[{'path':str(f.relative_to(dst)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(dst.rglob('*')) if f.is_file()]}
    (dst/'DELIVERY.json').write_text(json.dumps(receipt,indent=2));print('EXPORTED_TECHNICAL_RIG_STUDY',len(receipt['all_files']))


if __name__=='__main__':main()
