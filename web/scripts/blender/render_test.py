"""
Quick single-render test — standup-kseal + metallic + matte
Usage: blender --background --python render_test.py
"""
import bpy, sys, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from render_bags import (
    clean_scene, setup_render_settings, setup_world, setup_lighting, setup_camera,
    create_standup_pouch, create_material, add_zipper_line, add_tear_notch_marks,
    add_skirt_seal_band, add_seal_edges, add_ground_shadow_catcher,
    BAG_SHAPES, SUBSTRATES, FINISHES, OUTPUT_DIR
)

clean_scene()
setup_render_settings()
bpy.context.scene.cycles.samples = 32  # fast test

shape = BAG_SHAPES["standup-kseal"]
setup_world()
setup_lighting()
setup_camera(shape)
add_ground_shadow_catcher()

bag = create_standup_pouch(shape)
mat = create_material("test", SUBSTRATES["metallic"], FINISHES["matte"])
bag.data.materials.append(mat)

add_zipper_line(shape)
add_tear_notch_marks(shape)
add_skirt_seal_band(shape)
add_seal_edges(shape)

filepath = os.path.join(OUTPUT_DIR, "_test_render.png")
bpy.context.scene.render.filepath = filepath
bpy.ops.render.render(write_still=True)
print(f"\n✓ Test render: {filepath}")
