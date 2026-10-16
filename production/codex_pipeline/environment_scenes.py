"""Actor-free shots from the recovered brief; real geometry and animation.

E8-01: distant navigation lights in a slowly migrating airborne river.
END-07: wall clock at 04:47, without explaining the conflicting times.
No recovered shot model exists for either shot. Seeded construction is repeatable.
"""
import math
import random
import bpy
from mathutils import Vector
from blender_scene import box, material, light, textured_metal


def drones(scene, camera, frames):
    rng=random.Random(80314)
    camera.location=(0,0,1.8);camera.data.lens=31
    camera.data.dof.aperture_fstop=11
    target=(0,110,55)
    # One mesh with independent per-aircraft displacements. Distant lamps are
    # spherical octahedra, not billboard sprites or an animated plate.
    verts=[];ends=[];faces=[];indices=[]
    duration=(frames-1)/24
    def cube(center,dims,delta,mat):
        offset=len(verts);x,y,z=[v/2 for v in dims]
        corners=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
        for v in corners:
            p=Vector(center)+Vector(v);verts.append(tuple(p));ends.append(tuple(p+Vector(delta)))
        for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]:
            faces.append(tuple(offset+i for i in f));indices.append(mat)
    for i in range(2200):
        u=rng.uniform(-1.5,1.5)
        x=u*105;y=112+27*math.sin(u*1.8)+rng.gauss(0,9)
        z=52+10*math.sin(u*2.1)+rng.gauss(0,3.3)
        speed=rng.uniform(.55,.95)
        delta=(speed*duration,.10*duration,rng.uniform(-.025,.06)*duration)
        cube((x,y,z),(.48,.70,.16),delta,0)
        cube((x,y,z),(.94,.07,.05),delta,0)
        for side in [-1,1]:
            for fore in [-1,1]:
                # Four actual rotor hubs, plus a white belly navigation lamp.
                cube((x+side*.43,y+fore*.30,z+.02),(.20,.20,.035),delta,0)
        cube((x,y,z-.12),(.18,.18,.12),delta,1)
        if i%4==0:cube((x-.44,y,z),(.12,.12,.08),delta,2)
    mesh=bpy.data.meshes.new('2200 airborne aircraft');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new('Independently migrating drone river',mesh);scene.collection.objects.link(obj)
    for mat in [material('Airframe dark polymer',(.025,.029,.032),.2,.7),
                material('Warm white navigation lamps',(.70,.74,.68),0,.4,8),
                material('Port navigation red',(.42,.012,.006),0,.4,4)]:mesh.materials.append(mat)
    for poly,mat in zip(mesh.polygons,indices):poly.material_index=mat
    obj.shape_key_add(name='Basis');key=obj.shape_key_add(name='Independent flight displacements')
    for point,position in zip(key.data,ends):point.co=position
    key.value=0;key.keyframe_insert('value',frame=1)
    key.value=1;key.keyframe_insert('value',frame=frames)
    obj['aircraft_count']=2200;obj['seed']=80314
    obj['method']='Independent 3D trajectories; no photographic image plane'
    world=scene.world;world.use_nodes=True;nodes=world.node_tree.nodes
    background=nodes.get('Background');background.inputs['Strength'].default_value=.5
    tex=nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=6;tex.inputs['Detail'].default_value=3
    coord=nodes.new('ShaderNodeTexCoord');world.node_tree.links.new(coord.outputs['Normal'],tex.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.0015,.0025,.0045,1)
    ramp.color_ramp.elements[1].color=(.014,.019,.024,1)
    world.node_tree.links.new(tex.outputs['Fac'],ramp.inputs[0]);world.node_tree.links.new(ramp.outputs['Color'],background.inputs['Color'])
    scene.use_nodes=True;tree=scene.node_tree;tree.nodes.clear()
    layers=tree.nodes.new('CompositorNodeRLayers');glow=tree.nodes.new('CompositorNodeGlare')
    glow.glare_type='FOG_GLOW';glow.quality='HIGH';glow.threshold=1.5;glow.size=6;glow.mix=-.94
    output=tree.nodes.new('CompositorNodeComposite');tree.links.new(layers.outputs['Image'],glow.inputs['Image']);tree.links.new(glow.outputs['Image'],output.inputs['Image'])
    return target


def clock(scene,camera,frames):
    wall=textured_metal('B4 painted wall',(.075,.068,.060),.78)
    box('Wall',(0,.25,2.1),(8,.18,5),wall)
    shell=textured_metal('Clock brushed casing',(.043,.041,.036),.4)
    box('Wall clock',(0,0,2.2),(1.60,.19,.49),shell,.025)
    box('Dark smoked face',(0,-.105,2.2),(1.49,.014,.39),material('Smoked face',(.003,.003,.003),.1,.24),.015)
    glow=material('Red emergency clock LEDs',(.42,.018,.008),0,.4,3.5)
    off=material('Inactive LED segments',(.018,.005,.003),0,.6)
    # Physical seven-segment bars. No typeface substitution or text texture.
    digits={'0':'abcdef','4':'bcfg','7':'abc'}
    for k,digit in enumerate('0447'):
        cx=-.52+k*.345;cz=2.2;w=.19;h=.245;th=.025
        segments={'a':(0,h/2,w,th),'g':(0,0,w,th),'d':(0,-h/2,w,th),
                  'f':(-w/2,h/4,th,h/2),'b':(w/2,h/4,th,h/2),
                  'e':(-w/2,-h/4,th,h/2),'c':(w/2,-h/4,th,h/2)}
        for name,(x,z,sx,sz) in segments.items():
            box('Clock '+str(k)+' segment '+name,(cx+x,-.12,cz+z),(sx,.007,sz),glow if name in digits[digit] else off,.003)
    for z in [2.16,2.24]:box('Fixed colon',(0,-.122,z),(.024,.009,.024),glow,.004)
    light('Emergency red practical',(-2,-1,3.1),(0,0,2.1),38,(1,.035,.012),1)
    light('Display spill',(0,-.35,2.2),(0,.25,2.2),2,(1,.04,.015),.7)
    camera.location=(.36,-3.1,1.95);camera.data.lens=62;camera.data.dof.aperture_fstop=8
    scene['clock_time']='04:47';scene['time_conflict_explanation']='NONE'
    return (0,-.10,2.2)
