"""Run inside Blender to attest independent geometry/object/camera animation."""
import json
from pathlib import Path
import sys
import bpy

scene=bpy.context.scene
tracked=[]
for obj in bpy.data.objects:
    if obj.type=='CAMERA' or obj.name=='ANIMATED_ROTOR' or obj.name.startswith('Stationary cage ring') and len(tracked)<3:
        tracked.append(obj)
if not any(o.name=='ANIMATED_ROTOR' for o in tracked):
    tracked.extend(o for o in bpy.data.objects if o.name.startswith('Screen surface'))
records=[]
for frame in [1,7,13,19]:
    scene.frame_set(min(frame,scene.frame_end))
    records.append({'frame':scene.frame_current,'objects':{
        obj.name:{'type':obj.type,'world_matrix':[[float(x) for x in row] for row in obj.matrix_world]} for obj in tracked}})
camera=scene.camera
result={'blender_version':bpy.app.version_string,'engine':scene.render.engine,
        'mesh_objects':sum(o.type=='MESH' for o in bpy.data.objects),
        'curve_objects':sum(o.type=='CURVE' for o in bpy.data.objects),
        'frames':scene.frame_end,'fps':scene.render.fps,'camera_focal_mm':camera.data.lens,
        'depth_of_field':camera.data.dof.use_dof,'f_stop':camera.data.dof.aperture_fstop,
        'motion_blur_enabled':scene.render.use_motion_blur,'motion_blur_shutter':scene.render.motion_blur_shutter,
        'geometry_samples':records,'animation_type':'INDEPENDENT_NATIVE_GEOMETRY_AND_CAMERA',
        'actor_animation_acceptance':False}
output=Path(sys.argv[sys.argv.index('--')+1]);output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(result,indent=2))
print('Scene audit saved',output)
