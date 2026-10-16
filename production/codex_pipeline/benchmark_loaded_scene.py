"""Render an existing physical scene with another engine, without editing it."""
import argparse
import json
from pathlib import Path
import sys
import time
import bpy

p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
p.add_argument('--samples',type=int,default=64);p.add_argument('--frame',type=int,default=1)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);args.output.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
scene.cycles.samples=args.samples;scene.cycles.use_denoising=False;scene.cycles.max_bounces=4
scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.frame_set(args.frame);scene.render.filepath=str(args.output/f'{args.frame:06d}.png')
start=time.monotonic();bpy.ops.render.render(write_still=True)
(args.output/'BENCHMARK.json').write_text(json.dumps({'source_scene':bpy.data.filepath,
 'engine':'CYCLES','device':'CPU','threads':2,'samples':args.samples,'frame':args.frame,
 'width':scene.render.resolution_x,'height':scene.render.resolution_y,
 'seconds':time.monotonic()-start,'denoising':False,'film_output':False,
 'other_render_job_concurrently_active':True},indent=2))
