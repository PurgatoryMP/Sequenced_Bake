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
import re
from bpy.types import (
        Operator,
        Panel,
        PropertyGroup,
        )

image_formats = [
    ("PNG", "PNG", "Save as PNG"),
    ("JPEG", "JPEG", "Save as JPEG"),
    ("BMP", "BMP", "Save as BMP"),
    ("TIFF", "TIFF", "Save as TIFF"),
    ("TGA", "TGA", "Save as TGA"),
    ("EXR", "OpenEXR", "Save as OpenEXR"),
    ("HDR", "Radiance HDR", "Save as Radiance HDR"),
    ("CINEON", "Cineon", "Save as Cineon"),
    ("DPX", "DPX", "Save as DPX")
]

class SequenceBakeProperties(PropertyGroup):
    sequenced_bake_output_path: bpy.props.StringProperty(
        name="",
        default="",
        subtype='DIR_PATH',
        description='Define the output path for the rendered images'
    )
    sequenced_bake_width: bpy.props.IntProperty(
        name="Width", 
        description='The width of the baked image',
        default=1024, 
        min=1, 
        max=8192
    )
    sequenced_bake_height: bpy.props.IntProperty(
        name="Height",
        description='The height of the baked image',
        default=1024, 
        min=1, 
        max=8192
    )
    sequence_bake_image_format: bpy.props.EnumProperty(
        name="",
        description="Choose the image format",
        items=image_formats
    )
    sequence_is_alpha: bpy.props.BoolProperty(
        name="Use Alpha",
        description="Use alpha channel in the generated material maps",
        default=False
    )
    sequence_clear_baked_maps: bpy.props.BoolProperty(
        name="Clear Baked Maps",
        description="Clears the baked maps from blenders image viewer list",
        default=True
    )
    sequenced_bake_normal: bpy.props.BoolProperty(
        name="Normal",
        description='Enable to bake the normal map for the selected objects active material',
        default=False
    )
    sequenced_bake_roughness: bpy.props.BoolProperty(
        name="Roughness",
        description='Enable to bake the roughness map for the selected objects active material',
        default=False
    )
    sequenced_bake_glossy: bpy.props.BoolProperty(
        name="Glossy",
        description='Enable to bake the glossy map for the selected objects active material',
        default=False
    )
    sequenced_bake_emission: bpy.props.BoolProperty(
        name="Emission",
        description='Enable to bake the emissive map for the selected objects active material',
        default=False
    )
    sequenced_bake_ambient_occlusion: bpy.props.BoolProperty(
        name="Ambient Occlusion",
        description='Enable to bake the ambient occlusion map for the selected objects active material',
        default=False
    )
    sequenced_bake_shadow: bpy.props.BoolProperty(
        name="Shadow",
        description='Enable to bake the shadow map for the selected objects active material',
        default=False
    )
    sequenced_bake_position: bpy.props.BoolProperty(
        name="Position",
        description='Enable to bake the position map for the selected objects active material',
        default=False
    )
    sequenced_bake_uv: bpy.props.BoolProperty(
        name="UV",
        description='Enable to bake the UV map for the selected objects active material',
        default=False
    )
    sequenced_bake_environment: bpy.props.BoolProperty(
        name="Environment",
        description='Enable to bake the environment map for the selected objects active material',
        default=False
    )
    sequenced_bake_diffuse: bpy.props.BoolProperty(
        name="Diffuse",
        description='Enable to bake the deffuse map for the selected objects active material',
        default=False
    )
    sequenced_bake_transmission: bpy.props.BoolProperty(
        name="Transmission",
        description='Enable to bake the transmission map for the selected objects active material',
        default=False
    )
    sequenced_bake_combined: bpy.props.BoolProperty(
        name="Combined",
        description='Enable to bake the combined map for the selected objects active material',
        default=False
    )
    sequenced_bake_metallic: bpy.props.BoolProperty(
        name="Metallic",
        description='Enable to bake the metallic map for the selected objects active material',
        default=False
    )

