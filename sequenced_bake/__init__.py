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


bl_info = {
    "name": "Sequenced Bake",
    "author": "Anthony OConnell",
    "version": (1, 0, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Sequenced Bake",
    "description": "Add-on for material sequenced baking in Blender",
    "category": "3D View"
}

import bpy
import os
from bpy.types import (
        Operator,
        Panel,
        )

class SequencedBakePanel(Panel):
    bl_label = "Sequenced Bake"
    bl_idname = "VIEW3D_PT_sequenced_bake"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sequenced Bake'

    def draw(self, context):
        # setup the UI elements
        layout = self.layout

        col = layout.column(align=True)
        
        col.label(text="Output Path:")
        col.prop(context.scene, "sequenced_bake_output_path", text="")
        
        col.label(text="")
        
        col.label(text="Generated Image Size:")
        row = col.row(align=True)
        row.prop(context.scene, "sequenced_bake_width")
        row.prop(context.scene, "sequenced_bake_height")
        
        col.label(text="")
        
        col.label(text="Bake Type Options:")
        col.prop(context.scene, "sequenced_bake_normal", text="Normal")
        col.prop(context.scene, "sequenced_bake_roughness", text="Roughness")
        col.prop(context.scene, "sequenced_bake_glossy", text="Glossy")
        col.prop(context.scene, "sequenced_bake_emit", text="Emit")
        col.prop(context.scene, "sequenced_bake_ao", text="AO")
        col.prop(context.scene, "sequenced_bake_shadow", text="Shadow")
        col.prop(context.scene, "sequenced_bake_position", text="Position")
        col.prop(context.scene, "sequenced_bake_uv", text="UV")
        col.prop(context.scene, "sequenced_bake_environment", text="Environment")
        col.prop(context.scene, "sequenced_bake_diffuse", text="Diffuse")
        col.prop(context.scene, "sequenced_bake_transmission", text="Transmission")
        col.prop(context.scene, "sequenced_bake_combined", text="Combined")
        
        col.label(text="")
        
        col.label(text="Baking: ")
        col.operator("sequenced_bake.bake", text="Bake Material Sequence")


class SequencedBakeOperator(Operator):
    bl_idname = "sequenced_bake.bake"
    bl_label = "Sequenced Bake"
    bl_description = "Start the sequenced baking process"

    def execute(self, context):

        # Define the root directory.
        root_directory = bpy.context.scene.sequenced_bake_output_path

        # Define the bake types to bake out
        bake_types = []
        if bpy.context.scene.sequenced_bake_normal:
            bake_types.append('NORMAL')
        if bpy.context.scene.sequenced_bake_roughness:
            bake_types.append('ROUGHNESS')
        if bpy.context.scene.sequenced_bake_glossy:
            bake_types.append('GLOSSY')
        if bpy.context.scene.sequenced_bake_emit:
            bake_types.append('EMIT')
        if bpy.context.scene.sequenced_bake_ao:
            bake_types.append('AO')
        if bpy.context.scene.sequenced_bake_shadow:
            bake_types.append('SHADOW')
        if bpy.context.scene.sequenced_bake_position:
            bake_types.append('POSITION')
        if bpy.context.scene.sequenced_bake_uv:
            bake_types.append('UV')
        if bpy.context.scene.sequenced_bake_environment:
            bake_types.append('ENVIRONMENT')
        if bpy.context.scene.sequenced_bake_diffuse:
            bake_types.append('DIFFUSE')
        if bpy.context.scene.sequenced_bake_transmission:
            bake_types.append('TRANSMISSION')
        if bpy.context.scene.sequenced_bake_combined:
            bake_types.append('COMBINED')

        # Get the current frame range
        frame_range = range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1)

        # Get the active object
        obj = bpy.context.active_object

        # Get the active material
        mat = obj.active_material

        # Define the image size
        image_width = bpy.context.scene.sequenced_bake_width
        image_height = bpy.context.scene.sequenced_bake_height

        # Define the function to remove the generated texture node rather than removing all the texture nodes
        def remove_generated_texture_node():
            material = bpy.context.active_object.active_material
            if material and material.node_tree:
                node_tree = material.node_tree
                nodes_to_remove = []
                for node in node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        nodes_to_remove.append(node)
                for node in nodes_to_remove:
                    node_tree.nodes.remove(node)

        # Clear any existing image textures
        for image in bpy.data.images:
            if image.users == 0:
                bpy.data.images.remove(image)

        def bake_maps(bake_type):
            # Call the function to remove the generated texture node
            remove_generated_texture_node()

            for frame in frame_range:
                # Set the frame and update the scene
                bpy.context.scene.frame_set(frame)
                bpy.context.view_layer.update()

                # Create a new texture for the Image Texture node
                texture = bpy.data.images.new(name=bake_type, width=image_width, height=image_height, alpha=True)

                # Create a new Image Texture node
                image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                
                # Set node position
                image_node.location = (400, -200)
                image_node.image = texture

                # Select the new Image Texture node
                mat.node_tree.nodes.active = image_node

                # Bake the texture
                bpy.ops.object.bake(type=bake_type)

                # Define the output path
                image_path = os.path.join(root_directory, bake_type, str(frame) + '.png')

                # Save the rendered image
                texture.save_render(image_path)
                
                # Update the Blender interface
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        # Start baking the different material map sequences
        for bake_type in bake_types:
            bake_directory = os.path.join(root_directory, bake_type)
            os.makedirs(bake_directory, exist_ok=True)

            # Begin baking
            bake_maps(bake_type)
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        # Call the function to remove the generated texture node
        remove_generated_texture_node()

        # Clear any existing image textures
        for image in bpy.data.images:
            if image.users == 0:
                bpy.data.images.remove(image)

        self.report({'INFO'}, "Sequenced bake completed successfully")
        return {'FINISHED'}


