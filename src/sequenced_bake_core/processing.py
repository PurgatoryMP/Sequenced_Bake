"""
    This file is part of Sequence Bake.

    Sequence Bake is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or any later version.

    Sequence Bake is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Sequence Bake. If not, see <http://www.gnu.org/licenses/>.

"""

import bpy
from mathutils import Vector
import os


def clear_generated_textures(props):
    """
    Remove unused image datablocks generated during baking.

    This function iterates through all images in the Blender file and removes
    any image with zero users, effectively cleaning up temporary textures
    created during the bake process. Cleanup is conditional based on the
    user's add-on preferences.

    Args:
        props: Property group containing Sequenced Bake settings. The
            `sequence_clear_baked_maps` flag determines whether cleanup
            is performed.
    """
    if not props.sequence_clear_baked_maps:
        return

    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)


def connect_metallic_node(material):
    """
    Temporarily reroute the Metallic input for baking.

    For Metallic baking, Blender requires the Metallic signal to be connected
    directly to the Material Output surface socket. This function detects an
    existing Metallic input connection on the Principled BSDF and redirects
    it to the Material Output node.

    Args:
        material (bpy.types.Material): The material whose node tree will be
            modified for Metallic baking.

    Raises:
        RuntimeError: If the Principled BSDF or Material Output node cannot
            be found in the material's node tree.
    """
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not bsdf or not output:
        raise RuntimeError("Required nodes not found for metallic bake")

    if bsdf.inputs['Metallic'].is_linked:
        src = bsdf.inputs['Metallic'].links[0].from_socket
        links.new(src, output.inputs['Surface'])


def connect_occlusion_node(material):
    """
    Temporarily reroute the Occlusio input for baking.

    steps:
    1: Add Combine Color Node set to RGB.
    2: Add Ambient Occlusion Node set to 16 samples with color set to white and connect the AO output socket to the Red input socket of the Combine Color Node.
    3: Get the current Principled BSDF connected to the material output and get the node connected to the metallic socket and connect it to the Green input socket of the combine color node.
    4: Get the current Principled BSDF connected to the material output and get the node connected to the roughness socket and connect it to the Blue input socket of the combine color node.
    5: Create a new temporary Principled BSDF.
    6: Set the temporary Principled BSDF Base color to black.
    7: Set the temporary Principled BSDF Roughness to 1.0.
    8: Connect the Color output socket of the Combine Color node to the Emission Color input socket of the new temporary Principled BSDF
    9: Set the Emission Strength to 1.0
    10: Connect the output of the temporary Principled BSDF to the Surface input of the material output node.
    11: The Frame is baked.
    12: then we reuse "def reconnect_node(material):" to restore the connections to where they were before.
    """
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not bsdf or not output:
        raise RuntimeError("Required nodes not found for occlusion bake")

    # --- Create Combine Color ---
    combine = nodes.new(type='ShaderNodeCombineColor')
    combine.mode = 'RGB'

    # ✅ INSERT HERE
    combine.label = "__SEQBAKE_TEMP__"

    # --- Create Ambient Occlusion ---
    ao = nodes.new(type='ShaderNodeAmbientOcclusion')
    ao.samples = 16
    ao.inputs['Color'].default_value = (1, 1, 1, 1)

    # ✅ INSERT HERE
    ao.label = "__SEQBAKE_TEMP__"

    # AO → R
    links.new(ao.outputs['Color'], combine.inputs['Red'])

    # Metallic → G
    if bsdf.inputs['Metallic'].is_linked:
        metallic_src = bsdf.inputs['Metallic'].links[0].from_socket
        links.new(metallic_src, combine.inputs['Green'])
    else:
        combine.inputs['Green'].default_value = bsdf.inputs['Metallic'].default_value

    # Roughness → B
    if bsdf.inputs['Roughness'].is_linked:
        roughness_src = bsdf.inputs['Roughness'].links[0].from_socket
        links.new(roughness_src, combine.inputs['Blue'])
    else:
        combine.inputs['Blue'].default_value = bsdf.inputs['Roughness'].default_value

    # --- Remove existing output links ---
    for link in list(output.inputs['Surface'].links):
        links.remove(link)

    # --- Temp Principled ---
    temp_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')

    # ✅ INSERT HERE
    temp_bsdf.label = "__SEQBAKE_TEMP__"

    temp_bsdf.inputs['Base Color'].default_value = (0, 0, 0, 1)
    temp_bsdf.inputs['Roughness'].default_value = 1.0

    # --- Alpha ---
    if 'Alpha' in bsdf.inputs and 'Alpha' in temp_bsdf.inputs:
        if bsdf.inputs['Alpha'].is_linked:
            alpha_src = bsdf.inputs['Alpha'].links[0].from_socket
            links.new(alpha_src, temp_bsdf.inputs['Alpha'])
        else:
            temp_bsdf.inputs['Alpha'].default_value = bsdf.inputs['Alpha'].default_value

    # --- Normal ---
    if 'Normal' in bsdf.inputs and 'Normal' in temp_bsdf.inputs:
        if bsdf.inputs['Normal'].is_linked:
            normal_src = bsdf.inputs['Normal'].links[0].from_socket
            links.new(normal_src, temp_bsdf.inputs['Normal'])

    # Combine → Emission
    links.new(combine.outputs['Color'], temp_bsdf.inputs['Emission Color'])
    temp_bsdf.inputs['Emission Strength'].default_value = 1.0

    # Output
    links.new(temp_bsdf.outputs['BSDF'], output.inputs['Surface'])


