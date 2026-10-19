"""Bouwt de 3D-kamer in Blender, bakt camera, potlood, robotarm en pionnen uit build/timeline.json.

Draaien:  blender.exe -b -P room.py -- <videomap> [--preview] [--render] [--frames A-B] [--stills F,F,...]
Schrijft  <videomap>/build/scene.blend en rendert naar build/render/ (of build/render_preview/, of build/stills/).
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

SKILL = Path(__file__).resolve().parent.parent
D = json.loads((SKILL / "defaults.json").read_text(encoding="utf-8"))
argv = sys.argv[sys.argv.index("--") + 1:]
VDIR = Path(argv[0]).resolve()
PREVIEW = "--preview" in argv
RENDER = "--render" in argv
FRANGE = tuple(int(x) for x in argv[argv.index("--frames") + 1].split("-")) if "--frames" in argv else None
STILLS = [int(x) for x in argv[argv.index("--stills") + 1].split(",")] if "--stills" in argv else None
TL = json.loads((VDIR / "build" / "timeline.json").read_text(encoding="utf-8"))
BR = json.loads((VDIR / "brand.json").read_text(encoding="utf-8"))
FR = VDIR / "build" / "frames"
FPS, TOTAL = TL["fps"], TL["total_frames"]
W, H = TL["width"], TL["height"]
ASPECT = W / H
CAM = D["camera"]
STATIONS = {b["station"] for b in TL["beats"]}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, TOTAL


def hexrgb(h, default=(0.5, 0.5, 0.5)):
    if not h:
        return default
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ------------------------------------------------------------------ helpers
def mat(name, color=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = emit_strength
    return m


def wood(name, dark, light, scale, rough=0.45, axis="Z", distortion=9.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = axis
    wv.inputs["Scale"].default_value = 3.0
    wv.inputs["Distortion"].default_value = distortion
    wv.inputs["Detail"].default_value = 3.0
    wv.inputs["Detail Scale"].default_value = 1.6
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 40.0
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*dark, 1)
    cr.color_ramp.elements[1].color = (*light, 1)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.inputs[0].default_value = 0.25
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(wv.outputs["Fac"], mix.inputs[2])
    nt.links.new(nz.outputs["Fac"], mix.inputs[3])
    nt.links.new(mix.outputs[0], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], p.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.12
    rr.inputs["To Max"].default_value = rough + 0.12
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], p.inputs["Roughness"])
    return m


def box(name, size, loc, material=None, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = o.modifiers.new("bev", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "ANGLE"
        bpy.ops.object.shade_smooth()
    if material:
        o.data.materials.append(material)
    return o


def cyl(name, r, depth, loc, material=None, rot=(0, 0, 0), verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.object
    o.name = name
    if material:
        o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o


def sphere(name, r, loc, material):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o


def rr_points(w, h, r, seg=12):
    if r <= 0:
        return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def plane(name, w, h, radius, material):
    """Plat vlak met ronde hoeken, UV 0..1 over de volle maat, normaal +Z."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new((x, y, 0)) for x, y in rr_points(w, h, radius)])
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x / w + 0.5, lp.vert.co.y / h + 0.5)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    return o


def slab(name, w, h, r, t, material):
    me = bpy.data.meshes.new(name)
    pts = rr_points(w, h, r)
    n = len(pts)
    verts = [(x, y, 0) for x, y in pts] + [(x, y, -t) for x, y in pts]
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    return o


