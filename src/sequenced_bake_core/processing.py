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
import bmesh
import numpy as np
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


def calculate_sculpt_bounds(obj):
    """
    Calculates stable sculpt normalization bounds from the evaluated mesh.
    """

    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)

    mesh_data = None

    try:
        mesh_data = obj_eval.to_mesh()

        if not mesh_data:
            raise RuntimeError(f"Failed to evaluate mesh for object: {obj.name}")

        verts_co = np.array([v.co[:] for v in mesh_data.vertices])

        max_abs = np.abs(verts_co).max(axis=0)
        max_abs = np.where(max_abs == 0.0, 1.0, max_abs)

        return max_abs

    finally:
        if mesh_data is not None:
            obj_eval.to_mesh_clear()


def bake_sculpt_direct_to_buffer(obj, image, normalization_bounds):
    """
    Bakes a sculpt-style vertex position map directly into an image buffer using UV-space sampling.

    This function generates a "sculpt map" by projecting mesh geometry into UV space and
    encoding interpolated vertex positions into an image. Each pixel corresponds to a UV
    coordinate, and the mesh surface is evaluated using barycentric interpolation across
    UV triangles.

    The resulting image encodes normalized object-space vertex positions (XYZ → RGB),
    commonly used for sculpt baking, procedural reconstruction, or displacement workflows.

    Args:
        obj (bpy.types.Object): The source mesh object to bake from.
        image (bpy.types.Image): Target image buffer to write baked data into.
        normalization_bounds: Sculpt normalization bounds from the evaluated mesh.

    Raises:
        RuntimeError: If mesh evaluation fails or the object has no active UV layer.
    """

    # Dependency graph ensures we evaluate the *final* mesh state
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)

    mesh_data = None
    bm = None

    try:
        # Convert evaluated object into a mesh datablock
        mesh_data = obj_eval.to_mesh()

        if not mesh_data:
            raise RuntimeError(f"Failed to evaluate mesh for object: {obj.name}")

        # BMesh is used for fast topology + loop-level UV access
        bm = bmesh.new()
        bm.from_mesh(mesh_data)

        # Active UV layer is required for UV-space rasterization
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            raise RuntimeError(f"Object '{obj.name}' has no active UV layer.")

        width, height = image.size

        # Initialize image buffer with neutral gray (0.5)
        # Alpha is set to fully opaque
        pixels = np.full((height, width, 4), 0.5, dtype=np.float32)
        pixels[:, :, 3] = 1.0

        # Pre-extract face UVs and vertex positions for faster sampling
        face_data = []
        for face in bm.faces:
            loops = face.loops

            uv_coords = [loop[uv_layer].uv.copy() for loop in loops]
            vert_coords = [loop.vert.co.copy() for loop in loops]

            face_data.append({
                "uvs": uv_coords,
                "verts": vert_coords,
            })

        # Iterate over each pixel in the output image
        for py in range(height):
            v = (py + 0.5) / height  # pixel center in UV space (V axis)

            for px in range(width):
                u = (px + 0.5) / width  # pixel center in UV space (U axis)

                sample_uv = Vector((u, v))

                first_barycentric_hit_position = None

                # Search for which triangle in UV space contains this pixel
                for face in face_data:

                    uvs = face["uvs"]
                    verts = face["verts"]

                    if len(uvs) < 3:
                        continue

                    # Handle n-gons by triangulating from first vertex (fan method)
                    for i in range(1, len(uvs) - 1):

                        uv1 = uvs[0]
                        uv2 = uvs[i]
                        uv3 = uvs[i + 1]

                        # Early reject degenerate UV triangles
                        area = abs(
                            (uv2.x - uv1.x) * (uv3.y - uv1.y) -
                            (uv3.x - uv1.x) * (uv2.y - uv1.y)
                        )

                        if area < 1e-10:
                            continue

                        # Compute barycentric weights in UV space
                        # This determines whether the pixel lies inside the triangle
                        w1, w2, w3 = calculate_barycentric(
                            u,
                            v,
                            uv1,
                            uv2,
                            uv3
                        )

                        # Reject if outside triangle
                        if w1 < 0 or w2 < 0 or w3 < 0:
                            continue

                        # Interpolate corresponding 3D vertex positions
                        p1 = verts[0]
                        p2 = verts[i]
                        p3 = verts[i + 1]

                        first_barycentric_hit_position = (
                            p1 * w1 +
                            p2 * w2 +
                            p3 * w3
                        )

                        break

                    # Stop searching faces once a hit is found
                    if first_barycentric_hit_position is not None:
                        break

                # Normalize 3D position into [0, 1] range for image encoding.
                normalized = ((np.array(first_barycentric_hit_position[:]) / normalization_bounds) * 0.5) + 0.5

                # Clamp and assign to pixel buffer (RGB = XYZ position)
                r = float(np.clip(normalized[0], 0.0, 1.0))
                g = float(np.clip(normalized[1], 0.0, 1.0))
                b = float(np.clip(normalized[2], 0.0, 1.0))

                pixels[py, px] = (r, g, b, 1.0)

        # Write full pixel buffer into Blender image datablock
        image.pixels.foreach_set(pixels.flatten())

    except Exception as exc:
        # Wrap any failure with contextual mesh/object information
        raise RuntimeError(
            f"Sculpt map bake failed for object '{obj.name}': {exc}"
        ) from exc

    finally:
        # Ensure BMesh is freed to avoid memory leaks
        if bm is not None:
            bm.free()

        # Clear evaluated mesh data from Blender
        if mesh_data is not None:
            obj_eval.to_mesh_clear()