def register():
    bpy.types.Scene.sequenced_bake_output_path = bpy.props.StringProperty(
        name="Output Path", 
        subtype='DIR_PATH',
        description='Define the output path for the rendered images'
    )
    bpy.types.Scene.sequenced_bake_width = bpy.props.IntProperty(
        name="Width", default=1024, min=1, max=4096
    )
    bpy.types.Scene.sequenced_bake_height = bpy.props.IntProperty(
        name="Height", default=1024, min=1, max=4096
    )

    bpy.types.Scene.sequenced_bake_normal = bpy.props.BoolProperty(name="Normal")
    bpy.types.Scene.sequenced_bake_roughness = bpy.props.BoolProperty(name="Roughness")
    bpy.types.Scene.sequenced_bake_glossy = bpy.props.BoolProperty(name="Glossy")
    bpy.types.Scene.sequenced_bake_emit = bpy.props.BoolProperty(name="Emit")
    bpy.types.Scene.sequenced_bake_ao = bpy.props.BoolProperty(name="AO")
    bpy.types.Scene.sequenced_bake_shadow = bpy.props.BoolProperty(name="Shadow")
    bpy.types.Scene.sequenced_bake_position = bpy.props.BoolProperty(name="Position")
    bpy.types.Scene.sequenced_bake_uv = bpy.props.BoolProperty(name="UV")
    bpy.types.Scene.sequenced_bake_environment = bpy.props.BoolProperty(name="Environment")
    bpy.types.Scene.sequenced_bake_diffuse = bpy.props.BoolProperty(name="Diffuse")
    bpy.types.Scene.sequenced_bake_transmission = bpy.props.BoolProperty(name="Transmission")
    bpy.types.Scene.sequenced_bake_combined = bpy.props.BoolProperty(name="Combined")

    bpy.utils.register_class(SequencedBakePanel)
    bpy.utils.register_class(SequencedBakeOperator)


def unregister():
    bpy.utils.unregister_class(SequencedBakePanel)
    bpy.utils.unregister_class(SequencedBakeOperator)

    del bpy.types.Scene.sequenced_bake_output_path
    del bpy.types.Scene.sequenced_bake_width
    del bpy.types.Scene.sequenced_bake_height

    del bpy.types.Scene.sequenced_bake_normal
    del bpy.types.Scene.sequenced_bake_roughness
    del bpy.types.Scene.sequenced_bake_glossy
    del bpy.types.Scene.sequenced_bake_emit
    del bpy.types.Scene.sequenced_bake_ao
    del bpy.types.Scene.sequenced_bake_shadow
    del bpy.types.Scene.sequenced_bake_position
    del bpy.types.Scene.sequenced_bake_uv
    del bpy.types.Scene.sequenced_bake_environment
    del bpy.types.Scene.sequenced_bake_diffuse
    del bpy.types.Scene.sequenced_bake_transmission
    del bpy.types.Scene.sequenced_bake_combined


if __name__ == "__main__":
    register()