def create_sculpt_bbox_helper(obj, min_v, max_v, bbox_scale=1.0):
    name = "__SEQBAKE_SCULPT_BBOX__"

    # Remove existing helper if present
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    size = (max_v - min_v) * bbox_scale
    center = (max_v + min_v) * 0.5

    # Build a unit cube mesh centered on origin
    verts = [
        (-1.0, -1.0, -1.0),
        (-1.0, -1.0,  1.0),
        (-1.0,  1.0, -1.0),
        (-1.0,  1.0,  1.0),
        ( 1.0, -1.0, -1.0),
        ( 1.0, -1.0,  1.0),
        ( 1.0,  1.0, -1.0),
        ( 1.0,  1.0,  1.0),
    ]

    faces = [
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    ]

    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    cube = bpy.data.objects.new(name, mesh)

    # Link to a visible collection
    collection = obj.users_collection[0] if obj.users_collection else bpy.context.scene.collection
    collection.objects.link(cube)

    # Parent it to the target object so it follows transforms
    cube.parent = obj
    cube.matrix_parent_inverse.identity()

    # Local transform relative to parent
    cube.location = center
    cube.scale = size * 0.5

    # Display settings
    cube.display_type = 'WIRE'
    cube.hide_render = True
    cube.hide_select = True
    cube.hide_viewport = False
    cube.show_in_front = True

    return cube


def get_cached_bbox(obj):
    return obj.get("__seqbake_bbox_cache__", None)


def set_cached_bbox(obj, min_v, max_v):
    obj["__seqbake_bbox_cache__"] = {
        "min": [min_v.x, min_v.y, min_v.z],
        "max": [max_v.x, max_v.y, max_v.z],
    }

def remove_sculpt_bbox_helper():
    obj = bpy.data.objects.get("__SEQBAKE_SCULPT_BBOX__")
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