def empty(name, loc=(0, 0, 0), rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location, o.rotation_euler = loc, rot
    return o


def seq_mat(name, folder, strength=1.0, emissive=True, rough=0.3, spec=0.25):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    first = FR / folder / "0001.jpg"
    if not first.exists():  # station zonder beats: neutraal scherm
        p.inputs["Base Color"].default_value = (0.006, 0.006, 0.008, 1) if emissive else (0.92, 0.92, 0.9, 1)
        p.inputs["Roughness"].default_value = 0.3 if emissive else 0.6
        return m
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(str(first))
    img.source = "SEQUENCE"
    tex.image = img
    tex.image_user.frame_duration = TOTAL
    tex.image_user.frame_start = 1
    tex.image_user.use_auto_refresh = True
    tex.interpolation = "Cubic"
    if emissive:
        p.inputs["Base Color"].default_value = (0.004, 0.004, 0.005, 1)
        nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = strength
        p.inputs["Specular IOR Level"].default_value = spec
    else:
        nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Specular IOR Level"].default_value = 0.15
    p.inputs["Roughness"].default_value = rough
    return m


def image_mat(name, path, emit=0.12):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(str(path))
    nt.links.new(tx.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(tx.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = emit
    p.inputs["Roughness"].default_value = 0.35
    return m


# ------------------------------------------------------------------ materials
ROOM = BR.get("room", {})
WALLS = {
    "walnut": ((0.03, 0.014, 0.008), (0.11, 0.055, 0.028)),
    "oak": ((0.16, 0.1, 0.055), (0.38, 0.25, 0.14)),
    "dark": ((0.012, 0.012, 0.014), (0.04, 0.04, 0.045)),
}
wd, wl = WALLS.get(ROOM.get("wall", "walnut"), WALLS["walnut"])
M_WALL = wood("wall", wd, wl, (4, 4, 0.35), rough=0.55)
M_FLOOR = wood("floor", (0.05, 0.03, 0.018), (0.14, 0.085, 0.05), (0.6, 6, 1), rough=0.35, axis="X")
M_DESK = wood("desk", (0.035, 0.018, 0.01), (0.1, 0.055, 0.03), (1.2, 22, 6), rough=0.3, axis="X", distortion=2.5)
M_BLACK = mat("black_metal", (0.015, 0.015, 0.016), 0.35, 1.0)
M_ALU = mat("aluminium", (0.42, 0.43, 0.45), 0.32, 1.0)
M_STAND = mat("stand", (0.16, 0.16, 0.17), 0.35, 1.0)
M_BEZEL = mat("bezel", (0.004, 0.004, 0.004), 0.1)
M_DEVICE = mat("device_black", (0.006, 0.006, 0.007), 0.55)
M_KEY = mat("keys", (0.85, 0.85, 0.86), 0.45)
M_RUG = mat("rug", (0.05, 0.048, 0.045), 0.95)
M_CEIL = mat("ceiling", (0.02, 0.02, 0.02), 0.9)
led = hexrgb(ROOM.get("led"), (1.0, 0.62, 0.32))
M_LED = mat("led", led, 0.5, emit=led, emit_strength=18)
M_POT = mat("pot", (0.75, 0.72, 0.66), 0.6)
M_LEAF = mat("leaf", (0.05, 0.16, 0.05), 0.5)
M_MUG = mat("mug", (0.9, 0.9, 0.88), 0.25)
M_COFFEE = mat("coffee", (0.05, 0.025, 0.01), 0.15)
M_PAPER = mat("paper", (0.9, 0.89, 0.85), 0.8)
M_SCR_MON = seq_mat("scr_monitor", "monitor", 0.9, rough=0.3)
M_SCR_PHONE = seq_mat("scr_phone", "phone", 1.0, rough=0.5, spec=0.0)
M_SCR_BOARD = seq_mat("scr_board", "board", emissive=False, rough=0.6)
ACCENT = hexrgb((BR.get("colors") or {}).get("accent"), (0.9, 0.3, 0.01))

# ------------------------------------------------------------------ room
WALL_Y = 3.0
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.5, 0))
fl = bpy.context.object
fl.scale = (14, 10, 1)
fl.data.materials.append(M_FLOOR)
box("wall_back", (14, 0.05, 3.4), (0, WALL_Y + 0.05, 1.7), M_BLACK)
box("ceiling", (14, 10, 0.05), (0, 0.5, 3.3), M_CEIL)
sl = box("slat", (0.034, 0.035, 3.3), (-6.5, WALL_Y - 0.02, 1.65), M_WALL, bevel=0.004)
arr = sl.modifiers.new("arr", "ARRAY")
arr.count = 236
arr.relative_offset_displace = (1.62, 0, 0)
sl.modifiers.move(1, 0)
box("cove", (14, 0.12, 0.04), (0, WALL_Y - 0.1, 3.0), M_BLACK)
box("led_strip", (14, 0.02, 0.01), (0, WALL_Y - 0.06, 2.975), M_LED)
box("led_floor", (14, 0.02, 0.01), (0, WALL_Y - 0.06, 0.02), M_LED)
box("rug", (3.2, 2.0, 0.01), (0, 1.9, 0.005), M_RUG, bevel=0.004)

# desk + monitor
DESK = Vector((0, 2.35, 0.74))
box("desk_top", (1.7, 0.78, 0.04), (DESK.x, DESK.y, DESK.z - 0.02), M_DESK, bevel=0.006)
for sx in (-0.78, 0.78):
    box("desk_leg", (0.04, 0.68, 0.03), (sx, DESK.y, 0.015), M_BLACK)
    box("desk_leg", (0.04, 0.03, 0.72), (sx, DESK.y, 0.36), M_BLACK)
MON_W, MON_H = 0.62, 0.349
MON_C = Vector((0, 2.5, 1.08))
box("mon_body", (MON_W + 0.026, 0.022, MON_H + 0.026), (MON_C.x, MON_C.y + 0.012, MON_C.z), M_ALU, bevel=0.006)
box("mon_bezel", (MON_W + 0.016, 0.004, MON_H + 0.016), (MON_C.x, MON_C.y - 0.0005, MON_C.z), M_BEZEL, bevel=0.003)
ms = plane("mon_screen", MON_W, MON_H, 0.0, M_SCR_MON)
ms.location = (MON_C.x, MON_C.y - 0.003, MON_C.z)
ms.rotation_euler = (math.radians(90), 0, 0)
box("mon_stand", (0.12, 0.01, 0.33), (0, MON_C.y + 0.06, 0.9), M_STAND, bevel=0.003, rot=(math.radians(-12), 0, 0))
box("mon_foot", (0.12, 0.17, 0.008), (0, MON_C.y + 0.05, DESK.z + 0.004), M_STAND, bevel=0.003)
KB = Vector((-0.06, 2.12, DESK.z))
box("kb_body", (0.28, 0.115, 0.008), (KB.x, KB.y, KB.z + 0.004), M_ALU, bevel=0.003)
key = box("key", (0.0155, 0.0155, 0.004), (KB.x - 0.128, KB.y - 0.044, KB.z + 0.009), M_KEY, bevel=0.0015)
a1 = key.modifiers.new("ax", "ARRAY"); a1.count = 15; a1.relative_offset_displace = (1.15, 0, 0)
a2 = key.modifiers.new("ay", "ARRAY"); a2.count = 5; a2.relative_offset_displace = (0, 1.15, 0)
key.modifiers.move(2, 0); key.modifiers.move(2, 0)
box("trackpad", (0.15, 0.11, 0.006), (KB.x + 0.24, KB.y, KB.z + 0.003), M_KEY, bevel=0.003)

# phone op standaard
PH_W, PH_H, PH_R = 0.0715, 0.1545, 0.0105
PH_BASE = Vector((0.47, 2.2, DESK.z))
box("stand_base", (0.085, 0.08, 0.007), (PH_BASE.x, PH_BASE.y + 0.02, DESK.z + 0.0035), M_STAND, bevel=0.002)
box("stand_lip", (0.085, 0.012, 0.016), (PH_BASE.x, PH_BASE.y - 0.012, DESK.z + 0.012), M_STAND, bevel=0.002)
box("stand_back", (0.05, 0.007, 0.12), (PH_BASE.x, PH_BASE.y + 0.032, DESK.z + 0.065), M_STAND, bevel=0.002, rot=(math.radians(-14), 0, 0))
phone_root = empty("phone_root", (PH_BASE.x, PH_BASE.y, DESK.z + 0.012), (math.radians(76), 0, 0))
pb = slab("phone_body", PH_W, PH_H, PH_R, 0.0078, M_DEVICE)
pb.parent = phone_root
pb.location = (0, PH_H / 2, 0)
ps = plane("phone_screen", PH_W - 0.0032, PH_H - 0.0032, PH_R - 0.0016, M_SCR_PHONE)
ps.parent = phone_root
ps.location = (0, PH_H / 2, 0.0004)
bpy.context.view_layer.update()
PHONE_C = phone_root.matrix_world @ Vector((0, PH_H / 2, 0))
PHONE_N = (phone_root.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()

# plant + mok
cyl("pot", 0.07, 0.15, (0.68, 2.55, DESK.z + 0.075), M_POT)
random.seed(4)
for i in range(16):
    lf = sphere("leaf", 0.06, (0.68 + random.uniform(-0.09, 0.09), 2.55 + random.uniform(-0.08, 0.08), DESK.z + 0.2 + random.uniform(0, 0.17)), M_LEAF)
    lf.scale = (1, 0.18, 0.55)
    lf.rotation_euler = (random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), random.uniform(0, 3.1))
cyl("mug", 0.04, 0.095, (-0.55, 2.2, DESK.z + 0.0475), M_MUG)
cyl("coffee", 0.036, 0.004, (-0.55, 2.2, DESK.z + 0.085), M_COFFEE)

# whiteboard op ezel + potlood
BOARD_C = Vector((-2.0, 2.25, 1.45))
BW, BH = 0.75, 1.0
TILT = math.radians(8)
board = empty("board_root", BOARD_C, (math.radians(90) - TILT, 0, 0))
bs = plane("board_surface", BW, BH, 0.0, M_SCR_BOARD)
bs.parent = board
for (w, h, x, y) in ((BW + 0.04, 0.02, 0, BH / 2 + 0.01), (BW + 0.04, 0.02, 0, -BH / 2 - 0.01), (0.02, BH, BW / 2 + 0.01, 0), (0.02, BH, -BW / 2 - 0.01, 0)):
    b = box("board_frame", (w, h, 0.02), (0, 0, 0), M_ALU, bevel=0.003)
    b.parent = board
    b.location = (x, y, -0.005)
bk = box("board_back", (BW, BH, 0.012), (0, 0, 0), M_PAPER)
bk.parent = board
bk.location = (0, 0, -0.008)
bpy.context.view_layer.update()
BOARD_N = (board.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
M_EASEL = wood("easel", (0.12, 0.07, 0.035), (0.3, 0.18, 0.09), (1, 1, 6))
bottom = BOARD_C.z - BH / 2 * math.cos(TILT)
for sx in (-0.3, 0.3):
    box("easel_leg", (0.035, 0.025, 2.0), (BOARD_C.x + sx * 1.15, BOARD_C.y + 0.02, 1.0), M_EASEL, bevel=0.003, rot=(math.radians(-6), math.radians(-7 if sx > 0 else 7), 0))
box("easel_back", (0.035, 0.025, 1.95), (BOARD_C.x, BOARD_C.y + 0.42, 0.97), M_EASEL, bevel=0.003, rot=(math.radians(14), 0, 0))
box("easel_ledge", (0.86, 0.07, 0.025), (BOARD_C.x, BOARD_C.y - 0.04, bottom - 0.02), M_EASEL, bevel=0.003)
pencil = empty("pencil")
pencil.parent = board
L = 0.17
parts = [cyl("pencil_body", 0.0045, L, (0, 0, 0.012 + L / 2), mat("pencil", (0.95, 0.62, 0.08), 0.35), verts=6)]
bpy.ops.mesh.primitive_cone_add(radius1=0.0045, radius2=0.0008, depth=0.016, location=(0, 0, 0.008), rotation=(math.pi, 0, 0), vertices=6)
parts.append(bpy.context.object); parts[-1].data.materials.append(mat("pencil_wood", (0.8, 0.62, 0.42), 0.6))
bpy.ops.mesh.primitive_cone_add(radius1=0.0012, radius2=0.0, depth=0.003, location=(0, 0, 0.0012), rotation=(math.pi, 0, 0), vertices=8)
parts.append(bpy.context.object); parts[-1].data.materials.append(mat("graphite", (0.05, 0.05, 0.05), 0.3, 0.6))
parts.append(cyl("eraser", 0.0046, 0.014, (0, 0, 0.012 + L + 0.007), mat("eraser", (0.85, 0.42, 0.4), 0.7)))
for o in parts:
    o.parent = pencil
pencil_rot = Vector((0, 0, 1)).rotation_difference(Vector((0.42, -0.5, 0.76)).normalized()).to_euler()

# zijtafel
TAB_T = Vector((2.0, 1.95, 0.72))
box("table_top", (0.95, 0.62, 0.035), (TAB_T.x, TAB_T.y, TAB_T.z - 0.0175), M_DESK, bevel=0.005)
for sx in (-0.42, 0.42):
    for sy in (-0.26, 0.26):
        box("table_leg", (0.035, 0.035, 0.7), (TAB_T.x + sx, TAB_T.y + sy, 0.35), M_BLACK)
cyl("mug2", 0.04, 0.095, (2.38, 2.15, TAB_T.z + 0.0475), M_MUG)
box("notebook", (0.15, 0.21, 0.012), (1.62, 2.05, TAB_T.z + 0.006), mat("notebook", (0.06, 0.25, 0.2), 0.7), bevel=0.002, rot=(0, 0, math.radians(12)))

# vloerlamp
cyl("lamp_pole", 0.012, 1.6, (-2.75, 2.6, 0.8), M_BLACK)
cyl("lamp_base", 0.13, 0.02, (-2.75, 2.6, 0.01), M_BLACK)
cyl("lamp_shade", 0.17, 0.28, (-2.75, 2.6, 1.68), mat("shade", (0.9, 0.85, 0.75), 0.9, emit=(1, 0.75, 0.45), emit_strength=2.5))


# ------------------------------------------------------------------ table: bordjes, pionnen, robotarm
def ease(x):
    x = max(0.0, min(1.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def key_visible(objs, t_on, t_off):
    for o in objs:
        for (t, vis) in ((0, t_on <= 0), (t_on, True), (t_off, False)):
            f = max(1, int(round(t * FPS)) + 1)
            o.hide_render = not vis
            o.hide_viewport = not vis
            o.keyframe_insert("hide_render", frame=f)
            o.keyframe_insert("hide_viewport", frame=f)


all_table = [b for b in TL["beats"] if b["station"] == "table"]


def window(tb):
    """zichtbaar van de wissel van deze tafel-beat tot de wissel van de volgende"""
    k = all_table.index(tb)
    return tb["swap"], (all_table[k + 1]["swap"] if k + 1 < len(all_table) else 1e9)


# rommel op tafel: stapel facturen, enveloppen, schoenendoos (probleem-shot)
for tb in [b for b in all_table if b.get("clutter")]:
    cl = tb["clutter"]
    on, off = window(tb)
    rnd = random.Random(7)
    objs = []
    pm = [image_mat(f"paper_{i}", VDIR / "build" / "papers" / f"paper_{i}.png", emit=0.0) for i in range(6)
          if (VDIR / "build" / "papers" / f"paper_{i}.png").exists()] or [M_PAPER]
    for m in pm:
        m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
    for i in range(int(cl.get("papers", 14))):
        sh = plane("paper", 0.21, 0.297, 0.0, pm[i % len(pm)])
        sh.location = (1.9 + rnd.uniform(-0.17, 0.12), 1.96 + rnd.uniform(-0.08, 0.09), TAB_T.z + 0.0012 + i * 0.0011)
        sh.rotation_euler = (rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), rnd.uniform(-0.9, 0.9))
        objs.append(sh)
    M_ENV = mat("envelope", (0.93, 0.92, 0.88), 0.8)
    M_KRAFT = mat("kraft", (0.55, 0.4, 0.24), 0.85)
    for i in range(int(cl.get("envelopes", 5))):
        ev = box("envelope", (0.22, 0.11, 0.003), (1.85 + rnd.uniform(-0.2, 0.25), 1.86 + rnd.uniform(-0.06, 0.05), TAB_T.z + 0.02 + i * 0.004),
                 M_KRAFT if i % 2 else M_ENV, rot=(rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), rnd.uniform(-0.6, 0.6)))
        objs.append(ev)
    if cl.get("shoebox", True):
        M_BOX = mat("shoebox", (0.6, 0.45, 0.3), 0.8)
        bx, by, bw, bd, bh = 2.27, 2.1, 0.33, 0.2, 0.12
        rot = math.radians(-12)
        root = empty("shoebox_root", (bx, by, TAB_T.z), (0, 0, rot))
        for (sx, sy, sz, lx, ly, lz) in ((bw, bd, 0.004, 0, 0, 0.002), (bw, 0.004, bh, 0, -bd / 2, bh / 2), (bw, 0.004, bh, 0, bd / 2, bh / 2),
                                         (0.004, bd, bh, -bw / 2, 0, bh / 2), (0.004, bd, bh, bw / 2, 0, bh / 2)):
            w_ = box("box_wall", (sx, sy, sz), (0, 0, 0), M_BOX)
            w_.parent = root
            w_.location = (lx, ly, lz)
            objs.append(w_)
        for i in range(7):  # bonnetjes en facturen die uit de doos steken
            sh = plane("box_paper", 0.21, 0.297, 0.0, pm[(i + 2) % len(pm)])
            sh.parent = root
            sh.location = (-0.12 + i * 0.04, rnd.uniform(-0.03, 0.03), 0.1)
            sh.rotation_euler = (math.radians(rnd.uniform(70, 100)), 0, math.radians(90 + rnd.uniform(-12, 12)))
            objs.append(sh)
    key_visible(objs, on, off)

table_beats = [b for b in all_table if b.get("plaque")]
PL_W, PL_H, PL_D = 0.26, 0.115, 0.022
PQ = Vector((2.0, 2.03, TAB_T.z))
plaques = []
for k, tb in enumerate(table_beats):
    on, off = window(tb)
    root = empty(f"plaque_root_{k}")
    body = box("plaque_body", (PL_W, PL_D, PL_H), (0, 0, 0), mat("plaque_body", (0.02, 0.035, 0.06), 0.4), bevel=0.002)
    body.parent = root
    body.location = (0, 0, PL_H / 2)
    png = VDIR / "build" / "plaques" / f"plaque_{tb['i']}.png"
    face = plane("plaque_face", PL_W - 0.004, PL_H - 0.004, 0.0, image_mat("plaque_face", png) if png.exists() else M_PAPER)
    face.parent = root
    face.location = (0, -PL_D / 2 - 0.0006, PL_H / 2)
    face.rotation_euler = (math.radians(90), 0, 0)
    key_visible([body, face], on, off)
    plaques.append((root, tb))
for tb in all_table:
    on, off = window(tb)
    k = all_table.index(tb)
    pw = tb.get("pawns")
    if pw:
        n = int(pw.get("count", 10))
        sp = min(0.029, 0.29 / max(1, n - 1))
        objs, mats = [], []
        for i in range(n):
            m = mat(f"pawn_{k}_{i}", (0.85, 0.85, 0.83), 0.35)
            mats.append(m)
            x = 2.0 - sp * (n - 1) / 2 + i * sp
            y = 1.82 + 0.25 * (x - 2.0) ** 2
            objs.append(cyl("pawn_base", 0.0115, 0.007, (x, y, TAB_T.z + 0.0035), m))
            bpy.ops.mesh.primitive_cone_add(radius1=0.0098, radius2=0.005, depth=0.036, location=(x, y, TAB_T.z + 0.025), vertices=32)
            objs.append(bpy.context.object); objs[-1].data.materials.append(m); bpy.ops.object.shade_smooth()
            objs.append(sphere("pawn_head", 0.0095, (x, y, TAB_T.z + 0.049), m))
        key_visible(objs, on, off)
        for i, th in enumerate(tb["events"].get("highlight", [])):
            bsdf = mats[i].node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Emission Color"].default_value = (*ACCENT, 1)
            f_on = int(th * FPS) + 1
            for (fr, col, em) in ((f_on - 1, (0.85, 0.85, 0.83, 1), 0.0), (f_on + 3, (*ACCENT, 1), 0.35)):
                bsdf.inputs["Base Color"].default_value = col
                bsdf.inputs["Emission Strength"].default_value = em
                bsdf.inputs["Base Color"].keyframe_insert("default_value", frame=fr)
                bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=fr)

if table_beats:
    M_ROBOT = mat("robot", (0.82, 0.82, 0.84), 0.3)
    M_JOINT = mat("robot_joint", (0.03, 0.03, 0.035), 0.4, 0.5)
    ARM_B = Vector((2.0, 2.36, 2.15))
    L1, L2 = 0.75, 0.7
    cyl("arm_column", 0.045, 3.3 - ARM_B.z, (ARM_B.x, ARM_B.y, (3.3 + ARM_B.z) / 2), M_JOINT)
    sphere("arm_base", 0.07, ARM_B, M_JOINT)

    def link_obj(name, r, length):
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, vertices=32)
        o = bpy.context.object
        o.name = name
        for v in o.data.vertices:
            v.co.z += length / 2
        o.data.materials.append(M_ROBOT)
        bpy.ops.object.shade_smooth()
        return o

    arm_up, arm_lo = link_obj("arm_upper", 0.035, L1), link_obj("arm_lower", 0.028, L2)
    elbow = sphere("elbow", 0.05, (0, 0, 0), M_JOINT)
    wrist = empty("wrist")
    sphere("wrist_ball", 0.04, (0, 0, 0), M_JOINT).parent = wrist
    palm = box("gripper_palm", (0.07, 0.035, 0.03), (0, 0, 0), M_ROBOT, bevel=0.004)
    palm.parent = wrist
    palm.location = (0, 0, -0.045)
    fingers = []
    for sgn in (-1, 1):
        fg = box("gripper_finger", (0.008, 0.024, 0.05), (0, 0, 0), M_JOINT, bevel=0.002)
        fg.parent = wrist
        fingers.append((fg, sgn))
    GRIP = 0.1
    W_HOLD, W_UP = Vector((2.0, 2.12, 1.4)), Vector((2.0, 2.2, 1.62))
    W_PLACE = PQ + Vector((0, 0, PL_H + GRIP - 0.012))

    def arm_state(t):
        """(polspositie, vingers open 0..1, index bordje in de grijper of None)"""
        for k, tb in enumerate(table_beats):
            ev = tb["events"]
            nxt = table_beats[k + 1]["swap"] if k + 1 < len(table_beats) else 1e9
            if t < ev["down0"]:
                return W_HOLD if (k == 0 or t >= tb["swap"]) else W_UP, 0.0, k if (k == 0 or t >= tb["swap"]) else None
            if t < ev["down1"]:
                return W_HOLD.lerp(W_PLACE, ease((t - ev["down0"]) / (ev["down1"] - ev["down0"]))), 0.0, k
            if t < ev["release"]:
                return W_PLACE, 0.0, k
            if t < ev["up0"]:
                return W_PLACE, smooth((t - ev["release"]) / 0.15), None
            if t < nxt:
                return W_PLACE.lerp(W_UP, ease((t - ev["up0"]) / (ev["up1"] - ev["up0"]))), 1 - smooth((t - ev["up1"] - 0.2) / 0.3), None
        return W_UP, 0.0, None

    def aim(o, a, b, prev):
        o.location = a
        e = Vector((0, 0, 1)).rotation_difference((b - a).normalized()).to_euler()
        if prev is not None:
            e.make_compatible(prev)
        o.rotation_euler = e
        return e

    pu = pl = None
    for f in range(1, TOTAL + 1):
        t = (f - 1) / FPS
        Wp, op, carry = arm_state(t)
        d = Wp - ARM_B
        hz = Vector((d.x, d.y, 0))
        uh = hz.normalized() if hz.length > 1e-4 else Vector((0, -1, 0))
        Dd = min(d.length, L1 + L2 - 1e-4)
        a = math.atan2(d.z, hz.length)
        b = math.acos(max(-1, min(1, (L1 * L1 + Dd * Dd - L2 * L2) / (2 * L1 * Dd))))
        E = ARM_B + uh * (L1 * math.cos(a - b)) + Vector((0, 0, L1 * math.sin(a - b)))
        pu = aim(arm_up, ARM_B, E, pu)
        pl = aim(arm_lo, E, Wp, pl)
        elbow.location, wrist.location = E, Wp
        for o in (arm_up, arm_lo):
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("rotation_euler", frame=f)
        elbow.keyframe_insert("location", frame=f)
        wrist.keyframe_insert("location", frame=f)
        for fg, sgn in fingers:
            fg.location = (sgn * (0.03 + 0.012 * op), 0, -0.083)
            fg.keyframe_insert("location", frame=f)
        for k, (root, tb) in enumerate(plaques):
            if carry == k:
                root.location = Wp - Vector((0, 0, GRIP + PL_H - 0.012))
            elif t >= tb["events"]["release"]:
                root.location = PQ
            else:
                root.location = W_HOLD - Vector((0, 0, GRIP + PL_H - 0.012))
            root.keyframe_insert("location", frame=f)

