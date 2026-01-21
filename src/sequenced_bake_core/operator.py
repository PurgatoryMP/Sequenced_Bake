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
from bpy.types import Operator
from .processing import clear_generated_textures, create_image_texture, bake_frame, connect_metallic_node, reconnect_node

class SequencedBakeOperator(Operator):
    """
    Operator for baking material sequences in Blender using Cycles.

    This operator automates the process of baking multiple material maps
    (e.g., normal, roughness, diffuse, metallic, etc.) across a range
    of frames. It manages the creation and cleanup of temporary Image
    Texture nodes, applies per-bake-type settings, and saves the resulting
    images to the specified output directory.

    It also handles special cases such as Metallic map baking, reconnecting
    nodes after baking, and clearing unused textures if configured.

    Attributes:
        bl_idname (str): Blender identifier for the operator.
        bl_label (str): Human-readable label for the operator.
        bl_description (str): Tooltip description shown in Blender.
    """
    bl_idname = "sequenced_bake.bake"
    bl_label = "Sequenced Bake"
    bl_description = "Bakes the material sequence for the selected bake types"

    def execute(self, context):
        """
        Executes the baking operation for the active object and its material.

        This method performs the following steps:

        1. Checks that the render engine is set to Cycles.
        2. Validates that there is an active object and material.
        3. Determines which bake types are enabled in the add-on properties.
        4. Clears any previously generated textures if the option is enabled.
        5. Iterates through each bake type and each frame in the scene’s
           frame range:
           - Creates a temporary Image Texture node
           - Sets bake-specific settings
           - Executes the bake
           - Saves the resulting image
           - Cleans up the temporary node
        6. Handles Metallic map baking with special node connection logic.
        7. Reports completion or any errors encountered.

        Args:
            context (bpy.types.Context): Blender context containing the scene,
                active object, and other runtime information.

        Returns:
            set: Blender operator result set, typically {'FINISHED'} if
            successful or {'CANCELLED'} if errors occur.
        """
        scene = context.scene
        props = scene.sequenced_bake_props

        if scene.render.engine != 'CYCLES':
            self.report({'WARNING'}, "Render engine must be Cycles")
            return {'CANCELLED'}

        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}

        mat = obj.active_material
        if not mat:
            self.report({'ERROR'}, "Active object has no material")
            return {'CANCELLED'}

        # Determine bake types
        bake_types = []
        bake_map_options = [
            ("sequenced_bake_normal", "NORMAL"),
            ("sequenced_bake_roughness", "ROUGHNESS"),
            ("sequenced_bake_glossy", "GLOSSY"),
            ("sequenced_bake_emission", "EMIT"),
            ("sequenced_bake_ambient_occlusion", "AO"),
            ("sequenced_bake_shadow", "SHADOW"),
            ("sequenced_bake_position", "POSITION"),
            ("sequenced_bake_uv", "UV"),
            ("sequenced_bake_environment", "ENVIRONMENT"),
            ("sequenced_bake_diffuse", "DIFFUSE"),
            ("sequenced_bake_transmission", "TRANSMISSION"),
            ("sequenced_bake_combined", "COMBINED"),
            ("sequenced_bake_metallic", "METALLIC"),
        ]
        for prop_name, bake_name in bake_map_options:
            if getattr(props, prop_name):
                bake_types.append(bake_name)

        if not bake_types:
            self.report({'WARNING'}, "No bake types selected")
            return {'CANCELLED'}

        output_dir = props.sequenced_bake_output_path
        if not output_dir:
            self.report({'ERROR'}, "No output path specified")
            return {'CANCELLED'}

        # Clear old textures if needed
        err = clear_generated_textures(props)
        if err:
            self.report({'ERROR'}, err)

        # Perform baking for each type and frame
        for bake_type in bake_types:
            if bake_type == "METALLIC":
                connect_metallic_node(mat)

            for frame in range(scene.frame_start, scene.frame_end + 1):
                # Create new image texture
                node, image = create_image_texture(
                    material=mat,
                    name=f"{obj.name}_{mat.name}_{bake_type}",
                    width=props.sequenced_bake_width,
                    height=props.sequenced_bake_height,
                    alpha=props.sequence_is_alpha,
                    float_buffer=props.sequence_use_float,
                    interpolation=props.interpolation,
                    projection=props.projection,
                    extension=props.extension
                )

                bake_frame(bake_type, props, frame, obj, mat, node, image, output_dir)

            if bake_type == "METALLIC":
                reconnect_node(mat)

        self.report({'INFO'}, "Finished baking")
        return {'FINISHED'}