def connect_sculpt_node(material, obj=None, props=None):
    """
    Temporarily reroute the material to output a sculpt map.

    Supports:
        connect_sculpt_node(material, obj, props)
    and, for backward compatibility:
        connect_sculpt_node(material, props)
    """

    # Backward-compatibility fallback:
    # If called as connect_sculpt_node(material, props), obj is actually props.
    if props is None:
        props = obj
        obj = bpy.context.active_object

    if obj is None:
        raise RuntimeError("connect_sculpt_node: target object is missing")

    if props is None:
        raise RuntimeError("connect_sculpt_node: props is missing")

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    TEMP_TAG = "__SEQBAKE_TEMP__"

    # --- Find Material Output ---
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        raise RuntimeError("Material Output not found for sculpt bake")

    # --- Evaluated mesh ---
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.data

    verts = [v.co for v in mesh.vertices]
    if not verts:
        raise RuntimeError("Sculpt bake mesh has no vertices")

    min_v_live = Vector((
        min(v.x for v in verts),
        min(v.y for v in verts),
        min(v.z for v in verts),
    ))

    max_v_live = Vector((
        max(v.x for v in verts),
        max(v.y for v in verts),
        max(v.z for v in verts),
    ))

    # --- Resolve bounding mode ---
    if props.sequenced_sculpt_bbox_dynamic:
        bbox_min = min_v_live
        bbox_max = max_v_live
        set_cached_bbox(obj, bbox_min, bbox_max)
    else:
        cached = get_cached_bbox(obj)
        if cached and "min" in cached and "max" in cached:
            bbox_min = Vector(cached["min"])
            bbox_max = Vector(cached["max"])
        else:
            bbox_min = min_v_live
            bbox_max = max_v_live
            set_cached_bbox(obj, bbox_min, bbox_max)

    bbox_scale = props.sequenced_sculpt_bbox_scale

    size_v = (bbox_max - bbox_min) * bbox_scale

    # Prevent divide by zero
    size_v.x = size_v.x if abs(size_v.x) > 1e-6 else 1e-6
    size_v.y = size_v.y if abs(size_v.y) > 1e-6 else 1e-6
    size_v.z = size_v.z if abs(size_v.z) > 1e-6 else 1e-6

    # --- Helper cube ---
    if props.sequenced_sculpt_show_bbox:
        create_sculpt_bbox_helper(obj, bbox_min, bbox_max, bbox_scale)
    else:
        remove_sculpt_bbox_helper()

    # --- Sculpt mapping baseline ---
    base_offset_v = Vector((0.0, 0.0, bbox_min.z))
    base_scale_v = Vector((2.0, 2.0, size_v.z))

    # --- User offsets ---
    user_offset_v = Vector((
        props.sequenced_sculpt_offset_x,
        props.sequenced_sculpt_offset_y,
        props.sequenced_sculpt_offset_z,
    ))

    offset_v = base_offset_v + user_offset_v
    scale_v = base_scale_v

    # --- Clear existing Surface links ---
    for link in list(output.inputs['Surface'].links):
        links.remove(link)

    # --- Nodes ---
    geom = nodes.new(type='ShaderNodeNewGeometry')
    geom.label = TEMP_TAG

    sub = nodes.new(type='ShaderNodeVectorMath')
    sub.operation = 'SUBTRACT'
    sub.label = TEMP_TAG

    div = nodes.new(type='ShaderNodeVectorMath')
    div.operation = 'DIVIDE'
    div.label = TEMP_TAG

    add = nodes.new(type='ShaderNodeVectorMath')
    add.operation = 'ADD'
    add.label = TEMP_TAG

    emission = nodes.new(type='ShaderNodeEmission')
    emission.label = TEMP_TAG

    # --- Constant nodes ---
    offset_node = nodes.new(type='ShaderNodeCombineXYZ')
    offset_node.label = TEMP_TAG
    offset_node.inputs[0].default_value = offset_v.x
    offset_node.inputs[1].default_value = offset_v.y
    offset_node.inputs[2].default_value = offset_v.z

    scale_node = nodes.new(type='ShaderNodeCombineXYZ')
    scale_node.label = TEMP_TAG
    scale_node.inputs[0].default_value = scale_v.x
    scale_node.inputs[1].default_value = scale_v.y
    scale_node.inputs[2].default_value = scale_v.z

    half_node = nodes.new(type='ShaderNodeCombineXYZ')
    half_node.label = TEMP_TAG
    half_node.inputs[0].default_value = 0.5
    half_node.inputs[1].default_value = 0.5
    half_node.inputs[2].default_value = 0.0

    # --- Wiring ---
    links.new(geom.outputs['Position'], sub.inputs[0])
    links.new(offset_node.outputs['Vector'], sub.inputs[1])

    links.new(sub.outputs['Vector'], div.inputs[0])
    links.new(scale_node.outputs['Vector'], div.inputs[1])

    links.new(div.outputs['Vector'], add.inputs[0])
    links.new(half_node.outputs['Vector'], add.inputs[1])

    links.new(add.outputs['Vector'], emission.inputs['Color'])
    emission.inputs['Strength'].default_value = 1.0

    links.new(emission.outputs['Emission'], output.inputs['Surface'])


def reconnect_node(material):
    """
    Restore material after baking.

    - Removes temporary nodes
    - Restores BSDF → Output if available
    - Fails gracefully if not
    """

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    TEMP_TAG = "__SEQBAKE_TEMP__"

    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not output:
        print("[Sequenced Bake] WARNING: No Material Output node found.")
        return

    # --- Remove only TEMP connections ---
    for link in list(output.inputs['Surface'].links):
        if link.from_node.label == TEMP_TAG:
            links.remove(link)

    # --- Restore BSDF if available ---
    if bsdf:
        # Only reconnect if nothing is connected
        if not output.inputs['Surface'].is_linked:
            links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    else:
        print("[Sequenced Bake] WARNING: No Principled BSDF found, skipping reconnect.")

    # --- Cleanup temp nodes ---
    for node in list(nodes):
        if node.label == TEMP_TAG:
            nodes.remove(node)