# ------------------------------------------------------------------ lights + world
def light(name, kind, loc, energy, color=(1, 0.82, 0.62), size=0.5, rot=(0, 0, 0), spot=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy, ld.color = energy, color
    if kind == "AREA":
        ld.size = size
    if kind == "SPOT":
        ld.spot_size, ld.spot_blend, ld.shadow_soft_size = math.radians(spot), 0.6, 0.05
    o = bpy.data.objects.new(name, ld)
    o.location, o.rotation_euler = loc, rot
    bpy.context.collection.objects.link(o)


for x in (-2.0, -0.9, 0.9, 2.1):
    light("spot", "SPOT", (x, WALL_Y - 0.45, 3.15), 260, rot=(math.radians(-18), 0, 0), spot=55)
light("key_desk", "AREA", (0.6, 1.2, 2.2), 120, size=1.0, rot=(math.radians(40), math.radians(15), 0))
light("key_board", "AREA", (-1.4, 0.9, 2.1), 110, size=0.8, rot=(math.radians(45), math.radians(-20), 0))
light("key_table", "AREA", (2.3, 1.2, 2.0), 70, size=0.8, rot=(math.radians(30), math.radians(10), 0))
light("fill", "AREA", (0, -2.5, 1.6), 140, size=3.0, color=(0.75, 0.82, 1.0), rot=(math.radians(85), 0, 0))
light("lamp", "POINT", (-2.75, 2.6, 1.62), 60, color=(1, 0.7, 0.4))
w = bpy.data.worlds.new("world")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.01, 0.009, 1)
sc.world = w

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_d)
bpy.context.collection.objects.link(cam)
sc.camera = cam
cam_d.sensor_fit = "VERTICAL"
cam_d.sensor_height = 24
cam_d.dof.use_dof = True
cam_d.dof.aperture_fstop = CAM["fstop"]
cam_d.clip_start = 0.01
focus = empty("focus")
cam_d.dof.focus_object = focus
UP = Vector((0, 0, 1))
LENS = CAM["lens"]
VT = math.tan(math.atan(12 / LENS))          # tan(vfov/2)
HT = VT * ASPECT                              # tan(hfov/2)
CENTER = CAM["subject_center_9x16"] if ASPECT < 0.7 else CAM["subject_center_other"]


