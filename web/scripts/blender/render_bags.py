"""
Calyx Containers – Blender Bag Renderer
========================================
Generates 3D renders of packaging bags for the quoting configurator.

Usage:
  blender --background --python render_bags.py

Outputs transparent PNGs to ../../public/bag-renders/
Naming: {shape}_{substrate}_{finish}.png
  e.g.  standup-kseal_metallic_matte.png
"""

import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector

# ── Output config ─────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "public", "bag-renders"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

RENDER_WIDTH = 800
RENDER_HEIGHT = 1000
SAMPLES = 64

# ── Bag shape definitions ─────────────────────────────────────
BAG_SHAPES = {
    "standup-kseal": {
        "label": "Stand Up Pouch (K Seal)",
        "width": 0.12,
        "height": 0.18,
        "depth": 0.04,
        "gusset": "k_seal",
    },
    "standup-plow": {
        "label": "Stand Up Pouch (Plow Bottom)",
        "width": 0.12,
        "height": 0.18,
        "depth": 0.04,
        "gusset": "plow",
    },
    "flat-3side": {
        "label": "3 Side Seal",
        "width": 0.12,
        "height": 0.18,
        "depth": 0.006,
        "gusset": "none",
    },
    "flat-2side": {
        "label": "2 Side Seal",
        "width": 0.12,
        "height": 0.18,
        "depth": 0.006,
        "gusset": "none",
    },
}

# ── Substrate materials ───────────────────────────────────────
SUBSTRATES = {
    "metallic": {
        "label": "Metallic",
        "base_color": (0.45, 0.45, 0.50, 1.0),
        "metallic": 0.9,
        "roughness": 0.3,
        "alpha": 1.0,
    },
    "white-metallic": {
        "label": "White Metallic",
        "base_color": (0.80, 0.80, 0.85, 1.0),
        "metallic": 0.55,
        "roughness": 0.3,
        "alpha": 1.0,
    },
    "clear-highbarrier": {
        "label": "Clear (High Barrier)",
        "base_color": (0.92, 0.95, 0.97, 0.3),
        "metallic": 0.0,
        "roughness": 0.1,
        "alpha": 0.3,
    },
    "clear-standard": {
        "label": "Standard Clear",
        "base_color": (0.90, 0.94, 1.0, 0.18),
        "metallic": 0.0,
        "roughness": 0.05,
        "alpha": 0.18,
    },
}

# ── Finish modifiers ──────────────────────────────────────────
FINISHES = {
    "matte": {
        "label": "Matte",
        "roughness": 0.65,
        "clearcoat": 0.0,
    },
    "soft-touch": {
        "label": "Soft Touch",
        "roughness": 0.82,
        "clearcoat": 0.0,
    },
    "gloss": {
        "label": "Gloss",
        "roughness": 0.05,
        "clearcoat": 0.8,
    },
}


# ── Utility functions ─────────────────────────────────────────

def clean_scene():
    """Remove all objects, materials, etc."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.cameras:
        bpy.data.cameras.remove(block)
    for block in bpy.data.lights:
        bpy.data.lights.remove(block)


def setup_render_settings():
    """Configure Cycles render settings."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x = RENDER_WIDTH
    scene.render.resolution_y = RENDER_HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'


def setup_world():
    """Add a subtle environment for metallic reflections (hidden from camera)."""
    world = bpy.data.worlds.new("StudioEnv")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    # Clear default nodes
    for node in nodes:
        nodes.remove(node)

    # Build: gradient background visible only to glossy/reflection rays
    output = nodes.new('ShaderNodeOutputWorld')
    output.location = (600, 0)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = (400, 0)
    links.new(mix.outputs['Shader'], output.inputs['Surface'])

    # Camera ray → transparent (keeps film_transparent working)
    light_path = nodes.new('ShaderNodeLightPath')
    light_path.location = (0, 200)
    links.new(light_path.outputs['Is Camera Ray'], mix.inputs['Fac'])

    # Transparent for camera
    transparent = nodes.new('ShaderNodeBackground')
    transparent.location = (200, 100)
    transparent.inputs['Color'].default_value = (0, 0, 0, 1)
    transparent.inputs['Strength'].default_value = 0.0
    links.new(transparent.outputs['Background'], mix.inputs[1])

    # Gradient for reflections — soft grey studio
    bg = nodes.new('ShaderNodeBackground')
    bg.location = (200, -100)
    bg.inputs['Color'].default_value = (0.35, 0.37, 0.40, 1.0)
    bg.inputs['Strength'].default_value = 1.0
    links.new(bg.outputs['Background'], mix.inputs[2])


