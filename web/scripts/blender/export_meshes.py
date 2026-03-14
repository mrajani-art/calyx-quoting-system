"""
Calyx Containers – Blender Mesh Exporter
=========================================
Exports bag meshes as .glb files with proper UV mapping for texture/artwork.

Usage:
  blender --background --python export_meshes.py

Outputs .glb files to ../../public/models/
  standup-kseal.glb
  standup-plow.glb
  flat-3side.glb
  flat-2side.glb
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "public", "models"))
os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)


def create_standup_pouch(gusset_type="k_seal"):
    """
    Create a stand-up pouch mesh with proper UV mapping.
    The front face gets UVs suitable for artwork mapping.
    """
    w = 0.06    # half-width (12cm total)
    h = 0.18    # height
    d = 0.02    # half-depth (4cm total)

    bm = bmesh.new()

    if gusset_type in ("k_seal", "plow"):
        # Stand-up pouch with gusset bottom
        corner_cut = 0.01  # 45-degree seal at bottom
        gusset_h = 0.025   # gusset transition height

        n_rows = 10  # vertical resolution
        n_cols = 8   # horizontal resolution

        verts_front = []
        verts_back = []

        for row in range(n_rows + 1):
            t = row / n_rows
            z = t * h

            # Subtle belly bulge — more in lower-mid section (product settling)
            bulge = math.sin(t * math.pi) * 0.35
            if t < 0.5:
                bulge *= 1.2
            if t > 0.9:
                # Flatten near top (above zipper area)
                bulge *= 0.3
            current_d = d * (1.0 + bulge * 0.25)

            # Width pinches very slightly at bottom (gusset fold)
            if t < gusset_h / h:
                gt = t / (gusset_h / h)
                width_factor = 0.94 + 0.06 * gt
            else:
                width_factor = 1.0
            current_w = w * width_factor

            row_front = []
            row_back = []
            for col in range(n_cols + 1):
                s = col / n_cols
                x = -current_w + 2 * current_w * s

                # Horizontal curvature — slight pillow on front face
                face_curve = math.sin(s * math.pi) * current_d * 0.12
                y_front = -current_d - face_curve
                y_back = current_d + face_curve

                row_front.append(bm.verts.new((x, y_front, z)))
                row_back.append(bm.verts.new((x, y_back, z)))

            verts_front.append(row_front)
            verts_back.append(row_back)

        # Front faces
        for row in range(n_rows):
            for col in range(n_cols):
                bm.faces.new([
                    verts_front[row][col],
                    verts_front[row][col + 1],
                    verts_front[row + 1][col + 1],
                    verts_front[row + 1][col],
                ])

        # Back faces (reversed winding)
        for row in range(n_rows):
            for col in range(n_cols):
                bm.faces.new([
                    verts_back[row + 1][col],
                    verts_back[row + 1][col + 1],
                    verts_back[row][col + 1],
                    verts_back[row][col],
                ])

        # Side panels
        for row in range(n_rows):
            # Left
            bm.faces.new([
                verts_front[row][0],
                verts_front[row + 1][0],
                verts_back[row + 1][0],
                verts_back[row][0],
            ])
            # Right
            bm.faces.new([
                verts_back[row][n_cols],
                verts_back[row + 1][n_cols],
                verts_front[row + 1][n_cols],
                verts_front[row][n_cols],
            ])

        # Top cap
        top_verts = []
        for col in range(n_cols + 1):
            top_verts.append(verts_front[n_rows][col])
        for col in range(n_cols, -1, -1):
            top_verts.append(verts_back[n_rows][col])
        bm.faces.new(top_verts)

        # Bottom cap
        bot_verts = []
        for col in range(n_cols, -1, -1):
            bot_verts.append(verts_front[0][col])
        for col in range(n_cols + 1):
            bot_verts.append(verts_back[0][col])
        bm.faces.new(bot_verts)

        # --- UV mapping ---
        bm.faces.ensure_lookup_table()
        uv_layer = bm.loops.layers.uv.new("UVMap")

        # UV map the front face grid
        front_face_count = n_rows * n_cols
        for face_idx in range(front_face_count):
            face = bm.faces[face_idx]
            row = face_idx // n_cols
            col = face_idx % n_cols

            # Map to 0..1 UV space
            uvs = [
                (col / n_cols, row / n_rows),
                ((col + 1) / n_cols, row / n_rows),
                ((col + 1) / n_cols, (row + 1) / n_rows),
                (col / n_cols, (row + 1) / n_rows),
            ]
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = uv

        # Back faces get mirrored UVs
        back_start = front_face_count
        for face_idx in range(front_face_count):
            face = bm.faces[back_start + face_idx]
            row = face_idx // n_cols
            col = face_idx % n_cols

            uvs = [
                (col / n_cols, (row + 1) / n_rows),
                ((col + 1) / n_cols, (row + 1) / n_rows),
                ((col + 1) / n_cols, row / n_rows),
                (col / n_cols, row / n_rows),
            ]
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = uv

        # Side/top/bottom faces — basic planar UV
        for face_idx in range(2 * front_face_count, len(bm.faces)):
            face = bm.faces[face_idx]
            for loop in face.loops:
                co = loop.vert.co
                loop[uv_layer].uv = (
                    (co.x + w) / (2 * w),
                    co.z / h,
                )

    else:
        # Flat pouch — very thin with slight pillow curve
        n_rows = 8
        n_cols = 6

        verts_front = []
        verts_back = []

        for row in range(n_rows + 1):
            t = row / n_rows
            z = t * h

            bulge = math.sin(t * math.pi) * 0.12
            current_d = d * (1.0 + bulge)

            row_front = []
            row_back = []
            for col in range(n_cols + 1):
                s = col / n_cols
                x = -w + 2 * w * s
                face_curve = math.sin(s * math.pi) * current_d * 0.08
                y_front = -current_d - face_curve
                y_back = current_d + face_curve
                row_front.append(bm.verts.new((x, y_front, z)))
                row_back.append(bm.verts.new((x, y_back, z)))

            verts_front.append(row_front)
            verts_back.append(row_back)

        # Faces
        for row in range(n_rows):
            for col in range(n_cols):
                bm.faces.new([
                    verts_front[row][col],
                    verts_front[row][col + 1],
                    verts_front[row + 1][col + 1],
                    verts_front[row + 1][col],
                ])

        for row in range(n_rows):
            for col in range(n_cols):
                bm.faces.new([
                    verts_back[row + 1][col],
                    verts_back[row + 1][col + 1],
                    verts_back[row][col + 1],
                    verts_back[row][col],
                ])

        for row in range(n_rows):
            bm.faces.new([
                verts_front[row][0],
                verts_front[row + 1][0],
                verts_back[row + 1][0],
                verts_back[row][0],
            ])
            bm.faces.new([
                verts_back[row][n_cols],
                verts_back[row + 1][n_cols],
                verts_front[row + 1][n_cols],
                verts_front[row][n_cols],
            ])

        top_verts = []
        for col in range(n_cols + 1):
            top_verts.append(verts_front[n_rows][col])
        for col in range(n_cols, -1, -1):
            top_verts.append(verts_back[n_rows][col])
        bm.faces.new(top_verts)

        bot_verts = []
        for col in range(n_cols, -1, -1):
            bot_verts.append(verts_front[0][col])
        for col in range(n_cols + 1):
            bot_verts.append(verts_back[0][col])
        bm.faces.new(bot_verts)

        # UV mapping
        bm.faces.ensure_lookup_table()
        uv_layer = bm.loops.layers.uv.new("UVMap")

        front_count = n_rows * n_cols
        for face_idx in range(front_count):
            face = bm.faces[face_idx]
            row = face_idx // n_cols
            col = face_idx % n_cols
            uvs = [
                (col / n_cols, row / n_rows),
                ((col + 1) / n_cols, row / n_rows),
                ((col + 1) / n_cols, (row + 1) / n_rows),
                (col / n_cols, (row + 1) / n_rows),
            ]
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = uv

        back_start = front_count
        for face_idx in range(front_count):
            face = bm.faces[back_start + face_idx]
            row = face_idx // n_cols
            col = face_idx % n_cols
            uvs = [
                (col / n_cols, (row + 1) / n_rows),
                ((col + 1) / n_cols, (row + 1) / n_rows),
                ((col + 1) / n_cols, row / n_rows),
                (col / n_cols, row / n_rows),
            ]
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = uv

        for face_idx in range(2 * front_count, len(bm.faces)):
            face = bm.faces[face_idx]
            for loop in face.loops:
                co = loop.vert.co
                loop[uv_layer].uv = (
                    (co.x + w) / (2 * w),
                    co.z / h,
                )

    # Finalize mesh
    mesh = bpy.data.meshes.new("Bag")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("Bag", mesh)
    bpy.context.collection.objects.link(obj)

    # Smooth shading
    for face in obj.data.polygons:
        face.use_smooth = True

    # Light subdivision for smoothness
    subsurf = obj.modifiers.new("Subsurf", 'SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 1

    # Apply a default white material (Three.js will override)
    mat = bpy.data.materials.new(name="BagMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.5
    obj.data.materials.append(mat)

    return obj


def add_zipper_mesh(gusset_type):
    """Add a separate zipper strip mesh (exported as child)."""
    w = 0.06
    d = 0.02
    h = 0.18
    zipper_z = h * 0.88
    strip_h = 0.003

    if gusset_type in ("k_seal", "plow"):
        # Calculate the front face Y at the zipper height
        t = zipper_z / h
        bulge = math.sin(t * math.pi) * 0.35
        if t < 0.5:
            bulge *= 1.2
        if t > 0.9:
            bulge *= 0.3
        current_d = d * (1.0 + bulge * 0.25)
    else:
        t = zipper_z / h
        bulge = math.sin(t * math.pi) * 0.12
        current_d = d * (1.0 + bulge)

    protrude = 0.001

    bm = bmesh.new()
    v1 = bm.verts.new((-w + 0.006, -current_d - protrude, zipper_z - strip_h))
    v2 = bm.verts.new((w - 0.006, -current_d - protrude, zipper_z - strip_h))
    v3 = bm.verts.new((w - 0.006, -current_d - protrude, zipper_z + strip_h))
    v4 = bm.verts.new((-w + 0.006, -current_d - protrude, zipper_z + strip_h))
    bm.faces.new([v1, v2, v3, v4])

    mesh = bpy.data.meshes.new("Zipper")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("Zipper", mesh)
    bpy.context.collection.objects.link(obj)

    for face in obj.data.polygons:
        face.use_smooth = True

    solidify = obj.modifiers.new("Solidify", 'SOLIDIFY')
    solidify.thickness = 0.0012
    solidify.offset = 0

    mat = bpy.data.materials.new(name="ZipperMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.75, 0.75, 0.75, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.35
    obj.data.materials.append(mat)

    return obj


def add_seal_edge_mesh(gusset_type):
    """Add heat seal edge geometry as a separate object."""
    w = 0.06
    d = 0.02
    h = 0.18
    seal_w = 0.005

    if gusset_type in ("k_seal", "plow"):
        # Front face depth at edges (approximately at sides)
        current_d = d * 1.0  # minimal bulge at edges
    else:
        current_d = d

    bm = bmesh.new()

    # Top seal strip
    offset = 0.0004
    v1 = bm.verts.new((-w, -current_d - offset, h - seal_w))
    v2 = bm.verts.new((w, -current_d - offset, h - seal_w))
    v3 = bm.verts.new((w, -current_d - offset, h))
    v4 = bm.verts.new((-w, -current_d - offset, h))
    bm.faces.new([v1, v2, v3, v4])

    # Left seal strip
    v5 = bm.verts.new((-w - offset, -current_d, 0))
    v6 = bm.verts.new((-w + seal_w - offset, -current_d, 0))
    v7 = bm.verts.new((-w + seal_w - offset, -current_d, h))
    v8 = bm.verts.new((-w - offset, -current_d, h))
    bm.faces.new([v5, v6, v7, v8])

    # Right seal strip
    v9 = bm.verts.new((w - seal_w + offset, -current_d, 0))
    v10 = bm.verts.new((w + offset, -current_d, 0))
    v11 = bm.verts.new((w + offset, -current_d, h))
    v12 = bm.verts.new((w - seal_w + offset, -current_d, h))
    bm.faces.new([v9, v10, v11, v12])

    mesh = bpy.data.meshes.new("SealEdges")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("SealEdges", mesh)
    bpy.context.collection.objects.link(obj)

    mat = bpy.data.materials.new(name="SealMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.85, 0.85, 0.87, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.6
    bsdf.inputs['Alpha'].default_value = 0.25
    obj.data.materials.append(mat)

    return obj


def export_glb(filepath):
    """Export the scene as a .glb file."""
    # Select all mesh objects
    bpy.ops.object.select_all(action='SELECT')

    # Apply modifiers before export
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            for mod in obj.modifiers:
                bpy.ops.object.modifier_apply(modifier=mod.name)

    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_materials='EXPORT',
        export_normals=True,
        export_yup=True,  # Three.js uses Y-up
    )


# ── Export all bag types ──────────────────────────────────────

BAG_CONFIGS = {
    "standup-kseal": "k_seal",
    "standup-plow": "plow",
    "flat-3side": "none",
    "flat-2side": "none",
}

def main():
    for bag_name, gusset_type in BAG_CONFIGS.items():
        filepath = os.path.join(OUTPUT_DIR, f"{bag_name}.glb")

        print(f"\n{'='*50}")
        print(f"Exporting: {bag_name}")
        print(f"  Gusset: {gusset_type}")
        print(f"  Output: {filepath}")

        clean_scene()

        # Create the bag mesh
        bag = create_standup_pouch(gusset_type)

        # Add feature meshes
        add_zipper_mesh(gusset_type)
        add_seal_edge_mesh(gusset_type)

        # Export
        export_glb(filepath)

        file_size = os.path.getsize(filepath) / 1024
        print(f"  ✓ Exported ({file_size:.1f} KB)")

    print(f"\n{'='*50}")
    print(f"Done! All meshes exported to {OUTPUT_DIR}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