def mon_px(px, py):
    return Vector((MON_C.x - MON_W / 2 + px / 1600 * MON_W, MON_C.y - 0.003, MON_C.z + MON_H / 2 - py / 900 * MON_H))


SPLIT = False  # True: alleen de middelste helft van het beeld wordt gebruikt (talking head eronder)


def fit(center, w, h, normal, margin=None, lift=0.0):
    """Camera recht voor een vlak (w x h meter) zodat het past, met ruimte voor de ondertitel."""
    m = 1 + 2 * (CAM["margin"] if margin is None else margin)
    vt = VT / 2 if SPLIT else VT
    dist = max(h * m / 2 / vt, w * m / 2 / HT)
    tgt = center.copy()
    loc = center + normal * dist + Vector((0, 0, lift * dist))
    fh = 2 * dist * VT
    if h < 0.6 * fh and not SPLIT:  # onderwerp hoger in beeld zetten, ondertitel eronder
        f = (loc - tgt).normalized()
        r = f.cross(UP).normalized()
        u = r.cross(f)
        shift = fh * (0.5 - CENTER)
        tgt += u * shift
        loc += u * shift
    return dict(loc=loc, tgt=tgt, up=UP, lens=LENS)


def pose(station, zoom, split=False):
    global SPLIT
    SPLIT = split
    try:
        return _pose(station, zoom)
    finally:
        SPLIT = False