def setup_lighting():
    """3-point studio lighting — tuned for packaging photography."""
    # Key light — large soft area light, upper right
    key_data = bpy.data.lights.new(name="Key", type='AREA')
    key_data.energy = 80  # toned down from 150
    key_data.size = 0.6
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new("Key", key_data)
    bpy.context.collection.objects.link(key_obj)
    key_obj.location = (0.3, -0.4, 0.45)
    key_obj.rotation_euler = (math.radians(50), math.radians(15), math.radians(-10))

    # Fill light — large, soft, from the left (lower energy to maintain contrast)
    fill_data = bpy.data.lights.new(name="Fill", type='AREA')
    fill_data.energy = 35
    fill_data.size = 1.0
    fill_data.color = (0.95, 0.97, 1.0)
    fill_obj = bpy.data.objects.new("Fill", fill_data)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.location = (-0.4, -0.3, 0.3)
    fill_obj.rotation_euler = (math.radians(55), math.radians(-25), math.radians(15))

    # Rim/back light — edge definition from behind
    rim_data = bpy.data.lights.new(name="Rim", type='AREA')
    rim_data.energy = 50
    rim_data.size = 0.35
    rim_data.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new("Rim", rim_data)
    bpy.context.collection.objects.link(rim_obj)
    rim_obj.location = (0.1, 0.35, 0.35)
    rim_obj.rotation_euler = (math.radians(130), 0, math.radians(5))

    # Bottom fill — gentle upward light so the bottom isn't pure black
    bounce_data = bpy.data.lights.new(name="Bounce", type='AREA')
    bounce_data.energy = 15
    bounce_data.size = 0.5
    bounce_data.color = (1.0, 1.0, 1.0)
    bounce_obj = bpy.data.objects.new("Bounce", bounce_data)
    bpy.context.collection.objects.link(bounce_obj)
    bounce_obj.location = (0.0, -0.2, -0.05)
    bounce_obj.rotation_euler = (math.radians(-70), 0, 0)


def setup_camera(shape_config):
    """Position camera to frame the bag properly."""
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = 'PERSP'
    cam_data.lens = 85  # portrait lens
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    h = shape_config["height"]
    bag_center_z = h / 2

    # Camera distance depends on bag height — pulled well back
    cam_dist = h * 2.8
    cam_height = bag_center_z + h * 0.1  # slightly above center
    cam_x = h * 0.15  # slight offset right for 3/4 view

    cam_obj.location = (cam_x, -cam_dist, cam_height)

    # Look at bag center
    target = Vector((0.0, 0.0, bag_center_z))
    direction = target - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    return cam_obj


