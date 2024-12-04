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
    
    # Normal map options.
    normal_map_space: bpy.props.EnumProperty(
        name="Space",
        description="Normal map coordinate space",
        items=[
            ('OBJECT', "Object", "Use object space for the normal map"),
            ('TANGENT', "Tangent", "Use tangent space for the normal map")
        ],
        default='TANGENT'
    )
    
    normal_map_red_channel: bpy.props.EnumProperty(
        name="R",
        description="Swizzle for the R channel",
        items=[
            ("POS_X", '+X', "Positive X axis"),
            ("POS_Y", '+Y', "Positive Y axis"),
            ("POS_Z", '+Z', "Positive Z axis"),
            ("NEG_X", '-X', "Negative X axis"),
            ("NEG_Y", '-Y', "Negative Y axis"),
            ("NEG_Z", '-Z', "Negative Z axis"),
        ],
        default="POS_X"
    )
    
    normal_map_green_channel: bpy.props.EnumProperty(
        name="G",
        description="Swizzle for the G channel",
        items=[
            ("POS_X", '+X', "Positive X axis"),
            ("POS_Y", '+Y', "Positive Y axis"),
            ("POS_Z", '+Z', "Positive Z axis"),
            ("NEG_X", '-X', "Negative X axis"),
            ("NEG_Y", '-Y', "Negative Y axis"),
            ("NEG_Z", '-Z', "Negative Z axis"),
        ],
        default="POS_Y"
    )
    
    normal_map_blue_channel: bpy.props.EnumProperty(
        name="B",
        description="Swizzle for the B channel",
        items=[
            ("POS_X", '+X', "Positive X axis"),
            ("POS_Y", '+Y', "Positive Y axis"),
            ("POS_Z", '+Z', "Positive Z axis"),
            ("NEG_X", '-X', "Negative X axis"),
            ("NEG_Y", '-Y', "Negative Y axis"),
            ("NEG_Z", '-Z', "Negative Z axis"),
        ],
        default="POS_Z"
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
    
    # Lighting options.
    diffuse_lighting_direct: bpy.props.BoolProperty(
        name="Direct",
        description="Include direct lighting in the bake",
        default=True
    )    
    diffuse_lighting_indirect: bpy.props.BoolProperty(
        name="Indirect",
        description="Include indirect lighting in the bake",
        default=True
    )    
    diffuse_lighting_color: bpy.props.BoolProperty(
        name="Color",
        description="Include color lighting contributions in the bake",
        default=True
    )
    glossy_lighting_direct: bpy.props.BoolProperty(
        name="Direct",
        description="Include direct lighting in the bake",
        default=True
    )    
    glossy_lighting_indirect: bpy.props.BoolProperty(
        name="Indirect",
        description="Include indirect lighting in the bake",
        default=True
    )    
    glossy_lighting_color: bpy.props.BoolProperty(
        name="Color",
        description="Include color lighting contributions in the bake",
        default=True
    )    
    transmission_lighting_direct: bpy.props.BoolProperty(
        name="Direct",
        description="Include direct lighting in the bake",
        default=True
    )    
    transmission_lighting_indirect: bpy.props.BoolProperty(
        name="Indirect",
        description="Include indirect lighting in the bake",
        default=True
    )    
    transmission_lighting_color: bpy.props.BoolProperty(
        name="Color",
        description="Include color lighting contributions in the bake",
        default=True
    )    
    combined_lighting_direct: bpy.props.BoolProperty(
        name="Direct",
        description="Include direct lighting in the bake",
        default=True
    )    
    combined_lighting_indirect: bpy.props.BoolProperty(
        name="Indirect",
        description="Include indirect lighting in the bake",
        default=True
    )    
    combined_lighting_color: bpy.props.BoolProperty(
        name="Color",
        description="Include color lighting contributions in the bake",
        default=True
    )    
    combined_contribution_deffuse: bpy.props.BoolProperty(
        name="Diffuse",
        description="Include diffuse contributions in the bake",
        default=True
    )
    combined_contribution_glossy: bpy.props.BoolProperty(
        name="Glossy",
        description="Include glossy contributions in the bake",
        default=True
    )
    combined_contribution_transmission: bpy.props.BoolProperty(
        name="Transmission",
        description="Include transmission contributions in the bake",
        default=True
    )
    combined_contribution_emit: bpy.props.BoolProperty(
        name="Emit",
        description="Include emission contributions in the bake",
        default=True
    )
    
    # Color Management options.
    
    # Display Device
    display_device: bpy.props.EnumProperty(
        name="Display Device",
        description="Select the display device",
        items=[
            ('sRGB', 'sRGB', ''),
            ('Display P3', 'Display P3', ''),
            ('Rec.1886', 'Rec.1886', ''),
            ('Rec.2020', 'Rec.2020', '')
        ],
        default='sRGB'
    )

    # View Transform
    view_transform: bpy.props.EnumProperty(
        name="View Transform",
        description="Select the view transform",
        items=[
            ('Standard', 'Standard', ''),
            ('Khronos PBR Neutral', 'Khronos PBR Neutral', ''),
            ('AgX', 'AgX', ''),
            ('Filmic', 'Filmic', ''),
            ('Filmic Log', 'Filmic Log', ''),
            ('False Color', 'False Color', ''),
            ('Raw', 'Raw', '')
        ],
        default='AgX'
    )

    # Look
    look: bpy.props.EnumProperty(
        name="Look",
        description="Select the look",
        items=[
            ('None', 'None', ''),
            ('Punchy', 'Punchy', ''),
            ('Greyscale', 'Greyscale', ''),
            ('Very High Contrast', 'Very High Contrast', ''),
            ('High Contrast', 'High Contrast', ''),
            ('Medium High Contrast', 'Medium High Contrast', ''),
            ('Base Contrast', 'Base Contrast', ''),
            ('Medium Low Contrast', 'Medium Low Contrast', ''),
            ('Low Contrast', 'Low Contrast', ''),
            ('Very Low Contrast', 'Very Low Contrast', '')
        ],
        default='None'
    )

    # Exposure
    exposure: bpy.props.FloatProperty(
        name="Exposure",
        description="Adjust the exposure level",
        default=0.0,
        min=-10.0,
        max=10.0
    )

    # Gamma
    gamma: bpy.props.FloatProperty(
        name="Gamma",
        description="Adjust the gamma level",
        default=1.0,
        min=0.0,
        max=5.0
    )

    # Sequencer
    sequencer: bpy.props.EnumProperty(
        name="Sequencer",
        description="Select the sequencer color space",
        items=[
            ('ACES2065-1', 'ACES2065-1', ''),
            ('ACEScg', 'ACEScg', ''),
            ('AgX Base_Display_P3', 'AgX Base Display P3', ''),
            ('AgX Base_Rec_1886', 'AgX Base Rec.1886', ''),
            ('AgX Base_Rec_2020', 'AgX Base Rec.2020', ''),
            ('AgX Base_sRGB', 'AgX Base sRGB', ''),
            ('AgX Log', 'AgX Log', ''),
            ('Display P3', 'Display P3', ''),
            ('Filmic Log', 'Filmic Log', ''),
            ('Filmic sRGB', 'Filmic sRGB', ''),
            ('Khronos PBR Neutral sRGB', 'Khronos PBR Neutral sRGB', ''),
            ('Linear CIE XYZ D65', 'Linear CIE-XYZ D65', ''),
            ('Linear CIE XYZ E', 'Linear CIE-XYZ E', ''),
            ('Linear DCI P3 D65', 'Linear DCI-P3 D65', ''),
            ('Linear FilmLight E Gamut', 'Linear FilmLight E-Gamut', ''),
            ('Linear Rec.2020', 'Linear Rec.2020', ''),
            ('Linear Rec.709', 'Linear Rec.709', ''),
            ('Non-Color', 'Non-Color', ''),
            ('Rec.1886', 'Rec.1886', ''),
            ('Rec.2020', 'Rec.2020', ''),
            ('sRGB', 'sRGB', '')
        ],
        default='sRGB'
    )
    
    # Image texture settings.
    interpolation: bpy.props.EnumProperty(
        name="Interpolation",
        description="Set the texture interpolation method",
        items=[
            ('Linear', "Linear", "Use linear interpolation"),
            ('Closest', "Closest", "Use nearest neighbor interpolation"),
            ('Cubic', "Cubic", "Use cubic interpolation"),
            ('Smart', "Smart", "Use smart interpolation"),
        ],
        default='Linear',
    )

    projection: bpy.props.EnumProperty(
        name="Projection",
        description="Set the texture projection method",
        items=[
            ('Flat', "Flat", "Flat projection"),
            ('Box', "Box", "Box projection"),
            ('Square', "Square", "Square projection"),
            ('Tube', "Tube", "Tube projection"),
        ],
        default='Flat',
    )

    extension: bpy.props.EnumProperty(
        name="Extension",
        description="Set the texture extension method",
        items=[
            ('Repeat', "Repeat", "Repeat the texture"),
            ('Extend', "Extend", "Extend the texture edges"),
            ('Clip', "Clip", "Clip the texture to the image bounds"),
            ('Mirror', "Mirror", "Mirror the texture"),
        ],
        default='Repeat',
    )
    
    colorspace: bpy.props.EnumProperty(
        name="Color Space",
        description="Set the color space of the texture",
        items=[
            ('ACES2065-1', 'ACES2065-1', ''),
            ('ACEScg', 'ACEScg', ''),
            ('AgX Base_Display_P3', 'AgX Base Display P3', ''),
            ('AgX Base_Rec_1886', 'AgX Base Rec.1886', ''),
            ('AgX Base_Rec_2020', 'AgX Base Rec.2020', ''),
            ('AgX Base_sRGB', 'AgX Base sRGB', ''),
            ('AgX Log', 'AgX Log', ''),
            ('Display P3', 'Display P3', ''),
            ('Filmic Log', 'Filmic Log', ''),
            ('Filmic sRGB', 'Filmic sRGB', ''),
            ('Khronos PBR Neutral sRGB', 'Khronos PBR Neutral sRGB', ''),
            ('Linear CIE XYZ D65', 'Linear CIE-XYZ D65', ''),
            ('Linear CIE XYZ E', 'Linear CIE-XYZ E', ''),
            ('Linear DCI P3 D65', 'Linear DCI-P3 D65', ''),
            ('Linear FilmLight E Gamut', 'Linear FilmLight E-Gamut', ''),
            ('Linear Rec.2020', 'Linear Rec.2020', ''),
            ('Linear Rec.709', 'Linear Rec.709', ''),
            ('Non-Color', 'Non-Color', ''),
            ('Rec.1886', 'Rec.1886', ''),
            ('Rec.2020', 'Rec.2020', ''),
            ('sRGB', 'sRGB', '')
        ],
        default='sRGB',
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
        option_padding = 2.0

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
        
        col.label(text="Image Texture Settings:")
        col.prop(sequence_bake_props, "interpolation")
        col.prop(sequence_bake_props, "projection")
        col.prop(sequence_bake_props, "extension")
        col.prop(sequence_bake_props, "colorspace")
        
        col.separator(factor=3.0, type='LINE')
                
        # Bake Type Options
        col.label(text="Bake Type Options:")
        col.prop(sequence_bake_props, "sequenced_bake_normal")  
        
        # Expand additional options if normal is selected
        if sequence_bake_props.sequenced_bake_normal:
            col.label(text="Normal Map Options:")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "normal_map_space")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "normal_map_red_channel")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "normal_map_green_channel")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "normal_map_blue_channel")
        
        col.prop(sequence_bake_props, "sequenced_bake_roughness")
        col.prop(sequence_bake_props, "sequenced_bake_glossy")
        
        # Expand additional options if glossy is selected
        if sequence_bake_props.sequenced_bake_glossy:
            col.label(text="Lighting Contributions:")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "glossy_lighting_direct", text="Direct")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "glossy_lighting_indirect", text="Indirect")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "glossy_lighting_color", text="Color")
        
        col.prop(sequence_bake_props, "sequenced_bake_emission")
        col.prop(sequence_bake_props, "sequenced_bake_ambient_occlusion")
        col.prop(sequence_bake_props, "sequenced_bake_shadow")
        col.prop(sequence_bake_props, "sequenced_bake_position")
        col.prop(sequence_bake_props, "sequenced_bake_uv")
        col.prop(sequence_bake_props, "sequenced_bake_environment")
        col.prop(sequence_bake_props, "sequenced_bake_diffuse")
        
        # Expand additional options if diffuse is selected
        if sequence_bake_props.sequenced_bake_diffuse:
            col.label(text="Lighting Contributions:")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "diffuse_lighting_direct", text="Direct")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "diffuse_lighting_indirect", text="Indirect")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "diffuse_lighting_color", text="Color")
        
        col.prop(sequence_bake_props, "sequenced_bake_transmission")
        
        # Expand additional options if transmission is selected
        if sequence_bake_props.sequenced_bake_transmission:
            col.label(text="Lighting Contributions:")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "transmission_lighting_direct", text="Direct")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "transmission_lighting_indirect", text="Indirect")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "transmission_lighting_color", text="Color")
        
        col.prop(sequence_bake_props, "sequenced_bake_combined")
        
        # Expand additional options if combined is selected
        if sequence_bake_props.sequenced_bake_combined:
            col.label(text="Lighting Contributions:")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "combined_lighting_direct", text="Direct")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "combined_lighting_indirect", text="Indirect")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "combined_contribution_deffuse", text="Diffuse")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "combined_contribution_glossy", text="Glossy")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "combined_contribution_transmission", text="Transmission")
            
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(sequence_bake_props, "combined_contribution_emit", text="Emit")
        
        col.prop(sequence_bake_props, "sequenced_bake_metallic")
        
        col.separator(factor=3.0, type='LINE')
        
        col.label(text="Color Management:")
        col.prop(sequence_bake_props, "display_device")
        col.prop(sequence_bake_props, "view_transform")
        col.prop(sequence_bake_props, "look")
        col.prop(sequence_bake_props, "exposure")
        col.prop(sequence_bake_props, "gamma")
        col.prop(sequence_bake_props, "sequencer")
        
        col.separator(factor=3.0, type='LINE')
        
        # Baking Button
        col.operator("sequenced_bake.bake", text="Bake Material Sequence")