def _pose(station, zoom):
    if station == "wide":
        return dict(loc=Vector((0.2, -1.9, 1.62)), tgt=Vector((-0.6, 2.5, 1.2)), up=UP, lens=20)
    if station == "board":
        return fit(BOARD_C, BW, BH, BOARD_N, margin=0.1)
    if station == "monitor":
        if isinstance(zoom, dict) and "box" in zoom:
            x0, y0, x1, y1 = zoom["box"]
            return fit(mon_px((x0 + x1) / 2, (y0 + y1) / 2), (x1 - x0) / 1600 * MON_W, (y1 - y0) / 900 * MON_H, Vector((0, -1, 0)), margin=0.04, lift=0.01)
        return fit(MON_C, MON_W + 0.03, MON_H + 0.03, Vector((0, -1, 0)), lift=0.03)
    if station == "phone":
        return fit(PHONE_C, PH_W, PH_H, PHONE_N, margin=0.22, lift=0.05)
    if station == "table" and isinstance(zoom, dict) and "w" in zoom:  # bredere tafelshot (bijv. rommel)
        w_ = zoom["w"]
        return fit(Vector((2.05, 1.99, 0.77)), w_, w_ * 0.45, Vector((0, -0.9, 0.44)).normalized(), margin=0.08)
    if station == "table":
        # pionnen staan vooraan en lager: richtpunt laag zodat bordje + pionnen boven de ondertitel vallen
        return fit(Vector((2.0, 1.88, 0.735)), 0.36, 0.2, Vector((0, -0.94, 0.34)).normalized(), margin=0.1)
    raise ValueError(station)