class SequencedBakePanel(Panel):
    bl_label = "Sequenced Bake"
    bl_idname = "VIEW3D_PT_sequenced_bake"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sequenced Bake'

    def draw(self, context):
    
        layout = self.layout        
        scene = context.scene
        sequence_bake_props = scene.sequence_bake_props
        sprite_sheet_props = scene.sprite_sheet_props

        # Output Path
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Output Path:")
        col.prop(sequence_bake_props, "sequenced_bake_output_path")
        
        col.separator(factor=3.0, type='LINE')
        
        # Generated Image Size
        col.label(text="Generated Image Size:")
        row = col.row(align=True)
        row.prop(sequence_bake_props, "sequenced_bake_width")
        row.prop(sequence_bake_props, "sequenced_bake_height")
        
        col.separator()
        
        col.label(text="Baked Image Format:")
        col.prop(sequence_bake_props, "sequence_bake_image_format")
        
        col.separator()
        
        col.prop(sequence_bake_props, "sequence_is_alpha")
        col.prop(sequence_bake_props, "sequence_clear_baked_maps")
        
        col.separator(factor=3.0, type='LINE')
        
        # Bake Type Options
        col.label(text="Bake Type Options:")
        col.prop(sequence_bake_props, "sequenced_bake_normal")
        col.prop(sequence_bake_props, "sequenced_bake_roughness")
        col.prop(sequence_bake_props, "sequenced_bake_glossy")
        col.prop(sequence_bake_props, "sequenced_bake_emission")
        col.prop(sequence_bake_props, "sequenced_bake_ambient_occlusion")
        col.prop(sequence_bake_props, "sequenced_bake_shadow")
        col.prop(sequence_bake_props, "sequenced_bake_position")
        col.prop(sequence_bake_props, "sequenced_bake_uv")
        col.prop(sequence_bake_props, "sequenced_bake_environment")
        col.prop(sequence_bake_props, "sequenced_bake_diffuse")
        col.prop(sequence_bake_props, "sequenced_bake_transmission")
        col.prop(sequence_bake_props, "sequenced_bake_combined")
        col.prop(sequence_bake_props, "sequenced_bake_metallic")
        
        col.separator(factor=3.0, type='LINE')
        
        # Baking Button
        col.operator("sequenced_bake.bake", text="Bake Material Sequence")  

