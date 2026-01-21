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
    Removes all unused Blender images from memory if the user has enabled
    the 'clear baked maps' option in the properties.

    Args:
        props (bpy.types.PropertyGroup): The add-on properties containing
            the user settings, specifically 'sequence_clear_baked_maps'.

    Returns:
        str or None: Returns an error message string if an exception occurs
        while clearing images, otherwise returns None.
    """
    if props.sequence_clear_baked_maps:
        try:
            for image in bpy.data.images:
                if image.users == 0:
                    bpy.data.images.remove(image)
        except Exception as err:
            return f"Problem clearing baked maps: {err}"
    return None


def connect_metallic_node(material):
    """
    Redirects the node currently connected to the 'Metallic' input of a
    Principled BSDF shader directly to the 'Surface' input of the
    Material Output node for baking metallic maps.

    Args:
        material (bpy.types.Material): The Blender material to modify.

    Returns:
        str or None: Returns an error message if the Principled BSDF or
        Material Output node is not found, or if the material has no node
        tree. Returns None on success.
    """
    if material.use_nodes:
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        principled_bsdf = None
        material_output = None

        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_bsdf = node
            elif node.type == 'OUTPUT_MATERIAL':
                material_output = node

        if principled_bsdf and material_output:
            metallic_input = principled_bsdf.inputs['Metallic']
            if metallic_input.is_linked:
                connected_node_link = metallic_input.links[0]
                links.new(connected_node_link.from_socket, material_output.inputs['Surface'])
        else:
            return "Principled BSDF or Material Output not found"
    else:
        return "Material does not use nodes"
    return None


def reconnect_node(material):
    """
    Restores the connection between the Principled BSDF node and the
    Material Output node after temporary disconnections (e.g., for metallic baking).

    Args:
        material (bpy.types.Material): The Blender material to modify.

    Returns:
        str or None: Returns an error message if the Principled BSDF or
        Material Output node is not found, or if the material has no node
        tree. Returns None on success.
    """
    if material.use_nodes:
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        principled_bsdf = None
        material_output = None

        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_bsdf = node
            elif node.type == 'OUTPUT_MATERIAL':
                material_output = node

        if principled_bsdf and material_output:
            surface_input = material_output.inputs['Surface']
            for link in list(surface_input.links):
                links.remove(link)
            links.new(principled_bsdf.outputs['BSDF'], surface_input)
        else:
            return "Principled BSDF or Material Output not found"
    else:
        return "Material does not use nodes"
    return None


def create_image_texture(material, name, width, height, alpha, float_buffer, interpolation, projection, extension):
    """
    Creates a new image and corresponding Image Texture node in the
    material’s node tree. Node is positioned to the right of the Material Output.

    Args:
        material (bpy.types.Material): The Blender material to add the node to.
        name (str): Name of the image and node.
        width (int): Width of the image in pixels.
        height (int): Height of the image in pixels.
        alpha (bool): Whether the image has an alpha channel.
        float_buffer (bool): Whether to use floating-point precision.
        interpolation (str): Interpolation method ('Linear', 'Closest', etc.).
        projection (str): Texture projection type ('FLAT', 'CUBE', etc.).
        extension (str): Image extension behavior ('REPEAT', 'CLIP', etc.).

    Returns:
        tuple: (ShaderNodeTexImage, bpy.types.Image)
    """
    image = bpy.data.images.new(name=name, width=width, height=height, alpha=alpha, float_buffer=float_buffer)
    node = material.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = image
    node.interpolation = interpolation.capitalize()
    node.projection = projection.upper()
    node.extension = extension.upper()
    mat_output = next((n for n in material.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if mat_output:
        node.location = (mat_output.location.x + 250, mat_output.location.y)
    return node, image


def bake_frame(bake_type, props, frame, obj, mat, image_node, image, output_dir):
    """
    Bakes a single frame for a specific bake type, applying all relevant
    settings such as lighting contributions, normal map swizzle, and
    selected-to-active options. Saves the image and removes the temporary node.

    Args:
        bake_type (str): Bake type ('NORMAL', 'ROUGHNESS', 'GLOSSY', 'EMIT',
            'AO', 'SHADOW', 'POSITION', 'UV', 'ENVIRONMENT', 'DIFFUSE',
            'TRANSMISSION', 'COMBINED', 'METALLIC').
        props (bpy.types.PropertyGroup): Add-on properties controlling bake settings.
        frame (int): Frame number.
        obj (bpy.types.Object): Active object.
        mat (bpy.types.Material): Active material.
        image_node (bpy.types.ShaderNodeTexImage): Temporary bake node.
        image (bpy.types.Image): Image to bake into.
        output_dir (str): Root output path.

    Returns:
        None
    """
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()

    bake_settings = bpy.context.scene.render.bake

    if bake_type == "DIFFUSE":
        bake_settings.use_pass_direct = props.diffuse_lighting_direct
        bake_settings.use_pass_indirect = props.diffuse_lighting_indirect
        bake_settings.use_pass_color = props.diffuse_lighting_color
    elif bake_type == "GLOSSY":
        bake_settings.use_pass_direct = props.glossy_lighting_direct
        bake_settings.use_pass_indirect = props.glossy_lighting_indirect
        bake_settings.use_pass_color = props.glossy_lighting_color
    elif bake_type == "TRANSMISSION":
        bake_settings.use_pass_direct = props.transmission_lighting_direct
        bake_settings.use_pass_indirect = props.transmission_lighting_indirect
        bake_settings.use_pass_color = props.transmission_lighting_color
    elif bake_type == "NORMAL":
        bake_settings.normal_space = props.normal_map_space
        bake_settings.normal_r = props.normal_map_red_channel
        bake_settings.normal_g = props.normal_map_green_channel
        bake_settings.normal_b = props.normal_map_blue_channel
    elif bake_type == "COMBINED":
        bake_settings.use_pass_direct = props.combined_lighting_direct
        bake_settings.use_pass_indirect = props.combined_lighting_indirect
        bake_settings.use_pass_diffuse = props.combined_contribution_deffuse
        bake_settings.use_pass_glossy = props.combined_contribution_glossy
        bake_settings.use_pass_transmission = props.combined_contribution_transmission
        bake_settings.use_pass_emit = props.combined_contribution_emit
    elif bake_type in ["ROUGHNESS", "EMIT", "AO", "SHADOW", "POSITION", "UV", "ENVIRONMENT"]:
        # For these bake types, no special lighting contributions are applied
        pass

    file_path = os.path.join(output_dir, f"{obj.name}_{mat.name}_{bake_type}", f"{frame}.{props.sequenced_bake_image_format}")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    cage_obj_name = props.selected_to_active_cage_object.name if props.selected_to_active_cage and props.selected_to_active_cage_object else ""
    bpy.ops.object.bake(
        type=bake_type if bake_type != "METALLIC" else "EMIT",
        use_selected_to_active=props.sequenced_selected_to_active,
        cage_extrusion=props.selected_to_active_extrusion,
        max_ray_distance=props.selected_to_active_max_ray_distance,
        cage_object=cage_obj_name
    )

    if not props.sequence_use_float:
        bpy.context.scene.render.image_settings.color_depth = '8'
    image.save_render(file_path)

    mat.node_tree.nodes.remove(image_node)