def pushed(p, amount):
    q = dict(p)
    q["loc"] = p["tgt"] + (p["loc"] - p["tgt"]) * (1 - amount)
    return q


shots = TL["shots"]
keys = []  # (t0, t1, poseA, poseB, kind)
t_cursor = 0.0
prev_end_pose = pose("wide", None) if TL.get("establishing", True) else None
for k, sh in enumerate(shots):
    p0 = pose(sh["station"], sh["zoom"], sh.get("split", False))
    p1 = pushed(p0, CAM["hold_push"])
    same = k > 0 and shots[k - 1]["station"] == sh["station"]
    mv = CAM["zoom_move_s"] if same else CAM["move_s"]
    if k == 0:
        arrive = CAM["establishing_s"] if prev_end_pose else 0.0
        if prev_end_pose:
            keys.append((0.0, arrive, prev_end_pose, p0, "move"))
    else:
        a0 = max(t_cursor, sh["start"] - mv * 0.5)
        arrive = a0 + mv
        keys.append((a0, arrive, prev_end_pose, p0, "zoom" if same else "move"))
    depart = (shots[k + 1]["start"] - (CAM["zoom_move_s"] if shots[k + 1]["station"] == sh["station"] else CAM["move_s"]) * 0.5) if k + 1 < len(shots) else TL["duration"] + 0.1
    depart = max(depart, arrive + 0.2)
    keys.append((arrive, depart, p0, p1, "hold"))
    prev_end_pose = p1
    t_cursor = depart