class SequencedBakeOperator(Operator):
    bl_idname = "sequenced_bake.bake"
    bl_label = "Sequenced Bake"
    _props = None
    _cancel = False
    object_name = ""
    material_name = ""
    
    def modal(self, context, event):
        if event.type == 'ESC':
            self._cancel = True
            self.report({'INFO'}, "Baking cancelled by user")
            return {'CANCELLED'}

        if self._cancel:
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
    
        if bpy.context.scene.render.engine == 'CYCLES':
        
            self._props = bpy.context.scene.sequence_bake_props

            # Define the root directory.
            root_directory = self._props.sequenced_bake_output_path        
            if not root_directory:
                self.report({'ERROR'}, "No directory provided")
                return {'CANCELLED'}

            # Define the bake types to bake out
            bake_types = []
            if self._props.sequenced_bake_normal:
                bake_types.append('NORMAL')
            if self._props.sequenced_bake_roughness:
                bake_types.append('ROUGHNESS')
            if self._props.sequenced_bake_glossy:
                bake_types.append('GLOSSY')
            if self._props.sequenced_bake_emission:
                bake_types.append('EMIT')
            if self._props.sequenced_bake_ambient_occlusion:
                bake_types.append('Ambient Occlusion')
            if self._props.sequenced_bake_shadow:
                bake_types.append('SHADOW')
            if self._props.sequenced_bake_position:
                bake_types.append('POSITION')
            if self._props.sequenced_bake_uv:
                bake_types.append('UV')
            if self._props.sequenced_bake_environment:
                bake_types.append('ENVIRONMENT')
            if self._props.sequenced_bake_diffuse:
                bake_types.append('DIFFUSE')
            if self._props.sequenced_bake_transmission:
                bake_types.append('TRANSMISSION')
            if self._props.sequenced_bake_combined:
                bake_types.append('COMBINED')
                
            # Get the current frame range
            start_frame = bpy.context.scene.frame_start
            end_frame = bpy.context.scene.frame_end        
            frame_range = range(start_frame, end_frame + 1)
            
            # Get property settings.
            sequence_bake_image_format = self._props.sequence_bake_image_format        
            sequence_is_alpha = self._props.sequence_is_alpha

            # Get the active object
            obj = bpy.context.active_object
            self.object_name = obj.name
            
            if not obj:
                self.report({'ERROR'}, "No active object selected. Please select an object and try again")
                return {'CANCELLED'}

            # Get the active material
            mat = obj.active_material
            self.material_name = mat.name
            
            if not mat:
                self.report({'ERROR'}, "No active object selected. Please select an object and try again")
                return {'CANCELLED'}

            # Define the image size
            image_width = self._props.sequenced_bake_width
            image_height = self._props.sequenced_bake_height


             # Clear any existing image textures
            def clear_generated_textures():
                if(self._props.sequence_clear_baked_maps):
                    try:
                        for image in bpy.data.images:
                            if image.users == 0:
                                bpy.data.images.remove(image)
                    except Exception as err:
                        print(f"Clear Baked Maps Error: {err}")
            # 
            def bake_maps(bake_type):
                
                for frame in frame_range:
                    if self._cancel:
                        break
                    # Set the frame and update the scene
                    bpy.context.scene.frame_set(frame)
                    bpy.context.view_layer.update()
                    
                    bake_type_name = self.object_name +"_"+ self.material_name +"_"+ bake_type

                    # Create a new texture for the Image Texture node
                    texture = bpy.data.images.new(name=bake_type_name, width=image_width, height=image_height, alpha=sequence_is_alpha)

                    # Create a new Image Texture node
                    image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    
                    # Set node position
                    image_node.location = (400, -200)
                    image_node.image = texture

                    # Select the new Image Texture node making it the active selection.
                    mat.node_tree.nodes.active = image_node
                    
                    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

                    # Bake the texture
                    bpy.ops.object.bake(type=bake_type)
                    
                    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

                    # Define the output path
                    image_path = os.path.join(root_directory, bake_type_name, str(frame) + f".{sequence_bake_image_format}")

                    # Save the rendered image
                    texture.save_render(image_path)
                    
                    # Update the Blender interface
                    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                    
                    # Clear ONLY the generated texture nodes after the rendered image is saved.
                    active_node = mat.node_tree.nodes.active                
                    mat.node_tree.nodes.remove(active_node)
                    
            def connect_metallic_node():
                
                # Assuming you're working with the active object's active material
                material = bpy.context.object.active_material

                # Check if the material has a node tree and use nodes
                if material.use_nodes:
                    nodes = material.node_tree.nodes
                    links = material.node_tree.links
                    
                    # Find the Principled BSDF and Material Output nodes
                    principled_bsdf = None
                    material_output = None
                    
                    for node in nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            principled_bsdf = node
                        elif node.type == 'OUTPUT_MATERIAL':
                            material_output = node
                    
                    if principled_bsdf and material_output:
                        # Get the input connected to the 'Metallic' socket of the Principled BSDF node
                        metallic_input = principled_bsdf.inputs['Metallic']
                        
                        if metallic_input.is_linked:
                            # Get the node connected to the Metallic input
                            metallic_node_link = metallic_input.links[0]
                            connected_node = metallic_node_link.from_node
                            connected_output_socket = metallic_node_link.from_socket
                            
                            # Connect it to the Surface input of the Material Output node
                            surface_input = material_output.inputs['Surface']
                            links.new(connected_output_socket, surface_input)
                                    
                        else:
                            self.report({'WARNING'}, "The Metallic input is not connected to any node")
                    else:
                        self.report({'WARNING'}, "Principled BSDF or Material Output node not found")
                else:
                    self.report({'WARNING'}, "The material does not use nodes")                
            
            def reconnect_node():
                
                # Reconnects the Pricipled BSDF node to the material output node.
                # Get the active object's active material
                material = bpy.context.object.active_material

                # Check if the material has a node tree
                if material.use_nodes:
                    nodes = material.node_tree.nodes
                    links = material.node_tree.links
                    
                    # Find the Principled BSDF and Material Output nodes
                    principled_bsdf = None
                    material_output = None
                    
                    for node in nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            principled_bsdf = node
                        elif node.type == 'OUTPUT_MATERIAL':
                            material_output = node
                    
                    if principled_bsdf and material_output:
                        # Find the Surface input of the Material Output node
                        surface_input = material_output.inputs['Surface']
                        
                        # Disconnect any existing connections to the Surface input
                        for link in surface_input.links:
                            links.remove(link)
                        
                        # Connect the Principled BSDF node's output to the Surface input
                        bsdf_output_socket = principled_bsdf.outputs['BSDF']
                        links.new(bsdf_output_socket, surface_input)
                        
                        self.report({'INFO'}, "Reconnected Principled BSDF to Material Output")
                    else:
                        self.report({'WARNING'}, "Principled BSDF or Material Output node not found")
                else:
                    self.report({'WARNING'}, "The material does not use nodes")

            def bake_metallic():
                
                # Disconnect the node connected to the metallic input of the Pricipaled BSDF and connect it directly to the material output node.
                connect_metallic_node()
                
                for frame in frame_range:
                    if self._cancel:
                        break
                    # Set the frame and update the scene
                    bpy.context.scene.frame_set(frame)
                    bpy.context.view_layer.update()
                    
                    bake_type_name = self.object_name +"_"+ self.material_name +"_METALLIC"

                    # Create a new texture for the Image Texture node
                    texture = bpy.data.images.new(name=bake_type_name, width=image_width, height=image_height, alpha=sequence_is_alpha)
                                        
                    # Set the color space of the new texture to non color.
                    texture.colorspace_settings.name = 'Non-Color'

                    # Create a new Image Texture node
                    image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    
                    # Set node position
                    image_node.location = (400, -200)
                    image_node.image = texture

                    # Select the new Image Texture node
                    mat.node_tree.nodes.active = image_node
                    
                    # Bake the texture
                    try:
                        bpy.ops.object.bake(type='EMIT')
                    except Exception as error:
                        self.report({'ERROR'}, "No active object was selected. Please select an object and try again.")
                        return {"CANCELLED"}

                    # Define the output path
                    image_path = os.path.join(root_directory, bake_type_name, str(frame) + f".{sequence_bake_image_format}")

                    # Save the rendered image
                    texture.save_render(image_path)
                    
                    # Update the Blender interface
                    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                
                # Reconnect the pricipled BSDF node to the material output node.
                reconnect_node()    
            
            def invoke(self, context, event):
                self._cancel = False
                return self.execute(context)

            # Start baking the different material map sequences
            for bake_type in bake_types:
                if self._cancel:
                    break
                # Begin baking
                bake_maps(bake_type)
            
            # Metallic Map generation.
            if self._props.sequenced_bake_metallic:
                # Begin baking
                bake_metallic()
            
            # Clear any existing image textures        
            clear_generated_textures()
            
            self.report({'INFO'}, "Finished.")
            return {'FINISHED'}
        
        else:
            self.report({'WARNING'}, "Render engine is not set to Cycles.\nPlease switch to Cycles under the rendering tab and try again.")
            return {'FINISHED'}