class SequencedBakeOperator(Operator):
    bl_idname = "sequenced_bake.bake"
    bl_label = "Sequenced Bake"
    _props = None
    object_name = ""
    material_name = ""
    
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
            if self._props.sequenced_bake_metallic:
                bake_types.append('METALLIC')
                
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
                        self.report({'ERROR'}, f"Problem with clearing baked maps: {err}")
            # 
            def bake_maps(bake_type):
            
                if bake_type == "METALLIC":
                    # Disconnect the node connected to the metallic input of the Pricipaled BSDF and connect it directly to the material output node.
                    connect_metallic_node(mat)
                
                for frame in frame_range:
                    
                    # Set the frame and update the scene
                    bpy.context.scene.frame_set(frame)
                    bpy.context.view_layer.update()
                    
                    bake_type_name = self.object_name +"_"+ self.material_name +"_"+ bake_type

                    # Create a new texture for the Image Texture node
                    texture = bpy.data.images.new(name=bake_type_name, width=image_width, height=image_height, alpha=sequence_is_alpha)
                    
                    # Texture color space.
                    texture.colorspace_settings.name = self._props.colorspace
                    
                    # Create a new Image Texture node
                    image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    
                    # Image Texture Settings.
                    image_node.interpolation = self._props.interpolation.capitalize() 
                    image_node.projection  = self._props.projection.upper() 
                    image_node.extension  = self._props.extension.upper()
                    
                    # Get the position of the material output node.
                    material_output_node = None
                    for node in mat.node_tree.nodes:
                        if node.type == 'OUTPUT_MATERIAL':
                            material_output_node = node
                            break
                    
                    if material_output_node:
                        material_output_position = material_output_node.location
                    else:
                        # Default if Material Output node isn't found
                        self.report({'ERROR'}, "Material Output node was not found, Please add your material output node and try again.")
                        return {'CANCELLED'}                    
                    
                    # Set node position to the right of the material output node.
                    image_node.location = (material_output_position.x + 250, material_output_position.y)
                    image_node.image = texture

                    # Select the new Image Texture node making it the active selection.
                    mat.node_tree.nodes.active = image_node
                    
                    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

                     # Set bake type and lighting contributions
                    if bake_type == "DIFFUSE":
                        bpy.context.scene.render.bake.use_pass_direct = self._props.diffuse_lighting_direct
                        bpy.context.scene.render.bake.use_pass_indirect = self._props.diffuse_lighting_indirect
                        bpy.context.scene.render.bake.use_pass_color = self._props.diffuse_lighting_color
                    elif bake_type == "GLOSSY":
                        bpy.context.scene.render.bake.use_pass_direct = self._props.glossy_lighting_direct
                        bpy.context.scene.render.bake.use_pass_indirect = self._props.glossy_lighting_indirect
                        bpy.context.scene.render.bake.use_pass_color = self._props.glossy_lighting_color
                    elif bake_type == "TRANSMISSION":
                        bpy.context.scene.render.bake.use_pass_direct = self._props.transmission_lighting_direct
                        bpy.context.scene.render.bake.use_pass_indirect = self._props.transmission_lighting_indirect
                        bpy.context.scene.render.bake.use_pass_color = self._props.transmission_lighting_color
                    elif bake_type == "NORMAL":                      
                        # Set the normal space (Object or Tangent)
                        if self._props.normal_map_space == 'OBJECT':
                            bpy.context.scene.render.bake.normal_space = 'OBJECT'
                        else:
                            bpy.context.scene.render.bake.normal_space = 'TANGENT'                        
                        # Set the swizzle settings for normal channel baking
                        bpy.context.scene.render.bake.normal_r = self._props.normal_map_red_channel
                        bpy.context.scene.render.bake.normal_g = self._props.normal_map_green_channel
                        bpy.context.scene.render.bake.normal_b = self._props.normal_map_blue_channel
                                                
                    # elif bake_type == "ROUGHNESS":
                    # elif bake_type == "EMIT":
                    # elif bake_type == "Ambient Occlusion":
                    # elif bake_type == "SHADOW":
                    # elif bake_type == "POSITION":
                    # elif bake_type == "UV":
                    # elif bake_type == "ENVIRONMENT":
                    
                    elif bake_type == "COMBINED":
                        bpy.context.scene.render.bake.use_pass_direct = self._props.combined_lighting_direct
                        bpy.context.scene.render.bake.use_pass_indirect = self._props.combined_lighting_indirect
                        bpy.context.scene.render.bake.use_pass_color = self._props.combined_lighting_color                        
                        bpy.context.scene.render.bake.use_pass_diffuse = self._props.combined_contribution_deffuse
                        bpy.context.scene.render.bake.use_pass_glossy = self._props.combined_contribution_glossy
                        bpy.context.scene.render.bake.use_pass_transmission = self._props.combined_contribution_transmission
                        bpy.context.scene.render.bake.use_pass_emit = self._props.combined_contribution_emit
                    
                    # elif bake_type == "METALLIC":
                    
                    # Color Management options.                    
                    # Apply Display Device
                    bpy.context.scene.display_settings.display_device = self._props.display_device
                    
                    # Apply View Transform and Look
                    bpy.context.scene.view_settings.view_transform = self._props.view_transform
                    
                    agx_prefix = ''
                    if self._props.view_transform == 'AgX' and self._props.look != 'None':
                        agx_prefix = 'AgX - '
                    
                    bpy.context.scene.view_settings.look = agx_prefix + self._props.look

                    # Apply Exposure and Gamma
                    bpy.context.scene.view_settings.exposure = self._props.exposure
                    bpy.context.scene.view_settings.gamma = self._props.gamma

                    # Apply Sequencer Color Space
                    try:
                        bpy.context.scene.sequencer_colorspace_settings.name = self._props.sequencer
                    except Exception as e:
                        self.report({'WARNING'}, f"Sequencer color space '{props.sequencer}' not applied: {str(e)}")                    
                    
                    # Bake the texture
                    try:
                        if bake_type == "METALLIC":
                            bpy.ops.object.bake(type="EMIT")
                        else:
                            bpy.ops.object.bake(type=bake_type)
                    except Exception as error:
                        self.report({'ERROR'}, f"There was an error while attempting to bake the {bake_type} map. Error: {error.args}")
                        return {"CANCELLED"}
                    
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
                    
                # Reconnect the pricipled BSDF node to the material output node.
                if bake_type == "METALLIC":
                    reconnect_node(mat)  
                    
            def connect_metallic_node(material):
                # Connect the node currenty connected to the metallic channel of the Pricipaled BSDF and connect it directly to the material output.
            
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
            
            def reconnect_node(material):                
                # Reconnects the Pricipled BSDF node to the material output node.

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
  
                        
            if bake_types:            
                # Start baking the different material map sequences
                for bake_type in bake_types:
                    # Begin baking
                    bake_maps(bake_type)
                    
                # Clear any existing image textures        
                clear_generated_textures()
            
            else:
                self.report({'WARNING'}, "No bake types have been selected, Please choose a bake type and try again.")
                return {"CANCELLED"}
            
            self.report({'INFO'}, "Finished.")
            return {'FINISHED'}
        
        else:
            self.report({'WARNING'}, "Render engine is not set to Cycles.\nPlease switch to Cycles under the rendering tab and try again.")
            return {'FINISHED'}