def pose_at(t):
    for (a, b, A, B, kind) in keys:
        if a <= t <= b:
            break
    p = (t - a) / max(1e-6, b - a)
    e = (p * p * (3 - 2 * p) * 0.8 + p * 0.2) if kind == "hold" else ease(p)
    loc = A["loc"].lerp(B["loc"], e)
    tgt = A["tgt"].lerp(B["tgt"], e)
    up = A["up"].lerp(B["up"], e).normalized()
    lens = A["lens"] + (B["lens"] - A["lens"]) * e
    if kind == "move":
        lift = math.sin(math.pi * p)
        span = (B["tgt"] - A["tgt"]).length
        loc = loc + (loc - tgt).normalized() * (CAM["pullback"] * span) * lift + Vector((0, -0.25, 0.12)) * span * lift
    return loc, tgt, up, lens


def look(loc, tgt, up):
    f = (tgt - loc).normalized()
    r = f.cross(up).normalized()
    u = r.cross(f)
    return Matrix((r, u, -f)).transposed().to_euler()


prev = None
for f in range(1, TOTAL + 1):
    loc, tgt, up, lens = pose_at((f - 1) / FPS)
    eul = look(loc, tgt, up)
    if prev is not None:
        eul.make_compatible(prev)
    prev = eul
    cam.location, cam.rotation_euler, cam_d.lens, focus.location = loc, eul, lens, tgt
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)
    cam_d.keyframe_insert("lens", frame=f)
    focus.keyframe_insert("location", frame=f)

