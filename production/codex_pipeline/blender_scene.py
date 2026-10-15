"""Procedural physical scenes, rendered inside Blender 4.3+.

The F4 fan is modeled from recovered F4-01_v1, not animated as a flat plate.
Other modes are development comparisons until reviewed against source designs.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector


def material(name, color, metal=0, rough=.4, emission=0):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Metallic'].default_value = metal
    node.inputs['Roughness'].default_value = rough
    if emission:
        node.inputs['Emission Color'].default_value = (*color, 1)
        node.inputs['Emission Strength'].default_value = emission
    return mat


def textured_metal(name, color, rough=.4):
    mat = material(name, color, .8, rough)
    nodes = mat.node_tree.nodes
    noise = nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 150
    bump = nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .16
    bump.inputs['Distance'].default_value = .018
    mat.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    mat.node_tree.links.new(bump.outputs['Normal'], nodes.get('Principled BSDF').inputs['Normal'])
    return mat


def box(name, loc, dims, mat, bevel=.02):
    # Direct data API avoids O(scene size) context/depsgraph evaluation per box.
    x,y,z=[d/2 for d in dims]
    vertices=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),
              (x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);obj.location=loc
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Manufactured edge', 'BEVEL'); mod.width = bevel; mod.segments = 3
        obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return obj


def cylinder(name, loc, radius, depth, mat, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                      location=loc, rotation=(math.pi/2, 0, 0))
    obj = bpy.context.object; obj.name = name; obj.data.materials.append(mat)
    bevel = obj.modifiers.new('Machined lip', 'BEVEL'); bevel.width = .006; bevel.segments = 2
    obj.modifiers.new('Normals', 'WEIGHTED_NORMAL')
    return obj


def tube(name, points, radius, mat):
    curve = bpy.data.curves.new(name, 'CURVE'); curve.dimensions = '3D'
    curve.bevel_depth = radius; curve.bevel_resolution = 2
    spline = curve.splines.new('POLY'); spline.points.add(len(points)-1)
    for p, xyz in zip(spline.points, points):
        p.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve); bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def light(name, pos, target, power, color, size):
    data = bpy.data.lights.new(name, 'AREA'); data.energy = power; data.color = color
    data.shape = 'DISK'; data.size = size
    obj = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(obj)
    obj.location = pos; obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj


def aim(camera, point):
    camera.rotation_euler = (Vector(point)-camera.location).to_track_quat('-Z', 'Y').to_euler()


def make_fan(cx=0, cy=0, cz=1.2, scale=1):
    # Full-depth pitch-varying blades, enclosed by a stationary wire cage.
    existing = set(bpy.data.objects)
    frame = textured_metal('Black powder-coated casing', (.035,.032,.027), .48)
    brass = material('Warm graphite grille', (.09,.075,.052), .9, .3)
    blade_mat = material('Brushed rotor alloy', (.12,.115,.10), .86, .26)
    black = material('Cavity', (.009,.009,.008), .4, .5)
    for x in [-.68,.68]:
        box('Fan housing side', (x, .11, 0), (.18,.30,1.5), frame)
    for z in [-.68,.68]:
        box('Fan housing edge', (0,.11,z), (1.2,.30,.18), frame)
    cylinder('Dark motor cavity', (0,.20,0), .65,.06, black)
    bpy.ops.object.empty_add(); rotor = bpy.context.object; rotor.name = 'ANIMATED_ROTOR'
    # Blades sweep tangentially and twist in depth, not coplanar fan icons.
    for k in range(7):
        verts=[]; faces=[]
        for side in [-1,1]:
            for j in range(13):
                r=.17 + j/12*.45
                angle=k*2*math.pi/7 + .65*j/12 + side*(.08+.24*j/12)
                verts.append((r*math.cos(angle), .04 + side*.055*(j/12), r*math.sin(angle)))
        for j in range(12): faces.append((j,j+1,14+j,13+j))
        mesh=bpy.data.meshes.new('Twisted aerofoil');mesh.from_pydata(verts,[],faces);mesh.update()
        blade=bpy.data.objects.new('Rotor blade '+str(k),mesh);bpy.context.collection.objects.link(blade)
        blade.data.materials.append(blade_mat);blade.parent=rotor
        solid=blade.modifiers.new('Blade thickness','SOLIDIFY');solid.thickness=.009
        for poly in mesh.polygons:poly.use_smooth=True
    for r in [.19,.28,.38,.48,.59,.66]:
        tube('Stationary cage ring', [(r*math.cos(a*2*math.pi/96),-.055,r*math.sin(a*2*math.pi/96)) for a in range(97)], .0065, brass)
    for a in range(8):
        ang=a*math.pi/4
        tube('Stationary radial guard',[(r*math.cos(ang),-.07,r*math.sin(ang)) for r in [.17,.69]],.008,brass)
    cylinder('Stationary bearing cap',(0,-.085,0),.17,.065,frame)
    for x in [-.67,.67]:
        for z in [-.67,.67]:
            cylinder('Recessed machine screw',(x,-.059,z),.046,.035,brass,24)
            box('Screw slot',(x,-.081,z),(.039,.003,.006),black,.001)
    members=set(bpy.data.objects)-existing
    bpy.ops.object.empty_add(location=(cx,cy,cz));root=bpy.context.object;root.name='Fan assembly'
    for obj in members:
        if obj.parent is None:obj.parent=root
    root.scale=(scale,)*3
    return rotor


def fan_scene():
    rotor=make_fan()
    metal=textured_metal('Rack rails',(.052,.043,.03))
    for x in [-.95,.95]:
        box('Upright',(x,.06,1.2),(.16,.35,3.3),metal)
        for z in range(20):box('Punched rack rail',(x,-.13,z*.16),(.058,.01,.06),material('Rack cutout',(.005,.005,.004)),.006)
    for z in [0,2.4]:make_fan(cy=.15,cz=z,scale=.62)
    light('Tungsten grazing key',(-1.4,-1.2,2.5),(0,0,1.2),140,(1,.59,.27),1.1)
    light('Warm edge',(1,.15,2.2),(0,0,1.2),90,(1,.70,.40),.7)
    light('Cold practical',(-1,.5,.6),(0,0,1.2),12,(.32,.46,.58),.5)
    return rotor


def room_scene():
    metal=textured_metal('Rack cabinet',(.032,.037,.038),.4)
    dark=material('Server slot',(.012,.016,.018),.3,.5)
    led=material('Muted green diagnostic LED',(.13,.40,.21),.1,.35,2)
    floor=material('Sealed concrete',(.052,.049,.044),.15,.45)
    box('Floor',(0,1,-.12),(10,16,.2),floor)
    box('Ceiling',(0,1,3.4),(10,16,.2),metal)
    for side in [-1,1]:
        for row in range(4):
            x=side*2.0;y=-1+row*2.1
            box('Cabinet',(x,y,1.5),(1.1,1.4,3),metal,.04)
            for rack in range(12):
                z=.2+rack*.225
                box('Server drawer',(x,y-.72,z),(.94,.04,.15),dark,.006)
                for i in range(3):box('Status diode',(x-.36+i*.07,y-.75,z),(.012,.012,.012),led,.002)
                for i in range(6):box('Vent',(x+.08+i*.06,y-.75,z),(.015,.01,.09),metal,.001)
    for y in [-2,1,4,7]:
        light('Ceiling practical',(0,y,3.18),(0,y,0),90,(1,.69,.39),1.8)
        box('Luminaire',(0,y,3.26),(1.6,.18,.04),material('Lamp',(1,.68,.35),0,.3,3))
    box('Far wall',(0,8,1.5),(9,.2,3.3),metal)
    return []


def screen_scene(texture):
    frame=textured_metal('Display bezel',(.027,.028,.026))
    box('Display',(0,0,1.15),(2.0,.16,1.26),frame,.035)
    mat=material('Display pixels',(.2,.25,.2),0,.6)
    node=mat.node_tree.nodes.get('Principled BSDF');image=mat.node_tree.nodes.new('ShaderNodeTexImage')
    image.image=bpy.data.images.load(str(texture));image.interpolation='Linear'
    mat.node_tree.links.new(image.outputs['Color'],node.inputs['Base Color'])
    mat.node_tree.links.new(image.outputs['Color'],node.inputs['Emission Color']);node.inputs['Emission Strength'].default_value=.8
    bpy.ops.mesh.primitive_plane_add(size=1,location=(0,-.086,1.15),rotation=(math.pi/2,0,0))
    obj=bpy.context.object;obj.name='Screen surface';obj.scale=(1.84,1.08,1);obj.data.materials.append(mat)
    box('Monitor stem',(0,.05,.3),(.10,.15,.6),frame)
    box('Desk',(0,0,-.05),(4,2,.15),frame)
    light('Screen reflection',(-.8,-1,1.8),(0,0,1),45,(.5,.62,.62),1.5)
    return image.image


def printer_scene(texture):
    shell=material('Printer aged grey polymer',(.22,.23,.21),0,.53)
    inset=material('Printer recess',(.018,.022,.020),.1,.4)
    paper=material('Uncoated paper',(.58,.57,.51),0,.8)
    box('Printer main body',(0,.2,.77),(2.5,1.45,1.4),shell,.09)
    box('Scanner lid',(0,.17,1.51),(2.55,1.50,.10),shell,.04)
    box('Output cavity',(0,-.56,.65),(1.9,.08,.43),inset,.03)
    for z in [.19,.34]:
        box('Paper drawer',(0,-.56,z),(2.18,.1,.12),shell,.018)
        box('Drawer handle',(0,-.63,z),(.42,.04,.04),inset,.008)
    image=screen_scene(texture)
    # Reuse the UV-defined physical screen, discard desktop monitor stand/back.
    for name in ['Display','Monitor stem','Desk']:
        obj=bpy.data.objects.get(name)
        if obj:bpy.data.objects.remove(obj,do_unlink=True)
    surface=bpy.data.objects['Screen surface'];surface.location=(.16,-.569,1.22);surface.scale=(1.5,.46,1)
    box('Printer control bezel',(.16,-.519,1.22),(1.66,.09,.59),inset,.025)
    led=material('Printer ready lamp',(.28,.52,.32),0,.4,1.8)
    cylinder('Ready indicator',(-.95,-.55,1.25),.025,.02,led,20)
    box('Catch tray',(0,-.93,.41),(1.8,.85,.045),shell,.02)
    sheets=[]
    for i in range(3):
        sheet=box('Moving sheet '+str(i),(0,-.81,.47+i*.009),(1.55,.55,.004),paper,.001)
        sheets.append(sheet)
    metal=material('Printer rollers',(.07,.07,.065),.4,.3)
    for x in [-.6,.6]:
        roll=cylinder('Feed roller',(x,-.55,.69),.05,.16,metal,24);roll.rotation_euler=(0,math.pi/2,0)
    light('Office fluorescent',(-2,-2,3),(0,0,1),160,(.75,.80,.76),2.5)
    return image,sheets


def interaction_scene():
    # Clearly labelled rig feasibility test. No claim of actor or identity approval.
    frame=textured_metal('Breaker plate',(.10,.09,.07))
    grip=material('Bakelite',(.025,.02,.017),0,.25)
    skin=material('Unapproved hand study',(.32,.20,.13),0,.62)
    box('Breaker panel',(0,.3,1.1),(2,.13,1.7),frame)
    cylinder('Hinge',(0,.15,1.2),.14,.18,grip)
    bpy.ops.object.empty_add(location=(0,0,1.2));hinge=bpy.context.object;hinge.name='Articulated lever pivot'
    handle=box('Breaker handle',(0,-.12,1.46),(.5,.13,.12),grip);handle.parent=hinge;handle.matrix_parent_inverse=hinge.matrix_world.inverted()
    rod=box('Lever shaft',(0,0,1.32),(.08,.06,.3),frame);rod.parent=hinge;rod.matrix_parent_inverse=hinge.matrix_world.inverted()
    bpy.ops.object.empty_add(location=(0,-.24,1.49));hand=bpy.context.object;hand.name='Hand IK target study'
    palm=box('Palm',(0,-.24,1.55),(.27,.12,.24),skin,.045)
    palm.parent=hand;palm.matrix_parent_inverse=hand.matrix_world.inverted()
    fingers=[]
    for i in range(4):
        for j in range(3):
            finger=box('Finger phalanx',(-.102+i*.068,-.25+j*.025,1.42-j*.048),(.049,.055,.065),skin,.019)
            finger.parent=hand;finger.matrix_parent_inverse=hand.matrix_world.inverted();fingers.append(finger)
    thumb=box('Opposable thumb',(.18,-.25,1.51),(.08,.065,.13),skin,.03);thumb.rotation_euler[1]=-.7
    thumb.parent=hand;thumb.matrix_parent_inverse=hand.matrix_world.inverted()
    light('Task light',(-1,-1,2.5),(0,0,1.2),100,(1,.65,.34),1)
    light('Edge light',(1,.3,2),(0,0,1.2),40,(.25,.4,.5),.8)
    return hand,hinge


def setup(args):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine=args.engine
    scene.render.threads_mode='FIXED';scene.render.threads=4
    if args.engine=='CYCLES':
        scene.cycles.device='CPU';scene.cycles.samples=args.samples;scene.cycles.use_denoising=False
        scene.cycles.max_bounces=4;scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2
        scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.05
    else:scene.eevee.taa_render_samples=args.samples
    scene.render.resolution_x=args.width;scene.render.resolution_y=round(args.width/2.39)
    scene.render.resolution_percentage=100;scene.render.fps=24
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.color_depth='8';scene.render.film_transparent=False
    scene.world.color=(.008,.008,.008)
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.use_motion_blur=True;scene.render.motion_blur_shutter=.5
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Physical camera';scene.camera=cam
    cam.data.lens=65;cam.data.dof.use_dof=True;cam.data.dof.aperture_fstop=5.6
    data=None
    if args.mode=='fan':
        data=fan_scene();cam.location=(.04,-2.45,1.25);target=(0,0,1.2);cam.data.lens=60
    elif args.mode in ['room','lowlight']:
        data=room_scene();cam.location=(.2,-5.5,1.5);target=(0,4,1.5);cam.data.lens=30;cam.data.dof.aperture_fstop=8
        if args.mode=='lowlight':
            for lamp in bpy.data.lights:
                lamp.energy*=.25;lamp.color=(1,.23,.07)
    elif args.mode=='printer':
        data=printer_scene(args.texture);cam.location=(.32,-2.85,1.55);target=(.08,-.53,1.20);cam.data.lens=65;cam.data.dof.aperture_fstop=8
    elif args.mode=='screen':
        data=screen_scene(args.texture);cam.location=(.35,-3.65,1.42);target=(0,0,1.15);cam.data.lens=55
    else:
        data=interaction_scene();cam.location=(.65,-2.55,1.55);target=(0,0,1.4);cam.data.lens=65
    aim(cam,target);cam.data.dof.focus_distance=(cam.location-Vector(target)).length
    return scene,cam,target,data


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['fan','room','screen','interaction','lowlight','printer'],required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--width',type=int,default=960)
    p.add_argument('--samples',type=int,default=16);p.add_argument('--frames',type=int,default=48)
    p.add_argument('--engine',default='CYCLES');p.add_argument('--texture',type=Path)
    p.add_argument('--only-frame',type=int);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.output.mkdir(parents=True,exist_ok=True)
    scene,cam,target,data=setup(args);initial=cam.location.copy();records=[]
    # Subframe keyframes give Cycles real object/camera motion blur.
    for frame in range(0,args.frames+2):
        t=(frame-1)/24;pct=max(0,min(1,(frame-1)/max(1,args.frames-1)))
        if args.mode=='fan':
            data.rotation_euler[1]=t*2*math.pi*5.37;data.keyframe_insert('rotation_euler',frame=frame)
            cam.location=initial+Vector((.006*math.sin(t*2*math.pi),.01*math.sin(t*2*math.pi+.4),.004*math.cos(t*2*math.pi)))
        elif args.mode in ['room','lowlight']:
            cam.location=initial+Vector((.35*pct,1.8*pct,.025*math.sin(pct*math.pi)))
        elif args.mode in ['screen','printer']:
            cam.location=initial+Vector((-.18*pct,.18*pct,0))
            if args.mode=='printer':
                for i,sheet in enumerate(data[1]):
                    sheet.location.y=-.70-.35*((t*.65+i*.33)%1)
                    sheet.keyframe_insert('location',frame=frame)
        else:
            amount=(1-math.cos(math.pi*max(0,min(1,(pct-.25)/.55))))/2
            hand,hinge=data;hinge.rotation_euler[0]=amount*1.3;hinge.keyframe_insert('rotation_euler',frame=frame)
            hand.location=(0,-.24-.26*math.sin(amount*1.3),1.49-.26*(1-math.cos(amount*1.3)))
            hand.rotation_euler[0]=amount*.9;hand.keyframe_insert('location',frame=frame);hand.keyframe_insert('rotation_euler',frame=frame)
        aim(cam,target);cam.keyframe_insert('location',frame=frame);cam.keyframe_insert('rotation_euler',frame=frame)
    for action in bpy.data.actions:
        for fc in action.fcurves:
            for key in fc.keyframe_points:key.interpolation='LINEAR'
    scene.frame_end=args.frames
    blend=args.output/'scene.blend'
    if not blend.exists():bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    frame_range=[args.only_frame] if args.only_frame is not None else range(1,args.frames+1)
    for frame in frame_range:
        dst=args.output/f'{frame:06d}.png'
        if dst.exists():continue
        scene.frame_set(frame)
        if args.mode in ['screen','printer']:
            alternate=args.texture.parent/f'{frame:06d}.png'
            image=data[0] if args.mode=='printer' else data
            if alternate.exists():image.filepath=str(alternate);image.reload()
        scene.render.filepath=str(dst);start=time.monotonic();bpy.ops.render.render(write_still=True)
        records.append({'frame':frame,'seconds':time.monotonic()-start})
        (args.output/'timing.json').write_text(json.dumps(records,indent=2))
    print('RENDER_FINISHED',args.mode,len(records),flush=True)


if __name__=='__main__':main()
