"""Build an actual skinned hand/character study from pinned CC0 mesh data.

Run inside Blender. This is an anatomical deformation study, not an identity-
matched actor and not a replacement for the recovered character references.
Only the left forearm and hand are visible in the study camera.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector,Quaternion
from blender_scene import material,light,aim

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--only-frame',type=int);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.output.mkdir(parents=True,exist_ok=True)
    root=HERE/'assets/makehuman';source=json.loads((root/'SOURCE.json').read_text())
    for row in source['files']:
        path=root/row['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Asset changed: '+str(path))
    data=root/'makehuman/data';positions=[];faces=[];uvs=[];face_uv=[];group=''
    for line in (data/'3dobjs/base.obj').read_text().splitlines():
        parts=line.split()
        if not parts:continue
        if parts[0]=='v':positions.append(Vector(tuple(map(float,parts[1:4]))))
        elif parts[0]=='vt':uvs.append(tuple(map(float,parts[1:3])))
        elif parts[0]=='g':group=parts[1]
        elif parts[0]=='f' and group=='body':
            refs=[p.split('/') for p in parts[1:]];faces.append([int(p[0])-1 for p in refs]);face_uv.append([int(p[1])-1 for p in refs])
    for line in (data/'targets/macrodetails/asian-female-young.target').read_text().splitlines():
        fields=line.split()
        if len(fields)==4 and not line.startswith('#'):positions[int(fields[0])]+=Vector(tuple(map(float,fields[1:])))
    # MakeHuman's vertical Y becomes Blender Z; one source unit is 10 cm.
    positions=[Vector((v.x,-v.z,v.y))*.1 for v in positions]
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=8
    scene.render.resolution_x=640;scene.render.resolution_y=268;scene.render.resolution_percentage=100
    scene.render.fps=24;scene.frame_start=1;scene.frame_end=24
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.view_settings.view_transform='AgX';scene.world.color=(.02,.02,.02)
    spec=json.loads((data/'rigs/default.mhskel').read_text());weights=json.loads((data/'rigs/default_weights.mhw').read_text())['weights']
    mesh=bpy.data.meshes.new('Anatomical base topology');mesh.from_pydata(positions,[],faces);mesh.update()
    body=bpy.data.objects.new('CC0 anatomical deformation study',mesh);scene.collection.objects.link(body)
    uv=mesh.uv_layers.new(name='Original UV')
    for poly,indices in zip(mesh.polygons,face_uv):
        for loop,index in zip(poly.loop_indices,indices):uv.data[loop].uv=uvs[index]
        poly.use_smooth=True
    arm=bpy.data.armatures.new('163 bone anatomical rig');rig=bpy.data.objects.new('Uncast character development rig',arm)
    scene.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    def joint(name):
        indices=spec['joints'][name];return sum((positions[i] for i in indices),Vector())/len(indices)
    bpy.ops.object.mode_set(mode='EDIT')
    for name,description in spec['bones'].items():
        bone=arm.edit_bones.new(name);bone.head=joint(description['head']);bone.tail=joint(description['tail'])
        if (bone.tail-bone.head).length<1e-5:bone.tail.z+=.001
        plane=spec['planes'].get(description.get('rotation_plane'))
        if plane:
            a,b,c=[joint(n) for n in plane];normal=(b-a).cross(c-a)
            if normal.length>1e-6:bone.align_roll(normal.normalized())
    for name,description in spec['bones'].items():
        if description['parent']:arm.edit_bones[name].parent=arm.edit_bones[description['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    totals=[0.0]*len(positions)
    for rows in weights.values():
        for i,w in rows:totals[i]+=w
    for name,rows in weights.items():
        group=body.vertex_groups.new(name=name)
        for i,w in rows:
            if totals[i]>0:group.add([i],w/totals[i],'REPLACE')
    modifier=body.modifiers.new('Actual skeletal skinning','ARMATURE');modifier.object=rig
    skin=material('Untextured skin study',(.37,.23,.17),0,.5)
    skin.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=0
    body.data.materials.append(skin)
    # Keep all topology in the source asset, but mask everything except the
    # left forearm/hand from this close-up. No face is presented as Lin Wu.
    group=body.vertex_groups.new(name='Visible forearm and hand')
    visible=set()
    for name,rows in weights.items():
        if name.endswith('.L') and name.startswith(('lowerarm','wrist','metacarpal','finger')):
            visible.update(i for i,w in rows if w>.03)
    group.add(sorted(visible),1,'REPLACE');mask=body.modifiers.new('Hand study isolation','MASK');mask.vertex_group=group.name
    sub=body.modifiers.new('Anatomical surface smoothing','SUBSURF');sub.levels=1;sub.render_levels=1
    for frame in range(1,25):
        amount=.5-.5*math.cos((frame-1)/23*math.pi)
        for name in rig.pose.bones.keys():
            if name.startswith('finger') and name.endswith('.L'):
                bone=rig.pose.bones[name];bone.rotation_mode='QUATERNION'
                # Resolve the anatomical flexion axis in each bone's own rest
                # basis. Imported rolls differ; one Euler axis/sign is unsafe.
                rest=rig.data.bones[name];direction=(rest.tail_local-rest.head_local).normalized()
                palm=Vector((.65,1,0)) if name.startswith('finger1-') else Vector((0,1,0))
                axis=direction.cross(palm).normalized()
                local_axis=rest.matrix_local.to_quaternion().inverted()@axis
                bone.rotation_quaternion=Quaternion(local_axis,amount*(.30 if name.startswith('finger1-') else .65))
                bone.keyframe_insert('rotation_quaternion',frame=frame)
    tips=[joint(spec['bones'][name]['head']) for name in spec['bones'] if name.startswith('finger') and name.endswith('.L')]
    target=sum(tips,Vector())/len(tips)
    bpy.ops.object.camera_add(location=target+Vector((.07,-.40,.19)));camera=bpy.context.object;scene.camera=camera
    camera.data.lens=47;camera.data.dof.use_dof=True;camera.data.dof.focus_distance=(camera.location-target).length;camera.data.dof.aperture_fstop=8;aim(camera,target)
    light('Soft key',target+Vector((-.3,-.4,.5)),target,18,(1,.78,.58),.5)
    light('Edge',target+Vector((.2,.3,.3)),target,12,(.55,.68,1),.3)
    scene['production_status']='ANATOMY_AND_SKINNING_STUDY_NOT_CAST_OR_FILM_READY';scene.frame_set(1)
    if not (args.output/'rig-study.blend').exists():bpy.ops.wm.save_as_mainfile(filepath=str(args.output/'rig-study.blend'))
    snapshot=Path(__file__).read_bytes();(args.output/'generator_snapshot.py').write_bytes(snapshot)
    report={'source_commit':source['commit'],'generator_sha256':hashlib.sha256(snapshot).hexdigest(),
            'asset_license':'CC0-1.0','vertices':len(positions),'body_faces':len(faces),
            'bones':len(arm.bones),'weight_groups':len(weights),'finger_animation_frames':24,
            'identity_matched':False,'clothes_hair_skin_detail_complete':False,'used_in_film':False,
            'source_rig':str(args.output/'rig-study.blend')}
    (args.output/'RIG_STUDY.json').write_text(json.dumps(report,indent=2))
    for frame in [args.only_frame] if args.only_frame else range(1,25):
        path=args.output/f'{frame:06d}.png'
        if path.exists():continue
        scene.frame_set(frame);scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)


if __name__=='__main__':main()