def create_material(name, substrate, finish):
    """Create a Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    bsdf.inputs['Base Color'].default_value = substrate["base_color"]
    bsdf.inputs['Metallic'].default_value = substrate["metallic"]
    bsdf.inputs['Roughness'].default_value = finish["roughness"]

    if substrate["alpha"] < 1.0:
        bsdf.inputs['Alpha'].default_value = substrate["alpha"]
        bsdf.inputs['Transmission Weight'].default_value = 1.0 - substrate["alpha"]
        bsdf.inputs['IOR'].default_value = 1.45
        mat.blend_method = 'BLEND'

    if finish.get("clearcoat", 0) > 0:
        bsdf.inputs['Coat Weight'].default_value = finish["clearcoat"]
        bsdf.inputs['Coat Roughness'].default_value = 0.02

    if substrate["metallic"] > 0.3:
        bsdf.inputs['Specular IOR Level'].default_value = 0.6

    return mat


def create_standup_pouch(shape_config):
    """
    Create a stand-up pouch with realistic shape.
    Uses a dense mesh with controlled edge loops to get a pouch shape
    that holds up without excessive subdivision.
    """
    w = shape_config["width"] / 2
    h = shape_config["height"]
    d = shape_config["depth"] / 2
    gusset = shape_config["gusset"]

    bm = bmesh.new()

    if gusset in ("k_seal", "plow"):
        # Stand-up pouch — has bottom gusset and slight belly bulge
        # Build profile with multiple edge loops for shape control

        corner_cut = min(d * 0.6, 0.012)  # 45-degree seal at bottom corners
        gusset_h = 0.025  # height where gusset transitions to flat face

        # Number of vertical subdivisions for smooth curvature
        n_rows = 8
        n_cols = 6  # horizontal subdivisions

        verts_grid_front = []
        verts_grid_back = []

        for row in range(n_rows + 1):
            t = row / n_rows  # 0 at bottom, 1 at top
            z = t * h

            # Bulge profile: slight outward curve in the middle
            # Max bulge at ~40% height, tapering to zero at top and bottom
            bulge_factor = math.sin(t * math.pi) * 0.4  # peaks at 50%
            # More bulge in lower half (bag has product settling)
            if t < 0.5:
                bulge_factor *= 1.3

            current_d = d * (1.0 + bulge_factor * 0.3)

            # Width narrows very slightly at bottom due to gusset fold
            if t < gusset_h / h:
                # In the gusset zone — width reduces at very bottom
                gusset_t = t / (gusset_h / h)
                width_factor = 0.92 + 0.08 * gusset_t
            else:
                width_factor = 1.0

            current_w = w * width_factor

            row_front = []
            row_back = []
            for col in range(n_cols + 1):
                s = col / n_cols  # 0 at left, 1 at right
                x = -current_w + 2 * current_w * s

                # Slight horizontal curvature — bag face isn't perfectly flat
                face_curve = math.sin(s * math.pi) * current_d * 0.15
                y_front = -current_d - face_curve
                y_back = current_d + face_curve

                row_front.append(bm.verts.new((x, y_front, z)))
                row_back.append(bm.verts.new((x, y_back, z)))

            verts_grid_front.append(row_front)
            verts_grid_back.append(row_back)

        # Create faces from grid — front
        for row in range(n_rows):
            for col in range(n_cols):
                v1 = verts_grid_front[row][col]
                v2 = verts_grid_front[row][col + 1]
                v3 = verts_grid_front[row + 1][col + 1]
                v4 = verts_grid_front[row + 1][col]
                bm.faces.new([v1, v2, v3, v4])

        # Create faces from grid — back (reversed winding)
        for row in range(n_rows):
            for col in range(n_cols):
                v1 = verts_grid_back[row][col]
                v2 = verts_grid_back[row][col + 1]
                v3 = verts_grid_back[row + 1][col + 1]
                v4 = verts_grid_back[row + 1][col]
                bm.faces.new([v4, v3, v2, v1])

        # Side panels — connect front and back at edges
        for row in range(n_rows):
            # Left side
            bm.faces.new([
                verts_grid_front[row][0],
                verts_grid_front[row + 1][0],
                verts_grid_back[row + 1][0],
                verts_grid_back[row][0],
            ])
            # Right side
            bm.faces.new([
                verts_grid_back[row][n_cols],
                verts_grid_back[row + 1][n_cols],
                verts_grid_front[row + 1][n_cols],
                verts_grid_front[row][n_cols],
            ])

        # Top edge — connect front top to back top
        bm.faces.new(
            [verts_grid_front[n_rows][col] for col in range(n_cols + 1)] +
            [verts_grid_back[n_rows][col] for col in range(n_cols, -1, -1)]
        )

        # Bottom — connect front bottom to back bottom (with 45-degree corners)
        bm.faces.new(
            [verts_grid_front[0][col] for col in range(n_cols, -1, -1)] +
            [verts_grid_back[0][col] for col in range(n_cols + 1)]
        )

    else:
        # Flat pouch — thin rectangular shape with very subtle curvature
        n_rows = 6
        n_cols = 4

        verts_grid_front = []
        verts_grid_back = []

        for row in range(n_rows + 1):
            t = row / n_rows
            z = t * h

            # Very subtle bulge for flat pouch (slight pillow effect)
            bulge = math.sin(t * math.pi) * 0.15
            current_d = d * (1.0 + bulge)

            row_front = []
            row_back = []
            for col in range(n_cols + 1):
                s = col / n_cols
                x = -w + 2 * w * s
                face_curve = math.sin(s * math.pi) * current_d * 0.1
                y_front = -current_d - face_curve
                y_back = current_d + face_curve
                row_front.append(bm.verts.new((x, y_front, z)))
                row_back.append(bm.verts.new((x, y_back, z)))

            verts_grid_front.append(row_front)
            verts_grid_back.append(row_back)

        # Faces — same as above
        for row in range(n_rows):
            for col in range(n_cols):
                v1 = verts_grid_front[row][col]
                v2 = verts_grid_front[row][col + 1]
                v3 = verts_grid_front[row + 1][col + 1]
                v4 = verts_grid_front[row + 1][col]
                bm.faces.new([v1, v2, v3, v4])

        for row in range(n_rows):
            for col in range(n_cols):
                v1 = verts_grid_back[row][col]
                v2 = verts_grid_back[row][col + 1]
                v3 = verts_grid_back[row + 1][col + 1]
                v4 = verts_grid_back[row + 1][col]
                bm.faces.new([v4, v3, v2, v1])

        for row in range(n_rows):
            bm.faces.new([
                verts_grid_front[row][0],
                verts_grid_front[row + 1][0],
                verts_grid_back[row + 1][0],
                verts_grid_back[row][0],
            ])
            bm.faces.new([
                verts_grid_back[row][n_cols],
                verts_grid_back[row + 1][n_cols],
                verts_grid_front[row + 1][n_cols],
                verts_grid_front[row][n_cols],
            ])

        bm.faces.new(
            [verts_grid_front[n_rows][col] for col in range(n_cols + 1)] +
            [verts_grid_back[n_rows][col] for col in range(n_cols, -1, -1)]
        )
        bm.faces.new(
            [verts_grid_front[0][col] for col in range(n_cols, -1, -1)] +
            [verts_grid_back[0][col] for col in range(n_cols + 1)]
        )

    mesh = bpy.data.meshes.new("Bag")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("Bag", mesh)
    bpy.context.collection.objects.link(obj)

    # Smooth shading
    for face in obj.data.polygons:
        face.use_smooth = True

    # Light subdivision — just enough to smooth without ballooning
    subsurf = obj.modifiers.new("Subsurf", 'SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 1

    return obj


def add_zipper_line(shape_config):
    """Add a subtle zipper ridge across the top of the bag."""
    w = shape_config["width"] / 2
    d = shape_config["depth"] / 2
    h = shape_config["height"]
    zipper_z = h * 0.88  # 88% up the bag

    bm = bmesh.new()
    strip_h = 0.003
    protrude = 0.0015  # how far it sticks out from the face

    # Front-facing zipper strip
    v1 = bm.verts.new((-w + 0.008, -d - protrude, zipper_z - strip_h))
    v2 = bm.verts.new((w - 0.008, -d - protrude, zipper_z - strip_h))
    v3 = bm.verts.new((w - 0.008, -d - protrude, zipper_z + strip_h))
    v4 = bm.verts.new((-w + 0.008, -d - protrude, zipper_z + strip_h))
    bm.faces.new([v1, v2, v3, v4])

    mesh = bpy.data.meshes.new("Zipper")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("Zipper", mesh)
    bpy.context.collection.objects.link(obj)

    mat = bpy.data.materials.new(name="ZipperMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.78, 0.78, 0.78, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.35
    bsdf.inputs['Metallic'].default_value = 0.15
    obj.data.materials.append(mat)

    # Give it some depth
    solidify = obj.modifiers.new("Solidify", 'SOLIDIFY')
    solidify.thickness = 0.0015
    solidify.offset = 0

    return obj


def add_tear_notch_marks(shape_config):
    """Add small V-shaped tear notch indicators on sides."""
    w = shape_config["width"] / 2
    d = shape_config["depth"] / 2
    h = shape_config["height"]
    notch_z = h * 0.83  # just below zipper
    notch_size = 0.004

    bm = bmesh.new()

    # Left notch
    v1 = bm.verts.new((-w - 0.001, 0, notch_z + notch_size))
    v2 = bm.verts.new((-w + notch_size * 1.2, 0, notch_z))
    v3 = bm.verts.new((-w - 0.001, 0, notch_z - notch_size))
    bm.faces.new([v1, v2, v3])

    # Right notch
    v4 = bm.verts.new((w + 0.001, 0, notch_z + notch_size))
    v5 = bm.verts.new((w - notch_size * 1.2, 0, notch_z))
    v6 = bm.verts.new((w + 0.001, 0, notch_z - notch_size))
    bm.faces.new([v6, v5, v4])

    mesh = bpy.data.meshes.new("TearNotch")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("TearNotch", mesh)
    bpy.context.collection.objects.link(obj)

    mat = bpy.data.materials.new(name="NotchMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.35, 0.35, 0.35, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.5
    obj.data.materials.append(mat)

    solidify = obj.modifiers.new("Solidify", 'SOLIDIFY')
    solidify.thickness = 0.001
    solidify.offset = 0

    return obj


def add_skirt_seal_band(shape_config):
    """Add K Seal skirt seal — a lighter band across the bottom."""
    if shape_config["gusset"] != "k_seal":
        return None

    w = shape_config["width"] / 2
    d = shape_config["depth"] / 2
    band_h = 0.01  # 10mm band
    band_bottom = 0.003  # slightly above absolute bottom

    bm = bmesh.new()

    # Front band
    v1 = bm.verts.new((-w + 0.005, -d - 0.0008, band_bottom))
    v2 = bm.verts.new((w - 0.005, -d - 0.0008, band_bottom))
    v3 = bm.verts.new((w - 0.005, -d - 0.0008, band_bottom + band_h))
    v4 = bm.verts.new((-w + 0.005, -d - 0.0008, band_bottom + band_h))
    bm.faces.new([v1, v2, v3, v4])

    mesh = bpy.data.meshes.new("SkirtSeal")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("SkirtSeal", mesh)
    bpy.context.collection.objects.link(obj)

    mat = bpy.data.materials.new(name="SkirtMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.82, 0.82, 0.84, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.5
    bsdf.inputs['Alpha'].default_value = 0.5
    mat.blend_method = 'BLEND'
    obj.data.materials.append(mat)

    solidify = obj.modifiers.new("Solidify", 'SOLIDIFY')
    solidify.thickness = 0.0005
    solidify.offset = 0

    return obj


def add_seal_edges(shape_config):
    """Add visible heat-seal edges (slightly different material along edges)."""
    w = shape_config["width"] / 2
    d = shape_config["depth"] / 2
    h = shape_config["height"]
    seal_w = 0.006  # 6mm seal width

    bm = bmesh.new()

    # Top seal — strip across the top of the front face
    v1 = bm.verts.new((-w, -d - 0.0005, h - seal_w))
    v2 = bm.verts.new((w, -d - 0.0005, h - seal_w))
    v3 = bm.verts.new((w, -d - 0.0005, h))
    v4 = bm.verts.new((-w, -d - 0.0005, h))
    bm.faces.new([v1, v2, v3, v4])

    # Left seal
    v5 = bm.verts.new((-w, -d - 0.0005, 0))
    v6 = bm.verts.new((-w + seal_w, -d - 0.0005, 0))
    v7 = bm.verts.new((-w + seal_w, -d - 0.0005, h))
    v8 = bm.verts.new((-w, -d - 0.0005, h))
    bm.faces.new([v5, v6, v7, v8])

    # Right seal
    v9 = bm.verts.new((w - seal_w, -d - 0.0005, 0))
    v10 = bm.verts.new((w, -d - 0.0005, 0))
    v11 = bm.verts.new((w, -d - 0.0005, h))
    v12 = bm.verts.new((w - seal_w, -d - 0.0005, h))
    bm.faces.new([v9, v10, v11, v12])

    mesh = bpy.data.meshes.new("SealEdges")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("SealEdges", mesh)
    bpy.context.collection.objects.link(obj)

    # Slightly different transparency to show seal edges
    mat = bpy.data.materials.new(name="SealMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.85, 0.85, 0.87, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.6
    bsdf.inputs['Alpha'].default_value = 0.2
    mat.blend_method = 'BLEND'
    obj.data.materials.append(mat)

    return obj


def add_ground_shadow_catcher():
    """Invisible ground plane that catches shadows."""
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, -0.001))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.is_shadow_catcher = True
    return ground


# ── Main render loop ──────────────────────────────────────────

def render_all():
    """Render all shape × substrate × finish combinations."""
    total = len(BAG_SHAPES) * len(SUBSTRATES) * len(FINISHES)
    count = 0

    for shape_key, shape_config in BAG_SHAPES.items():
        for substrate_key, substrate_config in SUBSTRATES.items():
            for finish_key, finish_config in FINISHES.items():
                count += 1
                filename = f"{shape_key}_{substrate_key}_{finish_key}.png"
                filepath = os.path.join(OUTPUT_DIR, filename)

                if os.path.exists(filepath):
                    print(f"[{count}/{total}] SKIP (exists): {filename}")
                    continue

                print(f"[{count}/{total}] Rendering: {filename}")
                print(f"  Shape: {shape_config['label']}")
                print(f"  Substrate: {substrate_config['label']}")
                print(f"  Finish: {finish_config['label']}")

                clean_scene()
                setup_render_settings()
                setup_world()
                setup_lighting()
                setup_camera(shape_config)
                add_ground_shadow_catcher()

                bag = create_standup_pouch(shape_config)
                mat = create_material(f"{substrate_key}_{finish_key}", substrate_config, finish_config)
                bag.data.materials.append(mat)

                add_zipper_line(shape_config)
                add_tear_notch_marks(shape_config)
                add_skirt_seal_band(shape_config)
                add_seal_edges(shape_config)

                bpy.context.scene.render.filepath = filepath
                bpy.ops.render.render(write_still=True)

                print(f"  ✓ Saved: {filepath}")
                print()

    print(f"\n{'='*50}")
    print(f"Done! Rendered {count} images to {OUTPUT_DIR}")
    print(f"{'='*50}")


if __name__ == "__main__":
    render_all()