def create_image_texture(material, name, width, height, alpha, float_buffer, interpolation, projection, extension,
                         colorspace):
    """
    Create and assign a new image texture node for baking.

    This function creates a new image datablock and assigns it to an
    Image Texture node within the given material. The node is set as
    active to ensure Blender bakes into it.

    Args:
        material (bpy.types.Material): Material to which the image texture
            node will be added.
        name (str): Name of the new image datablock.
        width (int): Width of the image in pixels.
        height (int): Height of the image in pixels.
        alpha (bool): Whether the image includes an alpha channel.
        float_buffer (bool): Whether to use a floating-point color buffer.
        interpolation (str): Texture interpolation mode.
        projection (str): Texture projection mode.
        extension (str): Texture extension mode.
        colorspace (str): Color space name for the image.

    Returns:
        tuple[bpy.types.Node, bpy.types.Image]:
            The created Image Texture node and its associated image datablock.
    """
    image = bpy.data.images.new(name=name, width=width, height=height, alpha=alpha, float_buffer=float_buffer)

    image.colorspace_settings.name = colorspace

    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    node.interpolation = interpolation
    node.projection = projection.upper()
    node.extension = extension.upper()

    material.node_tree.nodes.active = node

    output = next(
        (n for n in material.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'),
        None
    )
    if output:
        node.location = (output.location.x + 300, output.location.y)

    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    return node, image


def bake_frame(bake_type, props, frame, obj, mat, image_node, image, output_dir):
    """
    Bake a single frame for a specific bake pass and material.

    This function configures bake settings based on the bake type,
    updates the scene to the requested frame, performs the bake
    operation, and saves the resulting image to disk.

    Args:
        bake_type (str): The bake pass type (e.g. NORMAL, DIFFUSE, METALLIC).
        props: Property group containing Sequenced Bake settings.
        frame (int): Frame number to bake.
        obj (bpy.types.Object): Object being baked.
        mat (bpy.types.Material): Material being baked.
        image_node (bpy.types.Node): Active Image Texture node used for baking.
        image (bpy.types.Image): Image datablock receiving the baked result.
        output_dir (str): Directory where the baked image will be saved.
    """

    scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.context.view_layer.update()

    bake = scene.render.bake

    if bake_type == "DIFFUSE":
        bake.use_pass_direct = props.diffuse_lighting_direct
        bake.use_pass_indirect = props.diffuse_lighting_indirect
        bake.use_pass_color = props.diffuse_lighting_color

    elif bake_type == "GLOSSY":
        bake.use_pass_direct = props.glossy_lighting_direct
        bake.use_pass_indirect = props.glossy_lighting_indirect
        bake.use_pass_color = props.glossy_lighting_color

    elif bake_type == "TRANSMISSION":
        bake.use_pass_direct = props.transmission_lighting_direct
        bake.use_pass_indirect = props.transmission_lighting_indirect
        bake.use_pass_color = props.transmission_lighting_color

    elif bake_type == "COMBINED":
        bake.use_pass_direct = props.combined_lighting_direct
        bake.use_pass_indirect = props.combined_lighting_indirect
        bake.use_pass_diffuse = props.combined_contribution_deffuse
        bake.use_pass_glossy = props.combined_contribution_glossy
        bake.use_pass_transmission = props.combined_contribution_transmission
        bake.use_pass_emit = props.combined_contribution_emit

    elif bake_type == "NORMAL":
        bake.normal_space = props.normal_map_space
        bake.normal_r = props.normal_map_red_channel
        bake.normal_g = props.normal_map_green_channel
        bake.normal_b = props.normal_map_blue_channel

    scene.display_settings.display_device = props.display_device
    scene.view_settings.view_transform = props.view_transform
    scene.view_settings.look = props.look
    scene.view_settings.exposure = props.exposure
    scene.view_settings.gamma = props.gamma

    try:
        scene.sequencer_colorspace_settings.name = props.sequencer
    except Exception:
        pass

    cage_name = (
        props.selected_to_active_cage_object.name
        if props.selected_to_active_cage and props.selected_to_active_cage_object
        else ""
    )

    bpy.ops.object.bake(
        type=("EMIT" if bake_type in {"METALLIC", "OCCLUSION", "SCULPT"} else bake_type),
        use_selected_to_active=props.sequenced_selected_to_active,
        cage_extrusion=props.selected_to_active_extrusion,
        max_ray_distance=props.selected_to_active_max_ray_distance,
        cage_object=cage_name,
    )

    if not props.sequence_use_float:
        scene.render.image_settings.color_depth = '8'

    filepath = os.path.join(
        output_dir,
        f"{frame}.{props.sequenced_bake_image_format}"
    )

    image.save_render(filepath)
    mat.node_tree.nodes.remove(image_node)

    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
