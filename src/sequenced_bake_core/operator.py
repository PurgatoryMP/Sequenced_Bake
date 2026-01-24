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
    """Execute sequenced texture baking across frame ranges."""

    bl_idname = "sequenced_bake.bake"
    bl_label = "Sequenced Bake"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.sequenced_bake_props

        if scene.render.engine != 'CYCLES':
            self.report({'WARNING'}, "Sequenced Bake requires Cycles render engine")
            return {'FINISHED'}

        if not props.sequenced_bake_output_path:
            self.report({'ERROR'}, "No output path specified")
            return {'CANCELLED'}

        output_root = bpy.path.abspath(props.sequenced_bake_output_path)
        os.makedirs(output_root, exist_ok=True)

        obj = context.active_object
        if not obj or not obj.active_material:
            self.report({'ERROR'}, "Active object with material required")
            return {'CANCELLED'}

        mat = obj.active_material
        frame_start = scene.frame_start
        frame_end = scene.frame_end

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

        for bake_type, enabled in bake_map.items():
            if not enabled:
                continue

            if bake_type == "METALLIC":
                connect_metallic_node(mat)

            bake_dir = os.path.join(
                output_root,
                f"{obj.name}_{mat.name}_{bake_type}"
            )
            os.makedirs(bake_dir, exist_ok=True)

            for frame in range(frame_start, frame_end + 1):
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

            if bake_type == "METALLIC":
                reconnect_node(mat)

        clear_generated_textures(props)
        self.report({'INFO'}, "Sequenced Bake completed")
        return {'FINISHED'}