# potlood
penf = FR / "board_pen.json"
if penf.exists():
    pens = json.loads(penf.read_text(encoding="utf-8"))
    sx = sy = sz = None
    for f in range(1, TOTAL + 1):
        pe = pens.get(str(f)) or {"x": 60, "y": 300, "writing": 0}
        x, y = (pe["x"] / 900 - 0.5) * BW, (0.5 - pe["y"] / 1200) * BH
        z = 0.0015 if pe["writing"] else 0.02
        if sx is None:
            sx, sy, sz = x, y, z
        sx, sy, sz = sx + (x - sx) * 0.55, sy + (y - sy) * 0.55, sz + (z - sz) * 0.4
        pencil.location = (sx, sy, sz)
        pencil.keyframe_insert("location", frame=f)
pencil.rotation_euler = pencil_rot

# ------------------------------------------------------------------ render settings
r = sc.render
r.resolution_x, r.resolution_y = W, H
r.resolution_percentage = 50 if PREVIEW else 100
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
sub = "stills" if STILLS else ("render_preview" if PREVIEW else "render")
r.filepath = str(VDIR / "build" / sub / "f_")
sc.view_settings.view_transform = "Standard"
try:
    sc.view_settings.look = "Medium High Contrast"
except Exception:
    pass
sc.view_settings.exposure = D["render"]["exposure"]
r.engine = "BLENDER_EEVEE"
for k, v in (("use_raytracing", True), ("taa_render_samples", D["render"]["samples_preview"] if (PREVIEW or STILLS) else D["render"]["samples_final"]),
             ("use_shadows", True), ("use_fast_gi", True)):
    try:
        setattr(sc.eevee, k, v)
    except Exception as e:
        print("eevee skip", k, e)
r.use_motion_blur = True
r.motion_blur_shutter = D["render"]["motion_blur_shutter"]

bpy.ops.wm.save_as_mainfile(filepath=str(VDIR / "build" / "scene.blend"))
if STILLS:
    for f in STILLS:
        sc.frame_set(f)
        r.filepath = str(VDIR / "build" / "stills" / f"f_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
elif RENDER:
    if FRANGE:
        sc.frame_start, sc.frame_end = FRANGE
    bpy.ops.render.render(animation=True)