def calculate_barycentric(px, py, uv1, uv2, uv3):
    """
    Computes barycentric coordinates for a point within a UV triangle.

    This is used to determine whether a UV pixel lies inside a triangle
    and to interpolate vertex attributes (here: 3D positions).

    Args:
        px (float): U coordinate of sample point.
        py (float): V coordinate of sample point.
        uv1 (Vector): First triangle UV vertex.
        uv2 (Vector): Second triangle UV vertex.
        uv3 (Vector): Third triangle UV vertex.

    Returns:
        tuple: (w1, w2, w3) barycentric weights. If triangle is degenerate,
               returns (-1, -1, -1).
    """

    # Determinant of triangle in UV space (twice signed area)
    det = (uv2.y - uv3.y) * (uv1.x - uv3.x) + (uv3.x - uv2.x) * (uv1.y - uv3.y)

    # Degenerate triangle check (zero area → invalid interpolation)
    if det == 0:
        return -1, -1, -1

    # Compute barycentric weights for point (px, py)
    w1 = ((uv2.y - uv3.y) * (px - uv3.x) + (uv3.x - uv2.x) * (py - uv3.y)) / det
    w2 = ((uv3.y - uv1.y) * (px - uv3.x) + (uv1.x - uv3.x) * (py - uv3.y)) / det
    w3 = 1 - w1 - w2  # ensures weights sum to 1

    return w1, w2, w3


def reconnect_node(material, temp_tag="__SEQBAKE_TEMP__"):
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not output:
        return

    for link in list(output.inputs['Surface'].links):
        if link.from_node.label == temp_tag:
            links.remove(link)

    if bsdf and not output.inputs['Surface'].is_linked:
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    for node in list(nodes):
        if node.label in {temp_tag}:
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


def bake_frame(bake_type, props, frame, obj, mat, image_node, image, output_dir, sculpt_bounds=None,):
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
        sculpt_bounds: defines the bounding box area of the sculpted object.
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

    # Bake sculpt map rather than a shader.
    if bake_type == "SCULPT":
        scene.render.bake.use_clear = True
        scene.render.bake.margin_type = 'EXTEND'
        bake_sculpt_direct_to_buffer(obj, image, sculpt_bounds)
        scene.render.image_settings.color_depth = '16'

        if scene.render.image_settings.file_format == 'PNG':
            scene.render.image_settings.compression = 0

        # Save the result
        filepath = os.path.join(output_dir, f"{frame}.{props.sequenced_bake_image_format}")
        image.save_render(filepath)

    else:
        bpy.ops.object.bake(
            type=("EMIT" if bake_type in {"METALLIC", "OCCLUSION"} else bake_type),
            use_selected_to_active=props.sequenced_selected_to_active,
            cage_extrusion=props.selected_to_active_extrusion,
            max_ray_distance=props.selected_to_active_max_ray_distance,
            cage_object=cage_name,
        )

        filepath = os.path.join(
            output_dir,
            f"{frame}.{props.sequenced_bake_image_format}"
        )

        image.save_render(filepath)

    mat.node_tree.nodes.remove(image_node)

    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
