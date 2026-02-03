# This file is part of Sequence Bake.
#
# Sequence Bake is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or any later version.
#
# Sequence Bake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sequence Bake. If not, see <http://www.gnu.org/licenses/>.

import bpy
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


def reconnect_node(material):
    """
    Restore the original material node connections after baking.

    This function removes any temporary links connected to the Material Output
    surface socket and reconnects the Principled BSDF output, restoring the
    material to its original shading configuration.

    Args:
        material (bpy.types.Material): The material whose node tree should
            be restored.

    Raises:
        RuntimeError: If the Principled BSDF or Material Output node cannot
            be found in the material's node tree.
    """
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not bsdf or not output:
        raise RuntimeError("Required nodes not found for reconnect")

    for link in list(output.inputs['Surface'].links):
        links.remove(link)

    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])


def create_image_texture(material, name, width, height, alpha, float_buffer, interpolation, projection, extension, colorspace):
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
        type=bake_type if bake_type != "METALLIC" else "EMIT",
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
