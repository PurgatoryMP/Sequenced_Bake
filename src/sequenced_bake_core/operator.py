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

from .processing import (
    clear_generated_textures,
    connect_metallic_node,
    reconnect_node,
    create_image_texture,
    bake_frame,
)


class SequencedBakeOperator(bpy.types.Operator):
    """
    Blender operator that performs sequenced texture baking.

    This operator iterates over a frame range and bakes one or more texture
    types (e.g. Normal, Roughness, Metallic) for either the active material
    or all materials assigned to the active object. Each bake is written to
    a structured output directory on disk.

    The operator requires:
    - Cycles as the active render engine
    - An active object with at least one material
    - A valid output path specified in the add-on properties
    """

    bl_idname = "sequenced_bake.bake"
    bl_label = "Sequenced Bake"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """
        Execute the sequenced baking process.

        This method validates the current scene configuration, determines
        which materials and bake passes are enabled, and performs texture
        baking for each frame in the scene's frame range. Temporary image
        texture nodes are created per frame and cleaned up once baking
        completes.

        Args:
            context (bpy.types.Context): Blender context providing access to
                the active scene, object, and user-defined properties.

        Returns:
            set[str]:
                - {'FINISHED'} if the bake process completes successfully
                - {'CANCELLED'} if a blocking error occurs (e.g. missing output path)
        """
        scene = context.scene
        props = scene.sequenced_bake_props
        
        # Ensure Cycles is the active render engine (required for baking)
        if scene.render.engine != 'CYCLES':
            self.report({'WARNING'}, "Sequenced Bake requires Cycles render engine")
            return {'FINISHED'}
        
        # Validate that an output path has been provided
        if not props.sequenced_bake_output_path:
            self.report({'ERROR'}, "No output path specified")
            return {'CANCELLED'}
        
        # Resolve and create the root output directory
        output_root = bpy.path.abspath(props.sequenced_bake_output_path)
        os.makedirs(output_root, exist_ok=True)
        
        # Retrieve the active object and ensure it has a material
        obj = context.active_object
        if not obj or not obj.active_material:
            self.report({'ERROR'}, "Active object with material required")
            return {'CANCELLED'}

        # Determine materials to bake
        if props.bake_mode == 'ALL':
            mats_to_bake = [slot.material for slot in obj.material_slots if slot.material]
        else:
            mats_to_bake = [obj.active_material]
            
        # Abort if no valid materials were found
        if not mats_to_bake:
            self.report({'ERROR'}, "No materials found or selected to bake")
            return {'CANCELLED'}
        
        # Cache the frame range from the scene
        frame_start = scene.frame_start
        frame_end = scene.frame_end

        # Map bake pass identifiers to their corresponding enable flags
        bake_map = {
            "NORMAL": props.sequenced_bake_normal,
            "ROUGHNESS": props.sequenced_bake_roughness,
            "GLOSSY": props.sequenced_bake_glossy,
            "EMIT": props.sequenced_bake_emission,
            "AO": props.sequenced_bake_ambient_occlusion,
            "SHADOW": props.sequenced_bake_shadow,
            "POSITION": props.sequenced_bake_position,
            "UV": props.sequenced_bake_uv,
            "ENVIRONMENT": props.sequenced_bake_environment,
            "DIFFUSE": props.sequenced_bake_diffuse,
            "TRANSMISSION": props.sequenced_bake_transmission,
            "COMBINED": props.sequenced_bake_combined,
            "METALLIC": props.sequenced_bake_metallic,
        }
        
        # Iterate over each material selected for baking
        for mat in mats_to_bake:
            # Iterate over each enabled bake type
            for bake_type, enabled in bake_map.items():
                if not enabled:
                    continue
                    
                # Special-case handling for Metallic baking
                # (requires temporary node rewiring)
                if bake_type == "METALLIC":
                    connect_metallic_node(mat)
                    
                # TODO: Add GLTF Bake somewhere in here.
                    
                # Create an output directory per object/material/bake type
                bake_dir = os.path.join(output_root, f"{obj.name}_{mat.name}_{bake_type}")
                os.makedirs(bake_dir, exist_ok=True)
                
                # Bake the current pass for every frame in the range
                for frame in range(frame_start, frame_end + 1):
                    # Create a new image texture node for this frame
                    image_node, image = create_image_texture(
                        material=mat,
                        name=f"{obj.name}_{mat.name}_{bake_type}_{frame}",
                        width=props.sequenced_bake_width,
                        height=props.sequenced_bake_height,
                        alpha=props.sequence_is_alpha,
                        float_buffer=props.sequence_use_float,
                        interpolation=props.interpolation,
                        projection=props.projection,
                        extension=props.extension,
                        colorspace=props.colorspace,
                    )
                    
                    # Perform the actual bake operation for the frame
                    bake_frame(
                        bake_type=bake_type,
                        props=props,
                        frame=frame,
                        obj=obj,
                        mat=mat,
                        image_node=image_node,
                        image=image,
                        output_dir=bake_dir,
                    )
                
                # Restore the original node connections after Metallic baking
                if bake_type == "METALLIC":
                    reconnect_node(mat)
        
        # Remove all temporary image textures created during baking
        clear_generated_textures(props)
        
        # Report successful completion to the user
        self.report({'INFO'}, f"Sequenced Bake completed for {len(mats_to_bake)} material(s)")
        return {'FINISHED'}
